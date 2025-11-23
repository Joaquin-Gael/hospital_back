from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, Enum as SQLEnum
from sqlalchemy import UUID as UUID_TYPE
from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from app.models import Appointments, Services, Turns, User


class PaymentStatus(str, Enum):
    pending = "pending"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class PaymentMethod(str, Enum):
    card = "card"
    cash = "cash"
    transfer = "transfer"


class Payment(SQLModel, table=True):
    __tablename__ = "payments"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        sa_type=UUID_TYPE,
        sa_column_kwargs={"name": "payment_id"},
    )
    turn_id: UUID = Field(
        sa_type=UUID_TYPE,
        foreign_key="turns.turn_id",
        nullable=False,
    )
    appointment_id: Optional[UUID] = Field(
        default=None,
        sa_type=UUID_TYPE,
        foreign_key="appointments.appointment_id",
        nullable=True,
    )
    user_id: Optional[UUID] = Field(
        default=None,
        sa_type=UUID_TYPE,
        foreign_key="users.user_id",
        nullable=True,
    )
    status: PaymentStatus = Field(
        default=PaymentStatus.pending,
        sa_type=SQLEnum(PaymentStatus),
        nullable=False,
    )
    payment_method: PaymentMethod = Field(
        default=PaymentMethod.card,
        sa_type=SQLEnum(PaymentMethod),
        nullable=False,
    )
    amount_total: float = Field(default=0, nullable=False)
    currency: str = Field(default="usd", max_length=8)
    payment_url: Optional[str] = Field(default=None, nullable=True)
    gateway_session_id: Optional[str] = Field(default=None, nullable=True)
    gateway_metadata: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # ---------- RELACIONES ----------

    # Turno (muchos pagos pueden apuntar al mismo turno)
    turn: Optional["Turns"] = Relationship(
        sa_relationship=relationship(
            "Turns",
            back_populates="payments",
            uselist=False,
        )
    )

    # Cita asociada
    appointment: Optional["Appointments"] = Relationship(
        sa_relationship=relationship(
            "Appointments",
            back_populates="payments",
            uselist=False,
        )
    )

    # Usuario que paga
    user: Optional["User"] = Relationship(
        sa_relationship=relationship(
            "User",
            back_populates="payments",
        )
    )

    # Ítems del pago (1:N)
    items: List["PaymentItem"] = Relationship(
        sa_relationship=relationship(
            "PaymentItem",
            back_populates="payment",
            cascade="all, delete-orphan",
        )
    )


class PaymentItem(SQLModel, table=True):
    __tablename__ = "payment_items"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        sa_type=UUID_TYPE,
        sa_column_kwargs={"name": "payment_item_id"},
    )
    payment_id: UUID = Field(
        sa_type=UUID_TYPE,
        foreign_key="payments.payment_id",
        nullable=False,
    )
    service_id: Optional[UUID] = Field(
        default=None,
        sa_type=UUID_TYPE,
        foreign_key="services.service_id",
        nullable=True,
    )
    name: str
    description: Optional[str] = Field(default=None, nullable=True)
    quantity: int = Field(default=1, ge=1)
    unit_amount: float = Field(default=0)
    total_amount: float = Field(default=0)

    # Relación inversa con Payment (N:1)
    payment: "Payment" = Relationship(
        sa_relationship=relationship(
            "Payment",
            back_populates="items",
        )
    )

    # Servicio asociado (opcional)
    service: Optional["Services"] = Relationship(
        sa_relationship=relationship("Services")
    )
