from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.payment import PaymentMethod, PaymentStatus


class PaymentItemBase(BaseModel):
    service_id: Optional[UUID] = None
    name: str
    description: Optional[str] = None
    quantity: int = 1
    unit_amount: float
    total_amount: float


class PaymentItemCreate(PaymentItemBase):
    pass


class PaymentItemRead(PaymentItemBase):
    id: UUID


class PaymentBase(BaseModel):
    turn_id: UUID
    appointment_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    payment_method: PaymentMethod = PaymentMethod.card
    status: PaymentStatus = PaymentStatus.pending
    amount_total: float
    currency: str = "usd"
    payment_url: Optional[str] = None
    gateway_session_id: Optional[str] = None
    gateway_metadata: Optional[dict[str, Any]] = None


class PaymentCreate(BaseModel):
    turn_id: UUID
    appointment_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    payment_method: PaymentMethod = PaymentMethod.card
    gateway_metadata: Optional[dict[str, Any]] = None


class PaymentTurnCreate(BaseModel):
    """Payload para recrear o iniciar una sesión de pago de un turno."""

    turn_id: UUID
    payment_method: PaymentMethod = PaymentMethod.card
    gateway_metadata: Optional[dict[str, Any]] = None


class PaymentRead(PaymentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    items: List[PaymentItemRead] = Field(default_factory=list)


class PaymentStatusUpdate(BaseModel):
    status: PaymentStatus
    gateway_metadata: Optional[dict[str, Any]] = None
    payment_url: Optional[str] = None
    gateway_session_id: Optional[str] = None
