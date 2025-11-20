"""Appointment routes."""
from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import ORJSONResponse
from sqlmodel import select

from app.db.main import SessionDep
from app.models import Appointments
from app.schemas.medica_area import AppointmentResponse
from app.schemas.medica_area.services import ServiceResponse

from .common import auth_dependency, default_response_class


router = APIRouter(
    prefix="/appointments",
    tags=["appointments"],
    default_response_class=default_response_class,
    dependencies=[auth_dependency()],
)


def _get_primary_service(turn) -> Tuple[Optional[UUID], Optional[dict]]:
    """Return the primary service (first one) associated with a turn.

    The legacy schema stores services as a list in the turn, so we pick the
    first one to maintain backwards compatibility with consumers expecting a
    singular service_id/service payload.
    """

    if not turn or not turn.services:
        return None, None

    service = turn.services[0]
    serialized_service = ServiceResponse(
        id=service.id,
        name=service.name,
        description=service.description,
        price=service.price,
        specialty_id=service.specialty_id,
        icon_code=service.icon_code,
    ).model_dump()

    return service.id, serialized_service


@router.get("/", response_model=List[AppointmentResponse])
async def get_appointments(request: Request, session: SessionDep):
    if not request.state.user.is_superuser and "doc" not in request.state.scopes:
        raise HTTPException(status_code=401, detail="You are not authorized")

    statement = select(Appointments)
    result = session.exec(statement).all()
    serialized_appointments: List[AppointmentResponse] = []
    for appointment in result:
        service_id, serialized_service = _get_primary_service(appointment.turn)
        serialized_appointments.append(
            AppointmentResponse(
                id=appointment.id,
                user_id=appointment.user_id,
                doctor_id=appointment.doctor_id,
                turn_id=appointment.turn_id,
                service_id=service_id,
                date=appointment.turn.date,
                date_created=appointment.turn.date_created,
                date_limit=appointment.turn.date_limit,
                state=appointment.turn.state,
                service=serialized_service,
            ).model_dump()
        )

    return ORJSONResponse(serialized_appointments)


__all__ = ["router"]
