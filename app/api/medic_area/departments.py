"""Department related routes."""
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import ORJSONResponse
from sqlmodel import select

from app.db.main import SessionDep
from app.models import Departments, Doctors, Services, Specialties
from app.schemas.medica_area import (
    DepartmentCreate,
    DepartmentDelete,
    DepartmentResponse,
    DepartmentUpdate,
    DoctorResponse,
    ServiceResponse,
    SpecialtyDelete,
    SpecialtyResponse,
)

from .common import auth_dependency, console, default_response_class


router = APIRouter(
    prefix="/departments",
    tags=["departments"],
    default_response_class=default_response_class,
    dependencies=[auth_dependency()],
)


@router.get("/", response_model=DepartmentResponse)
async def get_departments(request: Request, session: SessionDep):
    result = session.exec(select(Departments)).all()

    departments_list: List[DepartmentResponse] = []
    for department in result:
        specialities_list = []
        for speciality in department.specialities:
            services_list = [
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
            doctors_list = [
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
                for doc in speciality.doctors
            ]
            specialities_list.append(
                SpecialtyResponse(
                    id=speciality.id,
                    name=speciality.name,
                    description=speciality.description,
                    department_id=department.id,
                    services=services_list,
                    doctors=doctors_list,
                    icon_type=speciality.icon_code,
                )
            )

        departments_list.append(
            DepartmentResponse(
                id=department.id,
                name=department.name,
                description=department.description,
                location_id=department.location_id,
                specialities=specialities_list,
            ).model_dump()
        )

    return ORJSONResponse(departments_list)


@router.get("/{department_id}/", response_model=DepartmentResponse)
async def get_department_by_id(
    request: Request, department_id: UUID, session: SessionDep
):
    department = session.exec(
        select(Departments).where(Departments.id == department_id)
    ).first()

    specialities_list = []
    for speciality in department.specialities:
        specialities_list.append(
            SpecialtyResponse(
                id=speciality.id,
                name=speciality.name,
                description=speciality.description,
                department_id=department.id,
            )
        )

    return DepartmentResponse(
        id=department.id,
        name=department.name,
        description=department.description,
        location_id=department.location_id,
        specialities=specialities_list,
    ).model_dump()


@router.post("/add/", response_model=DepartmentResponse)
async def add_department(
    request: Request, department: DepartmentCreate, session: SessionDep
):
    if not request.state.user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized"
        )

    new_department = Departments(
        name=department.name,
        description=department.description,
        location_id=department.location_id,
    )

    session.add(new_department)
    session.commit()
    session.refresh(new_department)

    return DepartmentResponse(
        id=new_department.id,
        name=new_department.name,
        description=new_department.description,
        location_id=new_department.location_id,
    ).model_dump()


@router.delete("/delete/{department_id}/", response_model=DepartmentDelete)
async def delete_department_by_id(
    request: Request, department_id: UUID, session: SessionDep
):
    if not request.state.user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="scopes have not unauthorized",
        )

    try:
        department = session.exec(
            select(Departments).where(Departments.id == department_id)
        ).first()

        session.delete(department)
        session.commit()

        return DepartmentDelete(
            id=department.id,
            message=f"Department {department.name} has been deleted",
        ).model_dump()

    except Exception as exc:  # pragma: no cover - mirrors existing behaviour
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department {department_id} not found",
        ) from exc


@router.delete(
    "/delete/{department_id}/specialities/{speciality_id}/",
    response_model=SpecialtyDelete,
)
async def delete_speciality_by_id(
    request: Request,
    department_id: UUID,
    speciality_id: UUID,
    session: SessionDep,
):
    if not request.state.user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="scopes have not unauthorized",
        )

    try:
        result = session.execute(
            select(Departments).where(Departments.id == department_id)
        ).scalars().first()
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Department {department_id} not found",
            )
        for speciality in result.specialities:
            if speciality.id == speciality_id:
                session.delete(speciality)
                session.commit()
                return SpecialtyDelete(
                    id=speciality.id,
                    message=f"Speciality {speciality.name} has been deleted",
                )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Speciality {speciality_id} not found",
        )
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - keeps legacy behaviour
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Speciality {speciality_id} not found",
        ) from exc


@router.patch("/update/{department_id}/", response_model=DepartmentResponse)
async def update_department(
    request: Request,
    department_id: UUID,
    department: DepartmentUpdate,
    session: SessionDep,
):
    if not request.state.user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized"
        )

    new_department = session.exec(
        select(Departments).where(Departments.id == department_id)
    ).first()

    new_department.name = department.name
    new_department.description = department.description
    new_department.location_id = department.location_id

    session.add(new_department)
    session.commit()
    session.refresh(new_department)

    return DepartmentResponse(
        id=new_department.id,
        name=new_department.name,
        description=new_department.description,
        location_id=new_department.location_id,
    ).model_dump()


__all__ = ["router"]
