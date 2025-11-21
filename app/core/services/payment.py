from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from sqlmodel import Session, select

from app.core.services.stripe_payment import StripeServices
from app.models import (
    Appointments,
    Payment,
    PaymentItem,
    PaymentMethod,
    PaymentStatus,
    Turns,
    User,
)


class PaymentService:
    """Domain service to handle payment lifecycle operations."""

    _ALLOWED_TRANSITIONS: Dict[PaymentStatus, set[PaymentStatus]] = {
        PaymentStatus.pending: {
            PaymentStatus.succeeded,
            PaymentStatus.failed,
            PaymentStatus.cancelled,
        },
        PaymentStatus.failed: {PaymentStatus.pending, PaymentStatus.cancelled},
        PaymentStatus.succeeded: set(),
        PaymentStatus.cancelled: set(),
    }

    def __init__(self, session: Session):
        self.session = session

    async def create_payment_for_turn(
        self,
        turn: Turns,
        *,
        appointment: Optional[Appointments] = None,
        user: Optional[User] = None,
        payment_method: PaymentMethod = PaymentMethod.card,
        gateway_metadata: Optional[dict] = None,
        health_insurance_id: Optional[UUID] = None,
    ) -> Payment:
        """Create a pending payment with items for the provided turn."""

        payment_url = await StripeServices.proces_payment(
            price=turn.price_total(),
            details=turn.get_details(),
            h_i=health_insurance_id,
            session=self.session,
        )

        payment = Payment(
            turn_id=turn.id,
            appointment_id=appointment.id if appointment else None,
            user_id=user.id if user else None,
            payment_method=payment_method,
            status=PaymentStatus.pending,
            amount_total=turn.price_total(),
            payment_url=payment_url,
            gateway_metadata=gateway_metadata,
        )

        payment.items = [
            PaymentItem(
                service_id=service.id,
                name=service.name,
                description=service.description,
                quantity=1,
                unit_amount=service.price,
                total_amount=service.price,
            )
            for service in turn.services
        ]

        self.session.add(payment)
        self.session.commit()
        self.session.refresh(payment)
        return payment

    def get_payment(self, payment_id: UUID) -> Optional[Payment]:
        return self.session.get(Payment, payment_id)

    def list_payments(self, user_id: Optional[UUID] = None) -> List[Payment]:
        statement = select(Payment)
        if user_id:
            statement = statement.where(Payment.user_id == user_id)
        return list(self.session.exec(statement))

    def update_status(
        self,
        payment: Payment | UUID,
        new_status: PaymentStatus,
        *,
        gateway_metadata: Optional[dict] = None,
        payment_url: Optional[str] = None,
        gateway_session_id: Optional[str] = None,
    ) -> Payment:
        if isinstance(payment, UUID):
            payment = self.get_payment(payment)
        if payment is None:
            raise ValueError("Payment not found")

        self._assert_transition(payment.status, new_status)

        payment.status = new_status
        payment.updated_at = datetime.utcnow()

        if gateway_metadata:
            merged = {**(payment.gateway_metadata or {}), **gateway_metadata}
            payment.gateway_metadata = merged

        if payment_url:
            payment.payment_url = payment_url

        if gateway_session_id:
            payment.gateway_session_id = gateway_session_id

        self.session.add(payment)
        self.session.commit()
        self.session.refresh(payment)
        return payment

    def delete_payment(self, payment_id: UUID) -> bool:
        payment = self.get_payment(payment_id)
        if payment is None:
            return False

        self.session.delete(payment)
        self.session.commit()
        return True

    def _assert_transition(
        self, current: PaymentStatus, new_status: PaymentStatus
    ) -> None:
        allowed = self._ALLOWED_TRANSITIONS.get(current, set())
        if new_status not in allowed and new_status != current:
            raise ValueError(
                f"Cannot transition payment from {current.value} to {new_status.value}"
            )
