from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class DepartmentBase(BaseModel):
    name: str
    description: str
    location_id: UUID


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location_id: Optional[UUID] = None


class DepartmentResponse(DepartmentBase):
    id: UUID
    specialities: Optional[List["SpecialtyResponse"]] = []
    location: Optional["LocationResponse"] = None


class DepartmentDelete(BaseModel):
    id: UUID
    message: str
