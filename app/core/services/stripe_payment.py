import stripe
import stripe as st

from datetime import datetime

from urllib.parse import urlencode

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from rich.console import Console

from app.models import Cashes, CashDetails, Turns, HealthInsurance
from app.config import stripe_secret_key, stripe_public_key, cors_host, id_prefix
from app.core.auth import encode

console = Console()

stripe.api_key = stripe_secret_key

class StripeServices:
    @staticmethod
    async def proces_payment(
        price: float,
        details: dict,
        h_i: UUID | None,
        session: Session
    ) -> str | None:
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

            payload_data = {
                "turn_id": str(details["turn_id"]),
                "total": total_with_discount,        # total YA con descuento
                "payment_method": "card",
                "discount": discount,                # % de descuento usado
                "services": encode(details["products_data"]).hex(),
            }

            payload = {"a": encode(payload_data).hex()}

            bad_payload = {
                "b": encode({"turn_id": str(details["turn_id"])}).hex()
            }

            checkout_session = st.checkout.Session.create(
                payment_method_types=["card"],
                line_items=line_items,
                mode="payment",
                success_url=(
                    f"{cors_host}/{id_prefix}/cashes/pay/success"
                    f"?session_id={{CHECKOUT_SESSION_ID}}&{urlencode(payload)}"
                ),
                cancel_url=(
                    f"{cors_host}/{id_prefix}/cashes/pay/cancel?"
                    f"{urlencode(bad_payload)}"
                ),
            )

            return checkout_session.url

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
        services: list
    ) -> bool:
        try:
            with session.begin():
                turn = session.exec(
                    select(Turns).where(Turns.id == turn_id)
                ).first()

                open_cash = session.exec(
                    select(Cashes).where(
                        Cashes.date == datetime.now().date()
                    )
                ).first()

                if not open_cash:
                    open_cash = Cashes(
                        date=datetime.now().date()
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
                            date=datetime.now().date(),
                            appointment_id=turn.appointment.id,
                            discount=discount,
                        )
                    )

                open_cash.income += total
                open_cash.make_balance()

                session.add(open_cash)
                session.commit()

                return True

        except IntegrityError:
            console.print_exception(show_locals=True)
            session.rollback()
            return False