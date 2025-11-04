from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, constr, field_validator


class DoctorBase(BaseModel):
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    dni: constr(min_length=8)
    telephone: Optional[str] = None
    speciality_id: UUID
    address: Optional[str] = None
    blood_type: Optional[str] = None
    doctor_state: Optional[str] = None


class DoctorCreate(DoctorBase):
    password: constr(min_length=8)


class DoctorUpdate(BaseModel):
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    doctor_state: Optional[str] = None

    @classmethod
    @field_validator("email", mode="before")
    def email_validator(cls, value: EmailStr):
        if "ñ" in value or "Ñ" in value:
            raise ValueError("El valor de email no puede contener ñ.")
        return value


class DoctorPasswordUpdate(BaseModel):
    password: constr(min_length=8)


class DoctorSpecialityUpdate(BaseModel):
    speciality_id: Optional[UUID] = None


class DoctorResponse(DoctorBase):
    id: UUID
    is_active: bool
    is_admin: Optional[bool] = None
    is_superuser: Optional[bool] = None
    last_login: Optional[datetime] = None
    date_joined: Optional[datetime]
    email: Optional[str] = None
    schedules: Optional[List["MedicalScheduleResponse"]] = None


class DoctorDelete(BaseModel):
    id: UUID
    message: str


class DoctorAuth(BaseModel):
    email: EmailStr
    password: constr(min_length=8)

    @classmethod
    @field_validator("email", mode="before")
    def email_validator(cls, value: EmailStr):
        if "ñ" in value or "Ñ" in value:
            raise ValueError("El valor de email no puede contener ñ.")
        return value
