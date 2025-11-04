from __future__ import annotations

from datetime import date as date_type, datetime, time as time_type
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from app.schemas import UserRead

from .enums import TurnsState


class TurnsBase(BaseModel):
    id: UUID
    reason: Optional[str] = None
    state: TurnsState
    date: date_type
    date_created: date_type
    user_id: Optional[UUID] = None
    doctor_id: Optional[UUID] = None
    services: Optional[List[UUID]] = None
    appointment_id: Optional[UUID] = None
    date_limit: date_type
    time: time_type


class TurnsCreate(BaseModel):
    reason: Optional[str] = None
    state: TurnsState
    date: date_type
    date_created: date_type = datetime.now().date()
    user_id: Optional[UUID] = None
    services: List[UUID] = []
    time: time_type
    health_insurance: Optional[UUID] = None


class TurnsUpdate(BaseModel):
    id: Optional[UUID] = None
    reason: Optional[str] = None
    state: Optional[TurnsState] = None
    date: Optional[date_type] = None
    date_created: Optional[date_type] = None
    time: Optional[date_type] = None


class TurnsResponse(TurnsBase):
    user: Optional[UserRead] = None
    doctor: Optional["DoctorResponse"] = None
    service: Optional[List["ServiceResponse"]] = None


class PayTurnResponse(BaseModel):
    turn: TurnsResponse
    payment_url: str


class TurnsDelete(BaseModel):
    id: UUID
    message: str
