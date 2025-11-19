from __future__ import annotations

from datetime import date as date_type, datetime, time as time_type
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, computed_field, field_serializer

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
    doctor_id: Optional[UUID] = None
    services: List[UUID] = []
    time: time_type
    health_insurance: Optional[UUID] = None


class TurnsUpdate(BaseModel):
    id: Optional[UUID] = None
    reason: Optional[str] = None
    state: Optional[TurnsState] = None
    date: Optional[date_type] = None
    date_created: Optional[date_type] = None
    time: Optional[time_type] = None


class TurnReschedule(BaseModel):
    date: date_type
    time: time_type


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


class TurnDocumentSummary(BaseModel):
    """DTO con los metadatos principales del PDF generado para un turno."""

    id: UUID
    turn_id: UUID
    user_id: UUID
    file_path: str
    generated_at: datetime
    turn: Optional[TurnsResponse] = None

    @computed_field(return_type=str)
    def filename(self) -> str:
        """Nombre del archivo derivado del path, útil para listados en frontend."""

        return Path(self.file_path).name

    @field_serializer("generated_at")
    def serialize_generated_at(self, generated_at: datetime) -> str:
        """Normaliza el timestamp para entrega consistente al frontend."""

        return generated_at.replace(microsecond=0).isoformat()


class TurnDocumentDownloadLog(BaseModel):
    """DTO que describe un evento de descarga de un PDF de turno."""

    id: UUID
    turn_document_id: UUID
    turn_id: UUID
    user_id: UUID
    downloaded_at: datetime
    channel: str
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    user: Optional[UserRead] = None
    turn: Optional[TurnsResponse] = None

    @field_serializer("downloaded_at")
    def serialize_downloaded_at(self, downloaded_at: datetime) -> str:
        """Expone el timestamp de descarga en formato ISO 8601 sin microsegundos."""

        return downloaded_at.replace(microsecond=0).isoformat()
