"""Schedules related routes."""
from datetime import date as date_type
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import ORJSONResponse
from sqlmodel import select

from app.db.main import SessionDep
from app.models import Doctors, MedicalSchedules, Specialties
from app.schemas.medica_area import (
    AvailableSchedules,
    DayOfWeek,
    DoctorResponse,
    MedicalScheduleCreate,
    MedicalScheduleResponse,
    MedicalScheduleUpdate,
    Schedules,
)

from .common import auth_dependency, console, default_response_class


router = APIRouter(
    prefix="/schedules",
    tags=["schedules"],
    default_response_class=default_response_class,
    dependencies=[auth_dependency()],
)


@router.get("/", response_model=List[MedicalScheduleResponse])
async def get_medical_schedules(request: Request, session: SessionDep):
    statement = select(MedicalSchedules)
    result = session.exec(statement).all()
    schedules = []
    for schedule_i in result:
        doctors = [
            DoctorResponse(
                id=doc.id,
                is_active=doc.is_active,
                is_admin=doc.is_admin,
                is_superuser=doc.is_superuser,
                last_login=doc.last_login,
                date_joined=doc.date_joined,
                username=doc.name,
                email=doc.email,
                first_name=doc.first_name,
                last_name=doc.last_name,
                dni=doc.dni,
                telephone=doc.telephone,
                speciality_id=doc.speciality_id,
                blood_type=doc.blood_type,
            )
            for doc in schedule_i.doctors
        ]
        schedule = MedicalScheduleResponse(
            id=schedule_i.id,
            day=schedule_i.day,
            start_time=schedule_i.start_time,
            end_time=schedule_i.end_time,
            doctors=doctors,
        )
        schedules.append(schedule.model_dump())

    return ORJSONResponse(schedules)


@router.get("/{schedule_id}", response_model=MedicalScheduleResponse)
async def get_schedule_by_id(session: SessionDep, schedule_id: UUID):
    try:
        schedule = session.get(MedicalSchedules, schedule_id)
        doctors_by_schedule_serialized = [
            DoctorResponse(
                username=doc.name,
                dni=doc.dni,
                id=doc.id,
                email=doc.email,
                speciality_id=doc.speciality_id,
                is_active=doc.is_active,
                doctor_status=doc.doctor_state,
                date_joined=doc.date_joined,
            )
            for doc in schedule.doctors
        ]

        return ORJSONResponse(
            MedicalScheduleResponse(
                id=schedule.id,
                day=schedule.day,
                start_time=schedule.start_time,
                end_time=schedule.end_time,
                doctors=doctors_by_schedule_serialized,
            ).model_dump(),
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:  # pragma: no cover - legacy behaviour
        console.print_exception(show_locals=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc


@router.get("/available/days/{speciality_id}", response_model=AvailableSchedules)
async def days_by_availability(
    request: Request, speciality_id: UUID, session: SessionDep, date: date_type | None = None
):
    try:
        speciality = session.get(Specialties, speciality_id)

        if speciality is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Specialty not found",
            )

        dict_days = {}
        target_day = (
            DayOfWeek(date.strftime("%A").lower()) if date is not None else None
        )

        for doc in speciality.doctors:
            for schedule in doc.medical_schedules:
                if not schedule.available:
                    continue

                if target_day is not None and schedule.day != target_day:
                    continue

                if date is not None and schedule.max_patients is not None:
                    turns_by_date = [turn for turn in schedule.turns if turn.date == date]
                    if len(turns_by_date) >= schedule.max_patients:
                        continue

                if dict_days.get(schedule.day.value, None):
                    match dict_days[schedule.day.value]:
                        case (start, end) if start > schedule.start_time and end > schedule.end_time:
                            dict_days[schedule.day.value] = (
                                schedule.start_time,
                                end,
                            )

                        case (start, end) if start < schedule.start_time and end < schedule.end_time:
                            dict_days[schedule.day.value] = (
                                start,
                                schedule.end_time,
                            )

                        case (start, end) if start < schedule.start_time and end > schedule.end_time:
                            continue
                else:
                    dict_days.setdefault(
                        schedule.day.value,
                        (
                            schedule.start_time,
                            schedule.end_time,
                        ),
                    )

        return ORJSONResponse(
            AvailableSchedules(
                available_days=[
                    Schedules(
                        day=k,
                        start_time=v[0],
                        end_time=v[1],
                    ).model_dump()
                    for k, v in dict_days.items()
                ]
            ).model_dump(),
            status_code=status.HTTP_200_OK,
        )
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - legacy behaviour
        console.print_exception(show_locals=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc


@router.post("/add/", response_model=MedicalScheduleResponse)
async def add_schedule(medical_schedule: MedicalScheduleCreate, session: SessionDep):
    schedule = MedicalSchedules(
        day=medical_schedule.day,
        start_time=medical_schedule.start_time,
        end_time=medical_schedule.end_time,
    )
    session.add(schedule)
    session.commit()
    session.refresh(schedule)

    doctors = [
        DoctorResponse(
            id=doc.id,
            is_active=doc.is_active,
            is_admin=doc.is_admin,
            is_superuser=doc.is_superuser,
            last_login=doc.last_login,
            date_joined=doc.date_joined,
            username=doc.name,
            email=doc.email,
            first_name=doc.first_name,
            last_name=doc.last_name,
            dni=doc.dni,
            telephone=doc.telephone,
            speciality_id=doc.speciality_id,
        ).model_dump()
        for doc in schedule.doctors
    ]

    return ORJSONResponse(
        MedicalScheduleResponse(
            id=schedule.id,
            day=schedule.day,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            doctors=doctors,
        ).model_dump()
    )


@router.put("/update/")
async def update_schedule(schedule: MedicalScheduleUpdate, session: SessionDep):
    """Update schedule details."""
    try:
        statement = select(MedicalSchedules).where(MedicalSchedules.id == schedule.id)
        result = session.exec(statement).first()

        form_fields = MedicalScheduleUpdate.__fields__.keys()

        for field in form_fields:
            value = getattr(schedule, field, None)
            if value is not None and field != "username":
                setattr(result, field, value)

        session.add(result)
        session.commit()
        session.refresh(result)

        return ORJSONResponse(
            MedicalScheduleResponse(
                id=result.id,
                start_time=result.start_time,
                end_time=result.end_time,
                day=result.day,
            ).model_dump(),
        )

    except Exception as exc:  # pragma: no cover - mirrors previous behaviour
        console.print_exception(show_locals=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {schedule.id} not found",
        ) from exc


__all__ = ["router"]
