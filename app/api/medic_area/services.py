"""Service related routes."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import ORJSONResponse
from sqlmodel import select

from app.db.main import SessionDep
from app.models import Services
from app.schemas.medica_area import ServiceCreate, ServiceDelete, ServiceResponse, ServiceUpdate

from .common import auth_dependency, console, default_response_class


router = APIRouter(
    prefix="/services",
    tags=["services"],
    default_response_class=default_response_class,
    dependencies=[auth_dependency()],
)


@router.get("/", response_model=List[ServiceResponse])
async def get_services(request: Request, session: SessionDep):
    result = session.exec(select(Services).where(True)).all()
    services_serialized = [
        ServiceResponse(
            id=service.id,
            name=service.name,
            description=service.description,
            price=service.price,
            specialty_id=service.specialty_id,
            icon_code=service.icon_code,
        ).model_dump()
        for service in result
    ]

    return ORJSONResponse(services_serialized, status_code=status.HTTP_200_OK)


@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service_by_id(request: Request, service_id: UUID, session: SessionDep):
    service = session.get(Services, service_id)
    return ORJSONResponse(
        ServiceResponse(
            id=service.id,
            name=service.name,
            description=service.description,
            price=service.price,
            specialty_id=service.specialty_id,
            icon_code=service.icon_code,
        ).model_dump(),
        status_code=status.HTTP_200_OK,
    )


@router.post("/add", response_model=ServiceResponse)
async def set_service(request: Request, session: SessionDep, service: ServiceCreate):
    if not request.state.user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="scopes have not unauthorized",
        )

    try:
        new_service = Services(
            name=service.name,
            description=service.description,
            price=service.price,
            specialty_id=service.specialty_id,
            icon_code=service.icon_code,
        )

        session.add(new_service)
        session.commit()
        session.refresh(new_service)

        return ORJSONResponse(
            ServiceResponse(
                id=new_service.id,
                name=service.name,
                description=service.description,
                price=service.price,
                specialty_id=service.specialty_id,
                icon_code=service.icon_code,
            ).model_dump()
        )
    except Exception as exc:  # pragma: no cover - legacy behaviour
        console.print_exception(show_locals=True)
        return ORJSONResponse({"error": str(exc)}, status_code=status.HTTP_400_BAD_REQUEST)


@router.delete("/delete/{service_id}", response_model=ServiceDelete)
async def delete_service(request: Request, session: SessionDep, service_id: UUID):
    try:
        service = session.exec(select(Services).where(Services.id == service_id)).first()

        session.delete(service)
        session.commit()

        return ORJSONResponse(
            ServiceDelete(
                id=service.id,
                message=f"Service {service.name} has been deleted",
            ).model_dump()
        )
    except Exception as exc:  # pragma: no cover - legacy behaviour
        console.print_exception(show_locals=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.patch("/update/{service_id}/", response_model=ServiceResponse)
async def update_service(
    request: Request, session: SessionDep, service_id: UUID, service: ServiceUpdate
):
    if not request.state.user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="scopes have not unauthorized",
        )

    new_service = session.exec(select(Services).where(Services.id == service_id)).first()

    fields = service.__fields__.keys()

    for field in fields:
        value = getattr(service, field)
        if value is not None:
            setattr(new_service, field, value)

    session.add(new_service)
    session.commit()
    session.refresh(new_service)

    return ORJSONResponse(
        ServiceResponse(
            id=new_service.id,
            name=new_service.name,
            description=new_service.description,
            price=new_service.price,
            specialty_id=new_service.specialty_id,
            icon_code=new_service.icon_code,
        ).model_dump()
    )


__all__ = ["router"]
