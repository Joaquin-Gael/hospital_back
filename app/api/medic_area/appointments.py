"""Appointment routes."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import ORJSONResponse
from sqlmodel import select

from app.db.main import SessionDep
from app.models import Appointments
from app.schemas.medica_area import AppointmentResponse

from .common import auth_dependency, default_response_class


router = APIRouter(
    prefix="/appointments",
    tags=["appointments"],
    default_response_class=default_response_class,
    dependencies=[auth_dependency()],
)


@router.get("/", response_model=List[AppointmentResponse])
async def get_appointments(request: Request, session: SessionDep):
    if not request.state.user.is_superuser and "doc" not in request.state.scopes:
        raise HTTPException(status_code=401, detail="You are not authorized")

    statement = select(Appointments)
    result = session.exec(statement).all()
    serialized_appointments: List[AppointmentResponse] = []
    for appointment in result:
        serialized_appointments.append(
            AppointmentResponse(
                id=appointment.id,
                user_id=appointment.user_id,
                doctor_id=appointment.doctor_id,
                turn_id=appointment.turn_id,
                service_id=appointment.turn.service_id,
                date=appointment.turn.date,
                date_created=appointment.turn.date_created,
                date_limit=appointment.turn.date_limit,
                state=appointment.turn.state,
            ).model_dump()
        )

    return ORJSONResponse(serialized_appointments)


__all__ = ["router"]
