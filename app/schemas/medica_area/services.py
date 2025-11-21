from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


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
    is_available: bool = True
    available_doctors_count: Optional[int] = Field(default=None, ge=0)

    @model_validator(mode="after")
    def set_availability_from_count(self):
        if self.available_doctors_count is not None:
            self.is_available = self.available_doctors_count > 0
        return self


class ServiceDelete(BaseModel):
    id: UUID
    message: str
