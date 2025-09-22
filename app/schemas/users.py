from datetime import datetime

from fastapi import UploadFile

from typing import Optional, List

from pydantic import BaseModel, EmailStr, constr, field_validator

from uuid import UUID

class UserBase(BaseModel):
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    dni: constr(min_length=8)
    telephone: Optional[str] = None
    address: Optional[str] = None
    blood_type: Optional[str] = None
    health_insurance: Optional[List[UUID]] = []

    @classmethod
    @field_validator("email", mode="before")
    def email_validator(cls, v: EmailStr):
        if v in ["ñ", "Ñ"]:
            raise ValueError("El valor de email no puede contener ñ.")
        return v

class UserCreate(UserBase):
    password: constr(min_length=8)
    img_profile: Optional[UploadFile] = None

class UserRead(UserBase):
    id: UUID
    is_active: bool
    is_admin: bool
    is_superuser: bool
    last_login: Optional[datetime] = None
    date_joined: datetime
    img_profile: Optional[str]

class UserUpdate(BaseModel):
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    address: Optional[str] = None
    telephone: Optional[str] = None
    health_insurance: Optional[List[str]] = []
    img_profile: Optional[UploadFile] = None

class UserHeathInsuranceUpdate(BaseModel):
    heath_insurance_id: Optional[List[UUID]] = []

class UserPasswordUpdate(BaseModel):
    old_password: constr(min_length=8)
    new_password: constr(min_length=8)
    new_password_confirm: constr(min_length=8)

class UserPetitionPasswordUpdate(BaseModel):
    email: EmailStr

class UserDelete(UserBase):
    id: UUID


class UserAuth(BaseModel):
    email: EmailStr
    password: constr(min_length=8)