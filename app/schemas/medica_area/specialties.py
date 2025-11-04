from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class SpecialtyBase(BaseModel):
    name: str
    description: str
    department_id: UUID


class SpecialtyCreate(SpecialtyBase):
    pass


class SpecialtyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    department_id: Optional[UUID] = None


class SpecialtyResponse(SpecialtyBase):
    id: UUID
    services: Optional[List["ServiceResponse"]] = []
    doctors: Optional[List["DoctorResponse"]] = []
    department: Optional["DepartmentResponse"] = None


class SpecialtyDelete(BaseModel):
    id: UUID
    message: str
