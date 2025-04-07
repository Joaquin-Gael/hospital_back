from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, constr

class UserBase(BaseModel):
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserCreate(UserBase):
    password: constr(min_length=8)  # Requiere mínimo 8 caracteres

class UserRead(UserBase):
    id: int
    is_active: bool
    is_staff: bool
    is_superuser: bool
    last_login: Optional[datetime] = None
    date_joined: datetime

    class Config:
        orm_mode = True

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: Optional[constr(min_length=8)] = None
    is_active: Optional[bool] = None
    is_staff: Optional[bool] = None
    is_superuser: Optional[bool] = None

    class Config:
        orm_mode = True