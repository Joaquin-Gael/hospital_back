"""Specialty related routes."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import ORJSONResponse
from sqlmodel import select

from app.db.main import SessionDep
from app.models import Doctors, Services, Specialties
from app.schemas.medica_area import (
    DoctorResponse,
    ServiceResponse,
    SpecialtyCreate,
    SpecialtyDelete,
    SpecialtyResponse,
    SpecialtyUpdate,
)

from .common import auth_dependency, default_response_class


router = APIRouter(
    prefix="/specialities",
    tags=["specialities"],
    default_response_class=default_response_class,
    dependencies=[auth_dependency()],
)


@router.get("/", response_model=List[SpecialtyResponse])
async def get_specialities(request: Request, session: SessionDep):
    statement = select(Specialties)
    result = session.exec(statement).all()

    specialities_serialized: List[SpecialtyResponse] = []
    for speciality in result:
        services_serialized = [
            ServiceResponse(
                id=service.id,
                name=service.name,
                description=service.description,
                price=service.price,
                specialty_id=service.specialty_id,
                icon_code=service.icon_code,
            )
            for service in speciality.services
        ]

        doctors_serialized = [
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
            )
            for doc in session.exec(
                select(Doctors).where(Doctors.speciality_id == speciality.id)
            ).all()
        ]

        specialities_serialized.append(
            SpecialtyResponse(
                id=speciality.id,
                name=speciality.name,
                description=speciality.description,
                department_id=speciality.department_id,
                doctors=doctors_serialized,
                services=services_serialized,
            ).model_dump()
        )

    return ORJSONResponse(specialities_serialized, status_code=status.HTTP_200_OK)


@router.post("/add/", response_model=SpecialtyResponse)
async def add_speciality(
    request: Request, session: SessionDep, specialty: SpecialtyCreate
):
    if not request.state.user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="scopes have not unauthorized",
        )

    try:
        new_speciality = Specialties(
            name=specialty.name,
            description=specialty.description,
            department_id=specialty.department_id,
        )

        session.add(new_speciality)
        session.commit()
        session.refresh(new_speciality)

        return ORJSONResponse(
            SpecialtyResponse(
                id=new_speciality.id,
                name=new_speciality.name,
                description=new_speciality.description,
                department_id=new_speciality.department_id,
            ).model_dump(),
            status_code=status.HTTP_201_CREATED,
        )

    except Exception as exc:  # pragma: no cover - mirrors behaviour
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.delete("/delete/{speciality_id}/", response_model=SpecialtyDelete)
async def delete_speciality(
    request: Request, session: SessionDep, speciality_id: UUID
):
    if not request.state.user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="scopes have not unauthorized",
        )

    speciality = session.exec(
        select(Specialties).where(Specialties.id == speciality_id)
    ).first()

    session.delete(speciality)
    session.commit()

    return ORJSONResponse(
        SpecialtyDelete(
            id=speciality.id,
            message=f"Specialty {speciality.name} has been deleted",
        ).model_dump()
    )


@router.patch("/update/{speciality_id}/", response_model=SpecialtyResponse)
async def update_speciality(
    request: Request,
    session: SessionDep,
    speciality_id: UUID,
    speciality: SpecialtyUpdate,
):
    if not request.state.user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="scopes have not unauthorized",
        )

    new_speciality = session.exec(
        select(Specialties).where(Specialties.id == speciality_id)
    ).first()

    fields = speciality.__fields__.keys()

    for field in fields:
        value = getattr(speciality, field)
        if value is not None:
            setattr(new_speciality, field, value)

    session.add(new_speciality)
    session.commit()
    session.refresh(new_speciality)

    return ORJSONResponse(
        SpecialtyResponse(
            id=new_speciality.id,
            name=new_speciality.name,
            description=new_speciality.description,
            department_id=new_speciality.department_id,
        ).model_dump()
    )


__all__ = ["router"]
