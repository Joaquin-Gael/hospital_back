from __future__ import annotations

import stripe
import stripe as st

from datetime import datetime
from uuid import UUID
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from rich.console import Console

from app.models import Cashes, CashDetails, Payment, PaymentStatus, Turns, HealthInsurance
from app.config import (
    STRIPE_SECRET_KEY,
    STRIPE_WEBHOOK_SECRET,
    CORS_HOST,
    ID_PREFIX,
)

if TYPE_CHECKING:  # pragma: no cover - only for type checking
    from app.core.services.payment import PaymentService

console = Console()

stripe.api_key = STRIPE_SECRET_KEY

class StripeServices:
    @staticmethod
    async def proces_payment(
        price: float,
        details: dict,
        h_i: UUID | None,
        session: Session,
        *,
        payment: Payment | None = None,
    ) -> dict | None:
        line_items: list[dict] = []

        # Si no hay obra social, health_insurance = None
        health_insurance = session.get(HealthInsurance, h_i) if h_i is not None else None

        # Descuento centralizado (0 si no hay obra social)
        discount: float = float(getattr(health_insurance, "discount", 0) or 0)
        multiplier: float = 1 - (discount / 100)

        # Por si alguien carga un descuento raro >100
        if multiplier < 0:
            multiplier = 0

        # Construcción de items para Stripe
        for detail in details["products_data"]:
            base_price = float(detail["price"])
            quantity = int(detail["quantity"])

            # precio en centavos, con descuento aplicado
            unit_amount = int(round(base_price * 100 * multiplier))

            line_items.append(
                {
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": unit_amount,
                        "product_data": {
                            "name": detail["name"],
                            "description": detail.get("description", ""),
                        },
                    },
                    "quantity": quantity,
                }
            )

        try:
            total_with_discount = float(price) * multiplier

            checkout_session = st.checkout.Session.create(
                payment_method_types=["card"],
                line_items=line_items,
                mode="payment",
                success_url=(
                    f"{CORS_HOST}/{ID_PREFIX}/cashes/pay/success"
                    f"?session_id={{CHECKOUT_SESSION_ID}}"
                ),
                cancel_url=(
                    f"{CORS_HOST}/{ID_PREFIX}/cashes/pay/cancel"
                    f"?session_id={{CHECKOUT_SESSION_ID}}"
                ),
                client_reference_id=str(getattr(payment, "id", details["turn_id"])),
                metadata={
                    "payment_id": str(getattr(payment, "id", "")),
                    "turn_id": str(details["turn_id"]),
                    "discount": str(discount),
                },
            )

            return {
                "checkout_url": checkout_session.url,
                "session_id": checkout_session.id,
                "amount_total": total_with_discount,
                "discount": discount,
            }

        except Exception:
            console.print_exception(show_locals=True)
            return None

    @staticmethod
    async def create_cash_detail(
        session: Session,
        turn_id: UUID,
        payment_method: str,
        discount: int,
        total: float,
        services: list,
        *,
        payment_id: UUID | None = None,
    ) -> bool:
        try:
            with session.begin():
                turn = session.exec(
                    select(Turns).where(Turns.id == turn_id)
                ).first()

                now = datetime.utcnow()
                open_cash = session.exec(
                    select(Cashes).where(
                        Cashes.date == now.date()
                    )
                ).first()

                if not open_cash:
                    open_cash = Cashes(
                        income=0,
                        expense=0,
                        balance=0,
                        date=now.date(),
                        time_transaction=now.time(),
                        transaction_type="income",
                        reference_id=payment_id or turn_id,
                        description="Stripe payment settlement",
                        metadata={
                            "turn_id": str(turn_id),
                            "payment_id": str(payment_id) if payment_id else None,
                            "payment_method": payment_method,
                            "discount": discount,
                        },
                        created_by=turn.user_id,
                        created_at=now,
                    )
                    session.add(open_cash)
                    session.flush()
                else:
                    session.merge(open_cash)
                    session.refresh(open_cash)

                session.refresh(turn)

                discount_factor = 1 - (float(discount) / 100)
                if discount_factor < 0:
                    discount_factor = 0

                for service in turn.services:
                    discounted_amount = service.price * discount_factor

                    open_cash.details.append(
                        CashDetails(
                            cash_id=open_cash.id,
                            service_id=service.id,
                            description=f"{service.name}-{payment_method}-{service.speciality}",
                            amount=discounted_amount,       # monto cobrado
                            total=service.price,            # precio base
                            date=now.date(),
                            time_transaction=now.time(),
                            appointment_id=turn.appointment.id,
                            discount=discount,
                            transaction_type="income",
                            reference_id=payment_id or turn_id,
                            transaction_metadata={
                                "turn_id": str(turn_id),
                                "payment_id": str(payment_id) if payment_id else None,
                                "payment_method": payment_method,
                                "service_id": str(service.id),
                            },
                            created_by=turn.user_id,
                            created_at=now,
                        )
                    )

                open_cash.apply_transaction(income_delta=total)
                open_cash.time_transaction = now.time()
                open_cash.reference_id = open_cash.reference_id or payment_id or turn_id
                merged_metadata = dict(open_cash.transaction_metadata or {})
                merged_metadata.update(
                    {
                        "last_turn_id": str(turn_id),
                        "last_payment_id": str(payment_id) if payment_id else None,
                        "payment_method": payment_method,
                    }
                )
                open_cash.transaction_metadata = merged_metadata

                session.add(open_cash)
                session.commit()

                return True

        except IntegrityError:
            console.print_exception(show_locals=True)
            session.rollback()
            return False

    @staticmethod
    def construct_event(payload: bytes, signature: str) -> stripe.Event:
        if not STRIPE_WEBHOOK_SECRET:
            raise ValueError("Stripe webhook secret is not configured")

        try:
            return stripe.Webhook.construct_event(
                payload, signature, STRIPE_WEBHOOK_SECRET
            )
        except stripe.error.SignatureVerificationError as exc:  # type: ignore[attr-defined]
            raise ValueError("Invalid Stripe signature") from exc

    @staticmethod
    def _map_event_to_status(event_type: str) -> PaymentStatus | None:
        mapping: dict[str, PaymentStatus] = {
            "checkout.session.completed": PaymentStatus.succeeded,
            "payment_intent.payment_failed": PaymentStatus.failed,
            "charge.failed": PaymentStatus.failed,
            "charge.refunded": PaymentStatus.cancelled,
            "charge.refund.updated": PaymentStatus.cancelled,
            "checkout.session.expired": PaymentStatus.cancelled,
            "payment_intent.canceled": PaymentStatus.cancelled,
        }
        return mapping.get(event_type)

    @staticmethod
    def _get_payment_from_object(
        payment_service: PaymentService, session_obj: dict
    ) -> Payment | None:
        metadata = session_obj.get("metadata") or {}
        payment_id = metadata.get("payment_id")

        if payment_id:
            try:
                return payment_service.get_payment(UUID(payment_id))
            except ValueError:
                pass

        session_id = session_obj.get("id")
        if session_id:
            return payment_service.get_payment_by_session(session_id)

        return None

    @staticmethod
    async def handle_webhook_event(
        payment_service: PaymentService, event: stripe.Event
    ) -> Payment | None:
        status = StripeServices._map_event_to_status(event.get("type", ""))
        if status is None:
            return None

        session_obj = event.get("data", {}).get("object", {})
        payment = StripeServices._get_payment_from_object(payment_service, session_obj)
        if payment is None:
            return None

        previous_status = payment.status
        discount = 0
        metadata = session_obj.get("metadata") or {}

        try:
            discount = int(float(metadata.get("discount", 0)))
        except (TypeError, ValueError):
            discount = 0

        updated_payment = payment_service.transition_status(
            payment,
            status,
            gateway_metadata={"stripe_event": event.get("type")},
            gateway_session_id=session_obj.get("id"),
        )

        if (
            previous_status != PaymentStatus.succeeded
            and updated_payment.status == PaymentStatus.succeeded
        ):
            await StripeServices.create_cash_detail(
                payment_service.session,
                turn_id=updated_payment.turn_id,
                payment_method=updated_payment.payment_method.value,
                discount=discount,
                total=updated_payment.amount_total,
                services=[],
                payment_id=updated_payment.id,
            )

        return updated_payment
