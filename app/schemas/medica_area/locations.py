from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class LocationBase(BaseModel):
    name: str
    description: str


class LocationCreate(LocationBase):
    pass


class LocationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class LocationResponse(LocationBase):
    id: UUID
    departments: Optional[List["DepartmentResponse"]] = []


class LocationDelete(BaseModel):
    id: UUID
    message: str
