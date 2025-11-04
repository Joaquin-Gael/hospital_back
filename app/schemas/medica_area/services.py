from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ServiceBase(BaseModel):
    name: str
    description: str
    price: float
    specialty_id: UUID
    icon_code: Optional[str] = None


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    icon_code: Optional[str] = None
    specialty_id: Optional[UUID] = None


class ServiceResponse(ServiceBase):
    id: UUID
    specialty: Optional["SpecialtyResponse"] = None


class ServiceDelete(BaseModel):
    id: UUID
    message: str
