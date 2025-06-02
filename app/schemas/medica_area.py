from enum import Enum

from typing import Optional, List

from datetime import time as time_type, date as date_type

from pydantic import BaseModel, EmailStr, constr, ValidationError, field_validator

from datetime import datetime

from uuid import UUID

from app.schemas import UserRead


# Definición del enumerado para los días de la semana
class DayOfWeek(str, Enum):
    monday = "Monday"
    tuesday = "Tuesday"
    wednesday = "Wednesday"
    thursday = "Thursday"
    friday = "Friday"
    saturday = "Saturday"
    sunday = "Sunday"

class TurnsState(str, Enum):
    waiting = "waiting"
    finished = "finished"
    cancelled = "cancelled"
    rejected = "rejected"
    accepted = "accepted"

# ------------------------ LOCATIONS ------------------------

# Modelo base (campos compartidos)
class LocationBase(BaseModel):
    name: str
    description: str

# Modelo para la creación: hereda del base
class LocationCreate(LocationBase):
    pass

# Modelo para la edición: campos opcionales
class LocationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class LocationResponse(LocationBase):
    id: UUID
    departments: Optional[List["DepartmentResponse"]] = []


class LocationDelete(BaseModel):
    id: UUID
    message: str

# ------------------------ DEPARTMENTS ------------------------

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

    #class Config:
    #    orm_mode = True

class DepartmentDelete(BaseModel):
    id: UUID
    message: str

# ------------------------ SPECIALTIES ------------------------

class SpecialtyBase(BaseModel):
    name: str
    description: str
    department_id: UUID

class SpecialtyCreate(SpecialtyBase):
    pass

class SpecialtyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    department_id: Optional[str] = None

class SpecialtyResponse(SpecialtyBase):
    id: UUID
    services: Optional[List["ServiceResponse"]] = []
    doctors: Optional[List["DoctorResponse"]] = []

    #class Config:
    #    orm_mode = True

class SpecialtyDelete(BaseModel):
    id: UUID
    message: str

# ------------------------ SERVICES ------------------------

class ServiceBase(BaseModel):
    name: str
    description: str
    price: float
    specialty_id: UUID

class ServiceCreate(ServiceBase):
    pass

class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    specialty_id: Optional[UUID] = None

class ServiceResponse(ServiceBase):
    id: UUID

    #class Config:
    #   orm_mode = True

class ServiceDelete(BaseModel):
    id: UUID
    message: str

# ------------------------ DOCTORS ------------------------

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

class DoctorCreate(DoctorBase):
    password: constr(min_length=8)
    pass

class DoctorUpdate(BaseModel):
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None

    @classmethod
    @field_validator("email", mode="before")
    def email_validator(cls, v: EmailStr):
        if "ñ" in v or "Ñ" in v:
            raise ValueError("El valor de email no puede contener ñ.")
        return v

class DoctorPasswordUpdate(BaseModel):
    password: constr(min_length=8)

class DoctorSpecialityUpdate(BaseModel):
    speciality_id: Optional[UUID] = None

class DoctorResponse(DoctorBase):
    id: UUID
    is_active: bool
    is_admin: bool
    is_superuser: bool
    last_login: Optional[datetime] = None
    date_joined: datetime
    email: Optional[str] = None

    #class Config:
    #    orm_mode = True

class DoctorDelete(BaseModel):
    id: UUID
    message: str

class DoctorAuth(BaseModel):
    email: EmailStr
    password: str

# ------------------------ MEDICAL SCHEDULES ------------------------

class MedicalScheduleBase(BaseModel):
    day: DayOfWeek
    start_time: time_type
    end_time: time_type

class MedicalScheduleCreate(MedicalScheduleBase):
    pass

