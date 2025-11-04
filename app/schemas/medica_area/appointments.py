from __future__ import annotations

from datetime import date as date_type
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.schemas import UserRead

from .enums import TurnsState


class AppointmentBase(BaseModel):
    id: UUID
    reason: Optional[str] = None
    state: TurnsState
    date: date_type
    date_created: date_type
    user_id: Optional[UUID] = None
    doctor_id: Optional[UUID] = None
    service_id: Optional[UUID] = None
    appointment_id: Optional[UUID] = None
    date_limit: date_type


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentUpdate(BaseModel):
    id: Optional[UUID] = None
    reason: Optional[str] = None
    state: Optional[TurnsState] = None
    date: Optional[date_type] = None
    date_created: Optional[date_type] = None


class AppointmentResponse(AppointmentBase):
    user: Optional[UserRead] = None
    doctor: Optional["DoctorResponse"] = None
    service: Optional["ServiceResponse"] = None
    turn: Optional["TurnsResponse"] = None


class AppointmentDelete(BaseModel):
    id: UUID
    message: str
