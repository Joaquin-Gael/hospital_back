from enum import Enum
from typing import Optional, List
from datetime import time
from pydantic import BaseModel, EmailStr, constr
from datetime import datetime


# Definición del enumerado para los días de la semana
class DayOfWeek(str, Enum):
    monday = "Monday"
    tuesday = "Tuesday"
    wednesday = "Wednesday"
    thursday = "Thursday"
    friday = "Friday"
    saturday = "Saturday"
    sunday = "Sunday"

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

# Modelo de respuesta: incluye id y relaciones (en este caso, la lista de departamentos)
class LocationResponse(LocationBase):
    id: str
    departments: Optional[List["DepartmentResponse"]] = []

    class Config:
        orm_mode = True

# Modelo de eliminación (puede usarse para responder con un mensaje de confirmación)
class LocationDelete(BaseModel):
    id: str
    message: str

# ------------------------ DEPARTMENTS ------------------------

class DepartmentBase(BaseModel):
    name: str
    description: str
    location_id: str

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location_id: Optional[str] = None

class DepartmentResponse(DepartmentBase):
    id: str
    specialities: Optional[List["SpecialtyResponse"]] = []

    class Config:
        orm_mode = True

class DepartmentDelete(BaseModel):
    id: str
    message: str

# ------------------------ SPECIALTIES ------------------------

class SpecialtyBase(BaseModel):
    name: str
    description: str
    department_id: str

class SpecialtyCreate(SpecialtyBase):
    pass

class SpecialtyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    department_id: Optional[str] = None

class SpecialtyResponse(SpecialtyBase):
    id: str
    services: Optional[List["ServiceResponse"]] = []
    doctors: Optional[List["DoctorResponse"]] = []

    class Config:
        orm_mode = True

class SpecialtyDelete(BaseModel):
    id: str
    message: str

# ------------------------ SERVICES ------------------------

class ServiceBase(BaseModel):
    name: str
    description: str
    price: float
    specialty_id: str

class ServiceCreate(ServiceBase):
    pass

class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    specialty_id: Optional[str] = None

class ServiceResponse(ServiceBase):
    id: str

    class Config:
        orm_mode = True

class ServiceDelete(BaseModel):
    id: str
    message: str

# ------------------------ DOCTORS ------------------------

class DoctorBase(BaseModel):
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    dni: str
    telephone: Optional[str] = None
    speciality_id: str

class DoctorCreate(DoctorBase):
    password: str
    pass

class DoctorUpdate(BaseModel):
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: Optional[constr(min_length=8)] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    is_superuser: Optional[bool] = None
    telephone: Optional[str] = None
    speciality_id: Optional[str] = None
    email: Optional[str] = None

class DoctorResponse(DoctorBase):
    id: str
    is_active: bool
    is_admin: bool
    is_superuser: bool
    last_login: Optional[datetime] = None
    date_joined: datetime
    email: Optional[str] = None

    class Config:
        orm_mode = True

class DoctorDelete(BaseModel):
    id: str
    message: str

class DoctorAuth(BaseModel):
    email: EmailStr
    password: str

# ------------------------ MEDICAL SCHEDULES ------------------------

class MedicalScheduleBase(BaseModel):
    day: DayOfWeek
    time_medic: time

class MedicalScheduleCreate(MedicalScheduleBase):
    pass

class MedicalScheduleUpdate(BaseModel):
    day: Optional[DayOfWeek] = None
    time_medic: Optional[time] = None

class MedicalScheduleResponse(MedicalScheduleBase):
    id: str
    doctors: Optional[List[DoctorResponse]] = []

    class Config:
        orm_mode = True

class MedicalScheduleDelete(BaseModel):
    id: str
    message: str

# ------------------------ ACTUALIZACIÓN DE REFERENCIAS ------------------------
# Debido a las relaciones circulares, es importante actualizar los forward refs.
LocationResponse.model_rebuild()
DepartmentResponse.model_rebuild()
SpecialtyResponse.model_rebuild()
ServiceResponse.model_rebuild()
DoctorResponse.model_rebuild()
MedicalScheduleResponse.model_rebuild()