class MedicalScheduleUpdate(BaseModel):
    day: Optional[DayOfWeek | str] = None
    start_time: Optional[time_type] = None
    end_time: Optional[time_type] = None

    @classmethod
    @field_validator("start_time", mode="before")
    def validate_day(cls, v: time_type):
        if v.hour < 0 or v.hour > 23:
            raise ValueError("El valor de start_time debe estar entre 0 y 23.")
        if v.minute < 0 or v.minute > 59:
            raise ValueError("El valor de start_time debe estar entre 0 y 59.")
        if v.second < 0 or v.second > 59:
            raise ValueError("El valor de start_time debe estar entre 0 y 59.")

        if v > cls.end_time:
            raise ValueError("El valor de start_time debe ser menor que end_time.")

        return v

    @classmethod
    @field_validator("start_time", mode="before")
    def validate_day(cls, v: time_type):
        if v.hour < 0 or v.hour > 23:
            raise ValueError("El valor de start_time debe estar entre 0 y 23.")
        if v.minute < 0 or v.minute > 59:
            raise ValueError("El valor de start_time debe estar entre 0 y 59.")
        if v.second < 0 or v.second > 59:
            raise ValueError("El valor de start_time debe estar entre 0 y 59.")

        if v < cls.start_time:
            raise ValueError("El valor de end_time debe ser mayor que start_time.")

        return v

class MedicalScheduleResponse(MedicalScheduleBase):
    id: UUID
    doctors: Optional[List[DoctorResponse]] = None

    #class Config:
    #    orm_mode = True

class MedicalScheduleDelete(BaseModel):
    id: UUID
    message: str

# -------------------------- MEDICAL CHATS -------------------------------------

class MessageBase(BaseModel):
    id: UUID
    content: str
    created_at: datetime
    deleted_at: datetime

class MessageResponse(MessageBase):
    sender: Optional[DoctorResponse] = None
    chat: Optional["ChatResponse"] = None

class ChatBase(BaseModel):
    id: UUID

class ChatResponse(ChatBase):
    doc_2: Optional["DoctorResponse"] = None
    doc_1: Optional["DoctorResponse"] = None
    messages: Optional[List["MessageResponse"]] = None

# --------------------------------- TURNS -------------------------------------

class TurnsBase(BaseModel):
    id: UUID
    reason: Optional[str] = None
    state: TurnsState
    date: date_type
    date_created: date_type
    user_id: Optional[UUID] = None
    doctor_id: Optional[UUID] = None
    service_id: Optional[UUID] = None
    appointment_id: Optional[UUID] = None
    date_limit: date_type

class TurnsCreate(TurnsBase):
    pass

class TurnsUpdate(BaseModel):
    id: Optional[UUID] = None
    reason: Optional[str] = None
    state: Optional[TurnsState] = None
    date: Optional[date_type] = None
    date_created: Optional[date_type] = None

class TurnsResponse(TurnsBase):
    user: Optional["UserRead"] = None
    doctor: Optional["DoctorResponse"] = None
    service: Optional["ServiceResponse"] = None
    appointment: Optional["AppointmentResponse"] = None

class TurnsDelete(BaseModel):
    id: UUID
    message: str

# ------------------------------ APPOINTMENTS ----------------------------------

class AppointmentBase(BaseModel):
    id: UUID
    reason: Optional[str] = None
    state: TurnsState
    date: date_type
    date_created: date_type
    user_id: Optional[UUID] = None
    doctor_id: Optional[UUID] = None
    service_id: Optional[UUID] = None
    appointment_id: Optional[UUID] = None
    date_limit: date_type

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentUpdate(BaseModel):
    id: Optional[UUID] = None
    reason: Optional[str] = None
    state: Optional[TurnsState] = None
    date: Optional[date_type] = None
    date_created: Optional[date_type] = None

class AppointmentResponse(AppointmentBase):
    user: Optional["UserRead"] = None
    doctor: Optional["DoctorResponse"] = None
    service: Optional["ServiceResponse"] = None
    turn: Optional["TurnsResponse"] = None

class AppointmentDelete(BaseModel):
    id: UUID
    message: str


# ------------------------ ACTUALIZACIÓN DE REFERENCIAS ------------------------
# Debido a las relaciones circulares, es importante actualizar los forward refs.
LocationResponse.model_rebuild()
DepartmentResponse.model_rebuild()
SpecialtyResponse.model_rebuild()
ServiceResponse.model_rebuild()
DoctorResponse.model_rebuild()
MedicalScheduleResponse.model_rebuild()
ChatResponse.model_rebuild()
MessageResponse.model_rebuild()
TurnsResponse.model_rebuild()
AppointmentResponse.model_rebuild()