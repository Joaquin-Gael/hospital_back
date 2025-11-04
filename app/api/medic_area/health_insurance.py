"""Health insurance routes."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import ORJSONResponse
from sqlmodel import select

from app.db.main import SessionDep
from app.models import HealthInsurance
from app.schemas.medica_area import (
    HealthInsuranceCreate,
    HealthInsuranceDelete,
    HealthInsuranceRead,
    HealthInsuranceUpdate,
)

from .common import auth_dependency, default_response_class


router = APIRouter(
    prefix="/health_insurance",
    tags=["health_insurance"],
    default_response_class=default_response_class,
    dependencies=[auth_dependency()],
)


@router.get("/", response_model=List[HealthInsuranceRead])
async def get_health_insurance(request: Request, session: SessionDep):
    result = session.exec(select(HealthInsurance)).all()

    serialized_heath_insurance: List[HealthInsuranceRead] = []
    for item in result:
        serialized_heath_insurance.append(
            HealthInsuranceRead(
                id=item.id,
                name=item.name,
                description=item.description,
                discount=item.discount,
            ).model_dump()
        )

    return serialized_heath_insurance


@router.get("/detail/{hi_id}", response_model=HealthInsuranceRead)
async def get_health_insurance_detail(
    request: Request, session: SessionDep, hi_id: UUID
):
    hi = session.get(HealthInsurance, hi_id)
    if not hi:
        raise HTTPException(status_code=404, detail="HealthInsurance not found")
    data = HealthInsuranceRead(
        id=hi.id,
        name=hi.name,
        description=hi.description,
        discount=hi.discount,
    ).model_dump()
    return data


@router.post(
    "/create",
    response_model=HealthInsuranceRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_health_insurance(
    request: Request, session: SessionDep, payload: HealthInsuranceCreate
):
    hi = HealthInsurance.model_validate(payload)
    session.add(hi)
    session.commit()
    session.refresh(hi)
    data = HealthInsuranceRead(
        id=hi.id,
        name=hi.name,
        description=hi.description,
        discount=hi.discount,
    ).model_dump()
    return data


@router.patch("/update/{hi_id}", response_model=HealthInsuranceRead)
async def update_health_insurance(
    request: Request,
    session: SessionDep,
    hi_id: UUID,
    payload: HealthInsuranceUpdate,
):
    hi = session.get(HealthInsurance, hi_id)
    if not hi:
        raise HTTPException(status_code=404, detail="HealthInsurance not found")
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(hi, key, value)
    session.add(hi)
    session.commit()
    session.refresh(hi)
    data = HealthInsuranceRead(
        id=hi.id,
        name=hi.name,
        description=hi.description,
        discount=hi.discount,
    ).model_dump()
    return data


@router.delete("/delete/{hi_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_health_insurance(
    request: Request, session: SessionDep, hi_id: UUID
):
    hi = session.get(HealthInsurance, hi_id)
    if not hi:
        raise HTTPException(status_code=404, detail="HealthInsurance not found")
    session.delete(hi)
    session.commit()
    return ORJSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)


__all__ = ["router"]
