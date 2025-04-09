from fastapi import APIRouter, Request
from fastapi.responses import ORJSONResponse

from sqlmodel import select

from typing import List

from rich import print
from rich.console import Console

from app.models import medic_area
from app.models.medic_area import Doctors, MedicalSchedules, Locations, Services, Specialties, Departments
from app.schemas.medica_area import (
    MedicalScheduleCreate,
    MedicalScheduleDelete,
    MedicalScheduleUpdate,
    MedicalScheduleResponse
)
from app.schemas.medica_area import (
    DoctorResponse,
)
from app.db.main import SessionDep

console = Console()

schedules = APIRouter(
    prefix="/schedules",
    tags=["schedules"],
    default_response_class=ORJSONResponse,
)

@schedules.get("/", response_model=List[MedicalScheduleResponse])
async def get_medical_schedules(request: Request, session: SessionDep):
    statement = select(MedicalSchedules)
    result: List[MedicalSchedules] = session.execute(statement).scalars().all()
    schedules = []
    for schedule_i in result:
        doctors: List[DoctorResponse] = []
        for doctor_i in schedule_i.doctors:
            doctor = DoctorResponse(
                id=doctor_i.id,
                name=doctor_i.name,
                lastname=doctor_i.lastname,
                dni=doctor_i.dni,
                telephone=doctor_i.telephone,
                email=doctor_i.email,
                medical_schedule_id=doctor_i.medical_schedule_id,
                speciality_id=doctor_i.speciality_id
            )
            doctors.append(doctor.model_dump())
        schedule = MedicalScheduleResponse(
            id=schedule_i.id,
            day=schedule_i.day,
            time_medic=schedule_i.time_medic,
            doctors=doctors
        )
        schedules.append(schedule.model_dump())

    return ORJSONResponse(
        schedules
    )

@schedules.post("/add/", response_model=MedicalScheduleResponse)
async def add_schedule(request: Request, medical_schedule: MedicalScheduleCreate, session: SessionDep):
    schedule = MedicalSchedules(
        day=medical_schedule.day,
        time_medic=medical_schedule.time_medic,
    )
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    return ORJSONResponse(
        MedicalScheduleResponse(
            id=schedule.id,
            day=schedule.day,
            time_medic=schedule.time_medic,
            doctors=schedule.doctors
        ).model_dump()
    )

router = APIRouter(
    prefix="/medic",
    default_response_class=ORJSONResponse,
)

router.include_router(schedules)