"""Utilities for building PDF friendly data representations of turns."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from app.models import Services, Turns


@dataclass
class TurnPdfService:
    """Small DTO describing a service that will appear in the PDF."""

    id: str
    name: str
    price: float
    description: Optional[str] = None
    specialty: Optional[str] = None
    icon_code: Optional[str] = None


@dataclass
class TurnPdfData:
    """Aggregated data needed to render a PDF for a turn."""

    turn_id: str
    state: str
    reason: Optional[str]
    scheduled_date: str
    scheduled_time: str
    created_at: str
    limit_date: str
    patient_full_name: str
    patient_dni: Optional[str]
    patient_email: Optional[str]
    patient_phone: Optional[str]
    doctor_full_name: str
    doctor_specialty: Optional[str]
    services: List[TurnPdfService] = field(default_factory=list)
    services_summary: str = ""
    total_price: float = 0.0
    appointment_id: Optional[str] = None
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds"))


def _full_name(entity, *, fallback: str) -> str:
    """Builds a display name combining first and last name when available."""

    if entity is None:
        return fallback

    parts = [part.strip() for part in (getattr(entity, "first_name", None), getattr(entity, "last_name", None)) if part]
    if parts:
        return " ".join(parts)

    username = getattr(entity, "name", None)
    return username or fallback


def _service_to_pdf(service: Services) -> TurnPdfService:
    """Translate a Service model into its PDF representation."""

    specialty_name = service.speciality.name if getattr(service, "speciality", None) else None

    return TurnPdfService(
        id=str(service.id),
        name=service.name,
        description=getattr(service, "description", None),
        price=service.price,
        specialty=specialty_name,
        icon_code=getattr(service, "icon_code", None),
    )


def build_turn_pdf_data(turn: Turns) -> TurnPdfData:
    """Build a :class:`TurnPdfData` instance from a :class:`Turns` model."""

    patient_full_name = _full_name(turn.user, fallback="Paciente sin datos")
    doctor_full_name = _full_name(turn.doctor, fallback="Profesional no asignado")
    doctor_specialty = (
        turn.doctor.speciality.name
        if turn.doctor and getattr(turn.doctor, "speciality", None) and getattr(turn.doctor.speciality, "name", None)
        else "Especialidad no especificada"
    )

    services_data = [_service_to_pdf(service) for service in getattr(turn, "services", [])]
    services_summary = (
        ", ".join(f"{service.name} ($ {service.price:.2f})" for service in services_data)
        if services_data
        else "Sin servicios asociados"
    )

    total_price = turn.price_total()

    scheduled_date = turn.date.isoformat() if getattr(turn, "date", None) else ""
    scheduled_time = turn.time.strftime("%H:%M") if getattr(turn, "time", None) else ""
    created_at = turn.date_created.isoformat() if getattr(turn, "date_created", None) else ""
    limit_date = turn.date_limit.isoformat() if getattr(turn, "date_limit", None) else ""

    appointment_id = str(turn.appointment.id) if getattr(turn, "appointment", None) else None

    return TurnPdfData(
        turn_id=str(turn.id),
        state=str(turn.state),
        reason=getattr(turn, "reason", None),
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time,
        created_at=created_at,
        limit_date=limit_date,
        patient_full_name=patient_full_name,
        patient_dni=getattr(turn.user, "dni", None) if turn.user else None,
        patient_email=getattr(turn.user, "email", None) if turn.user else None,
        patient_phone=getattr(turn.user, "telephone", None) if turn.user else None,
        doctor_full_name=doctor_full_name,
        doctor_specialty=doctor_specialty,
        services=services_data,
        services_summary=services_summary,
        total_price=total_price,
        appointment_id=appointment_id,
    )


__all__ = ["TurnPdfData", "TurnPdfService", "build_turn_pdf_data"]
