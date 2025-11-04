"""Location related routes."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import ORJSONResponse
from sqlmodel import select

from app.db.main import SessionDep
from app.models import Departments, Doctors, Locations, Services, Specialties
from app.schemas.medica_area import (
    DepartmentResponse,
    DoctorResponse,
    LocationCreate,
    LocationDelete,
    LocationResponse,
    LocationUpdate,
    ServiceResponse,
    SpecialtyResponse,
)

from .common import auth_dependency, default_response_class


router = APIRouter(
    prefix="/locations",
    tags=["locations"],
    default_response_class=default_response_class,
    dependencies=[auth_dependency()],
)


@router.get("/", response_model=List[LocationResponse])
async def get_locations(request: Request, session: SessionDep):
    statement = select(Locations).where(True)
    result = session.exec(statement).all()
    return [
        LocationResponse(
            id=location.id,
            name=location.name,
            description=location.description,
        ).model_dump()
        for location in result
    ]


@router.get("/all", response_model=List[LocationResponse])
async def get_locations_all_data(request: Request, session: SessionDep):
    statement = select(Locations).where(True)
    result_i = session.exec(statement).all()
    locations_serialized = []
    for location in result_i:
        result_departments = location.departments
        departments_serialized = []
        for department in result_departments:
            result_specialties = department.specialities
            specialties_serialized = []
            for specialty in result_specialties:
                result_services = specialty.services
                services_serialized = [
                    ServiceResponse(
                        id=service.id,
                        name=service.name,
                        description=service.description,
                        price=service.price,
                        specialty_id=service.specialty_id,
                        icon_code=service.icon_code,
                    )
                    for service in result_services
                ]
                result_doctors = specialty.doctors
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
                        blood_type=doc.blood_type,
                    )
                    for doc in result_doctors
                ]
                specialties_serialized.append(
                    SpecialtyResponse(
                        id=specialty.id,
                        name=specialty.name,
                        description=specialty.description,
                        department_id=specialty.department_id,
                        services=services_serialized,
                        doctors=doctors_serialized,
                        icon_type=specialty.icon_code,
                    )
                )
            departments_serialized.append(
                DepartmentResponse(
                    id=department.id,
                    name=department.name,
                    description=department.description,
                    location_id=department.location_id,
                    specialities=specialties_serialized,
                )
            )
        locations_serialized.append(
            LocationResponse(
                id=location.id,
                name=location.name,
                description=location.description,
                departments=departments_serialized,
            ).model_dump()
        )

    return ORJSONResponse({"locations_serialized": locations_serialized})


@router.post("/add/", response_model=LocationResponse)
async def set_location(request: Request, session: SessionDep, location: LocationCreate):
    if not request.state.user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="scopes have not unauthorized",
        )

    try:
        new_location = Locations(
            name=location.name,
            description=location.description,
        )

        session.add(new_location)
        session.commit()
        session.refresh(new_location)

        return ORJSONResponse(
            LocationResponse(
                id=new_location.id,
                name=new_location.name,
                description=new_location.description,
            ).model_dump(),
            status_code=status.HTTP_201_CREATED,
        )

    except Exception as exc:  # pragma: no cover - mirrors existing behaviour
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.delete("/delete/{location_id}", response_model=LocationDelete)
async def delete_location(request: Request, location_id: UUID, session: SessionDep):
    if not request.state.user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="scopes have not unauthorized",
        )

    location = session.exec(select(Locations).where(Locations.id == location_id)).first()

    session.delete(location)
    session.commit()

    return ORJSONResponse(
        LocationDelete(
            id=location.id,
            message=f"Location {location.name} deleted",
        ).model_dump()
    )


@router.put("/update/{location_id}/", response_model=LocationResponse)
async def update_location(
    request: Request, location_id: UUID, session: SessionDep, location: LocationUpdate
):
    if not request.state.user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="scopes have not unauthorized",
        )

    new_location = session.exec(select(Locations).where(Locations.id == location_id)).first()

    new_location.name = location.name
    new_location.description = location.description

    session.add(new_location)
    session.commit()
    session.refresh(new_location)

    return ORJSONResponse(
        LocationResponse(
            id=new_location.id,
            name=new_location.name,
            description=new_location.description,
        ).model_dump()
    )


__all__ = ["router"]
