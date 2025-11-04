from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, condecimal, constr


class HealthInsuranceBase(BaseModel):
    name: constr(max_length=50)
    description: constr(max_length=500)
    discount: condecimal(ge=0, le=100, max_digits=5, decimal_places=2) = 0


class HealthInsuranceCreate(HealthInsuranceBase):
    pass


class HealthInsuranceUpdate(BaseModel):
    name: Optional[constr(max_length=50)] = None
    description: Optional[constr(max_length=500)] = None
    discount: Optional[condecimal(ge=0, le=100, max_digits=5, decimal_places=2)] = None


class HealthInsuranceRead(HealthInsuranceBase):
    id: UUID


class HealthInsuranceDelete(BaseModel):
    id: UUID
    message: str
