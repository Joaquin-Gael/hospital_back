from __future__ import annotations

from datetime import date as date_type, datetime, time as time_type
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    computed_field,
    field_serializer,
    field_validator,
)

from app.schemas import UserRead
from app.schemas.payment import PaymentRead
from app.models.payment import PaymentStatus

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
    model_config = ConfigDict(from_attributes=True)

    user: Optional[UserRead] = None
    doctor: Optional["DoctorResponse"] = None
    service: Optional[List["ServiceResponse"]] = None
    payment: Optional[PaymentRead] = None

    @field_validator("services", mode="before")
    @classmethod
    def normalize_services(cls, value):
        if isinstance(value, list):
            return [getattr(item, "id", item) for item in value]
        return value

    @field_validator("user", mode="before")
    @classmethod
    def normalize_user(cls, value):
        if value is None:
            return None

        if isinstance(value, dict):
            if "username" not in value and "name" in value:
                value = {**value, "username": value.get("name")}
            if "img_profile" not in value and "url_image_profile" in value:
                value = {**value, "img_profile": value.get("url_image_profile")}
            if "health_insurance" in value and value["health_insurance"]:
                value = {
                    **value,
                    "health_insurance": [
                        getattr(insurance, "id", insurance)
                        for insurance in value.get("health_insurance", [])
                    ],
                }
            return value

        return {
            "id": getattr(value, "id", None),
            "username": getattr(value, "name", None),
            "email": getattr(value, "email", None),
            "first_name": getattr(value, "first_name", None),
            "last_name": getattr(value, "last_name", None),
            "dni": getattr(value, "dni", None),
            "telephone": getattr(value, "telephone", None),
            "address": getattr(value, "address", None),
            "blood_type": getattr(value, "blood_type", None),
            "health_insurance": [
                getattr(insurance, "id", insurance)
                for insurance in getattr(value, "health_insurance", [])
            ],
            "is_active": getattr(value, "is_active", None),
            "is_admin": getattr(value, "is_admin", None),
            "is_superuser": getattr(value, "is_superuser", None),
            "last_login": getattr(value, "last_login", None),
            "date_joined": getattr(value, "date_joined", None),
            "img_profile": getattr(value, "url_image_profile", None),
        }

    @field_validator("doctor", mode="before")
    @classmethod
    def normalize_doctor(cls, value):
        if value is None:
            return None

        if isinstance(value, dict):
            if "username" not in value and "name" in value:
                value = {**value, "username": value.get("name")}
            if "img_profile" not in value and "url_image_profile" in value:
                value = {**value, "img_profile": value.get("url_image_profile")}
            return value

        return {
            "id": getattr(value, "id", None),
            "username": getattr(value, "name", None),
            "email": getattr(value, "email", None),
            "first_name": getattr(value, "first_name", None),
            "last_name": getattr(value, "last_name", None),
            "dni": getattr(value, "dni", None),
            "telephone": getattr(value, "telephone", None),
            "speciality_id": getattr(value, "speciality_id", None),
            "address": getattr(value, "address", None),
            "blood_type": getattr(value, "blood_type", None),
            "doctor_state": getattr(value, "doctor_state", None),
            "is_active": getattr(value, "is_active", None),
            "is_admin": getattr(value, "is_admin", None),
            "is_superuser": getattr(value, "is_superuser", None),
            "last_login": getattr(value, "last_login", None),
            "date_joined": getattr(value, "date_joined", None),
            "img_profile": getattr(value, "url_image_profile", None),
        }

    @computed_field(return_type=Optional[str])
    def payment_url(self) -> Optional[str]:
        if self.payment is None:
            return None

        return self.payment.payment_url

    @computed_field(return_type=Optional[PaymentStatus])
    def payment_status(self) -> Optional[PaymentStatus]:
        if self.payment is None:
            return None

        return self.payment.status


class PayTurnResponse(BaseModel):
    turn: TurnsResponse
    payment: PaymentRead
    payment_url: Optional[str] = None


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
