from pathlib import Path

from fastapi import UploadFile
from sqlmodel import SQLModel, Field, Relationship

from sqlalchemy import Column, UUID as UUID_TYPE, VARCHAR
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import declarative_mixin

from typing import Optional, List

from passlib.context import CryptContext

import uuid
from uuid import UUID, uuid4

from datetime import time, datetime, timedelta
from datetime import date as date_type, time as time_type

from enum import Enum

import re

import os
from dotenv import load_dotenv

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class DoctorStates(str, Enum):
    available = "available",
    busy = "busy",
    offline = "offline"

class DayOfWeek(str, Enum):
    monday = "monday"
    tuesday = "tuesday"
    wednesday = "wednesday"
    thursday = "thursday"
    friday = "friday"
    saturday = "saturday"
    sunday = "sunday"

class TurnsState(str, Enum):
    waiting = "waiting"
    finished = "finished"
    cancelled = "cancelled"
    rejected = "rejected"
    accepted = "accepted"

@declarative_mixin
class RenameTurnsStateMixin:
    @classmethod
    def __declare_last__(cls):
        for col in list(cls.__table__.columns):
            if col.name == "state":
                col.name = f"{cls.__table__.name}_state"

class PasswordError(Exception):
    """Exception raised for errors in password validation."""
    def __init__(self, message: str = "Invalid password"):
        super().__init__(message)
        self.message = message

class BaseUser(SQLModel, table=False):
    name: str = Field(
        sa_type=VARCHAR(length=32),
        max_length=50,
        sa_column_kwargs={"name":"username"}
    )
    email: str = Field(unique=True, index=True)
    first_name: Optional[str] = Field(nullable=True)
    last_name: Optional[str] = Field(nullable=True)
    password: str = Field()
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    is_superuser: bool = Field(default=False)
    last_login: Optional[datetime] = Field(nullable=True)
    date_joined: datetime = Field(default_factory=datetime.now)
    dni: str = Field(max_length=8)
    telephone: Optional[str] = Field(max_length=50)
    address: Optional[str] = Field(nullable=True)
    blood_type: Optional[str] = Field(nullable=True)
    url_image_profile: Optional[str] = Field(nullable=True)

    def set_url_image_profile(self, file_name: str):
        self.url_image_profile = f"{os.getenv("DOMINIO")}/media/{self.__class__.__name__.lower()}/{file_name}"

    async def save_profile_image(self, file: UploadFile | None, media_root: str = "media"):
        if file is None:
            return
        
        cls_name = self.__class__.__name__.lower()
        
        try:
            if self.url_image_profile:
                os.remove(self.url_image_profile)
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Error removing old profile image: {e}")

        folder_path = Path(media_root) / cls_name
        folder_path.mkdir(parents=True, exist_ok=True)

        ext = file.filename.split(".")[-1]
        unique_name = f"{uuid4().hex}.{ext}"
        file_path = folder_path / unique_name

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        self.set_url_image_profile(unique_name)

    def set_password(self, raw_password: str):
        """
        sets a password for the user after validating against a specific pattern for
        security. The password must match the defined security requirements for
        complexity. Once validated, it hashes the password using a secure hashing
        algorithm and stores it.

        :param raw_password: The plain text password to be set. The password must
            meet the following criteria: at least one lowercase letter, one uppercase
            letter, one numeral, one special character, and a minimum length of 8 characters.
        :type raw_password: Str
        :return: None
        :raises ValueError: If the provided raw_password does not meet the required
            pattern for password complexity.
        """
        pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#])[A-Za-z\d@$!%*?&#]{8,}$'
        if re.match(pattern, raw_password) is None:
            raise PasswordError(message=f"value: {raw_password} does not match the required pattern")

        self.password = pwd_context.hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        """Verifica la contraseña en texto plano contra el hash almacenado."""
        return pwd_context.verify(raw_password, self.password)

    def get_full_name(self) -> str:
        """Devuelve el nombre completo del usuario."""
        full_name = f"{self.first_name or ''} {self.last_name or ''}".strip()
        return full_name if full_name else self.username

    def get_short_name(self) -> str:
        """Devuelve el nombre corto del usuario."""
        return self.first_name if self.first_name else self.username

    def make_superuser(self) -> bool:
        self.is_superuser = True
        self.is_admin = True
        return True

    def make_normal_user(self) -> bool:
        self.is_superuser = False
        self.is_admin = False
        return True

    def ban(self) -> bool:
        self.is_active = False
        return True

    def des_ban(self) -> bool:
        self.is_active = True
        return True

class BaseModelTurns(SQLModel, RenameTurnsStateMixin, table=False):
    reason: str = Field(nullable=True, default=None)
    state: TurnsState = Field(
        default=TurnsState.waiting,
        sa_type=SQLEnum(TurnsState),
        nullable=False
    )
    date: date_type = Field(nullable=False)
    date_created: date_type = Field(default_factory=date_type.today)
    date_limit: date_type = Field(nullable=False)
    time: date_type = Field(nullable=False, default=datetime.now().time())
    user_id: Optional[UUID] = Field(
        sa_type=UUID_TYPE,
        foreign_key="users.user_id",
        nullable=True,
    )
    doctor_id: Optional[UUID] = Field(
        sa_type=UUID_TYPE,
        foreign_key="doctors.doctor_id",
        nullable=True,
    )

# LINKS ---------------------------------------------------------------
class DoctorMedicalScheduleLink(SQLModel, table=True):
    __tablename__ = "doctor_medical_schedule_link"
    doctor_id: UUID = Field(
        foreign_key="doctors.doctor_id",
        primary_key=True,
        ondelete="CASCADE"
    )
    medical_schedule_id: UUID = Field(
        foreign_key="medical_schedules.medical_schedule_id",
        primary_key=True,
        ondelete="CASCADE"
    )

class TurnsServicesLink(SQLModel, table=True):
    __tablename__ = 'turns_services_link'

    turn_id: UUID = Field(
        foreign_key='turns.turn_id',
        primary_key=True,
        ondelete='CASCADE'
    )

    service_id: UUID = Field(
        foreign_key='services.service_id',
        primary_key=True,
        ondelete='CASCADE'
    )

class UserHealthInsuranceLink(SQLModel, table=True):
    __tablename__ = "user_health_insurance_link"
    user_id: UUID = Field(
        foreign_key="users.user_id",
        primary_key=True,
        ondelete="CASCADE"
    )
    health_insurance_id: UUID = Field(
        foreign_key="health_insurance.health_insurance_id",
        primary_key=True,
        ondelete="CASCADE"
    )

# MODELS -------------------------------------------------------------
class Turns(BaseModelTurns, table=True):
    id: UUID = Field(
        sa_type=UUID_TYPE,
        sa_column_kwargs={"name":"turn_id"},
        default_factory=uuid4,
        primary_key=True,
        unique=True
    )
    user: Optional["User"] = Relationship(back_populates="turns")
    doctor: Optional["Doctors"] = Relationship(back_populates="turns")
    services: List["Services"] = Relationship(
        back_populates="turns",
        link_model=TurnsServicesLink
    )

    appointment: Optional["Appointments"] = Relationship(back_populates="turn")

    def get_details(self) -> dict[str, list]:
        details: dict = {
            "products_data": [],
            "turn_id": self.id
        }

        for service in self.services:
            details["products_data"]\
                .append(
                {
                    "name": service.name,
                    "description": service.description,
                    "quantity": 1,
                    "price": service.price
                }
            )

        return details


    def price_total(self) -> float:
        total:float = 0.0
        for service in self.services:
            total += service.price

        return total

class Appointments(SQLModel, table=True):
    id: UUID = Field(
        sa_type=UUID_TYPE,
        sa_column_kwargs={"name":"appointment_id"},
        default_factory=uuid4,
        primary_key=True,
        unique=True
    )
    user_id: Optional[UUID] = Field(
        sa_type=UUID_TYPE,
        foreign_key="users.user_id",
        nullable=True,
    )
    doctor_id: Optional[UUID] = Field(
        sa_type=UUID_TYPE,
        foreign_key="doctors.doctor_id",
        nullable=True,
    )
    user: Optional["User"] = Relationship(back_populates="appointments")
    doctor: Optional["Doctors"] = Relationship(back_populates="appointments")

    turn_id: Optional[UUID] = Field(
        sa_type=UUID_TYPE,
        foreign_key="turns.turn_id",
        nullable=True,
    )
    turn: Optional["Turns"] = Relationship(back_populates="appointment")

    cash: Optional["Cashes"] = Relationship(back_populates="appointments")

    def get_monetary_gain(self) -> float:
        pass


class Cashes(SQLModel, table=True):
    id: UUID = Field(
        sa_type=UUID_TYPE,
        sa_column_kwargs={"name":"cash_id"},
        default_factory=uuid4,
        primary_key=True,
        unique=True
    )
    income: float = Field(default=0, nullable=False)
    expense: float = Field(default=0, nullable=False)
    date: date_type = Field(nullable=False)
    time_transaction: time_type = Field(nullable=False, default=datetime.now().time())
    balance: float = Field(default=0, nullable=False)

    appointment_id: UUID = Field(foreign_key="appointments.appointment_id")
    appointments: Optional["Appointments"] = Relationship(back_populates="cash")

    details: List["CashesDetails"] = Relationship(
        back_populates="cash",
        cascade_delete=True,
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    def make_balance(self):
        self.balance = self.income - self.expense

class CashesDetails(SQLModel, table=True):
    id: UUID = Field(
        sa_type=UUID_TYPE,
        sa_column_kwargs={"name":"cash_details_id", "comment": "The primary key of the cash_details table"},
        default_factory=uuid4,
        primary_key=True,
        unique=True
    )
    description: str = Field(max_length=50)
    amount: float = Field(default=0, nullable=False)
    date: date_type = Field(nullable=False)
    time_transaction: time_type = Field(nullable=False, default=datetime.now().time())

    service_id: UUID = Field(foreign_key="services.service_id")
    service: Optional["Services"] = Relationship(back_populates="details")

    cash_id: UUID = Field(foreign_key="cashes.cash_id")
    cash: Optional["Cashes"] = Relationship(back_populates="details")

class Locations(SQLModel, table=True):
    id: UUID = Field(
        sa_type=UUID_TYPE,
        sa_column_kwargs={"name":"location_id"},
        default_factory=uuid.uuid4,
        primary_key=True,
        unique=True
    )
    name: str = Field(max_length=50)
    description: str = Field(max_length=500)
    departments: List["Departments"] = Relationship(back_populates="location")


class Departments(SQLModel, table=True):
    id: UUID = Field(
        sa_type=UUID_TYPE,
        sa_column_kwargs={"name":"department_id"},
        default_factory=uuid.uuid4,
        primary_key=True
    )
    name: str = Field(max_length=50)
    description: str = Field(max_length=500)
    location: Optional["Locations"] = Relationship(back_populates="departments")
    location_id: UUID = Field(foreign_key="locations.location_id", ondelete="CASCADE")
    specialities: List["Specialties"] = Relationship(back_populates="departament")


class Specialties(SQLModel, table=True):
    id: UUID = Field(
        sa_type=UUID_TYPE,
        sa_column_kwargs={"name":"specialty_id"},
        default_factory=uuid.uuid4,
        primary_key=True,
    )
    name: str = Field(max_length=50)
    description: str = Field(max_length=500)
    departament: Optional["Departments"] = Relationship(back_populates="specialities")
    department_id: UUID = Field(foreign_key="departments.department_id", ondelete="CASCADE")
    services: List["Services"] = Relationship(back_populates="speciality")
    doctors: List["Doctors"] = Relationship(back_populates="speciality")

class Services(SQLModel, table=True):
    id: UUID = Field(
        sa_type=UUID_TYPE,
        sa_column_kwargs={"name":"service_id"},
        default_factory=uuid.uuid4,
        primary_key=True
    )
    name: str = Field(max_length=50)
    description: str = Field(max_length=500)
    price: float = Field(default=0, nullable=False)

    speciality: Optional["Specialties"] = Relationship(back_populates="services")
    specialty_id: UUID = Field(foreign_key="specialties.specialty_id", ondelete="CASCADE")

    turns: List["Turns"] = Relationship(
        back_populates="services",
        link_model=TurnsServicesLink
    )
    #appointments: List["Appointments"] = Relationship(back_populates="service")
    details: List["CashesDetails"] = Relationship(back_populates="service")

    # Static Style
    icon_code: Optional[str] = Field(max_length=20)

class MedicalSchedules(SQLModel, table=True):
    __tablename__ = "medical_schedules"
    id: UUID = Field(
        sa_type=UUID_TYPE,
        sa_column_kwargs={"name":"medical_schedule_id"},
        default_factory=uuid.uuid4,
        primary_key=True
    )
    day: DayOfWeek = Field(
        sa_type=SQLEnum(DayOfWeek),
        nullable=False,
        sa_column_kwargs={"name":"day"}
    )
    start_time: time_type = Field(nullable=False)
    end_time: time_type = Field(nullable=False)
    available: bool = Field(default=True)


    doctors: List["Doctors"] = Relationship(
        back_populates="medical_schedules",
        link_model=DoctorMedicalScheduleLink
    )

class User(BaseUser, table=True):
    __tablename__ = "users"
    id: Optional[UUID] = Field(
        sa_type=UUID_TYPE,
        sa_column_kwargs={"name":"user_id"},
        default_factory=uuid.uuid4,
        primary_key=True,
        unique=True
    )
    turns: list["Turns"] = Relationship(back_populates="user")
    appointments: list["Appointments"] = Relationship(back_populates="user")

    health_insurance: List["HealthInsurance"] = Relationship(
        back_populates="users",
        link_model=UserHealthInsuranceLink
    )
    

    def set_google_liked_acount_password(self, password:str) -> str:
        self.password = pwd_context.hash(password)

class Doctors(BaseUser, table=True):
    __tablename__ = "doctors"
    id: UUID = Field(
        sa_type=UUID_TYPE,
        sa_column_kwargs={"name":"doctor_id"},
        default_factory=uuid.uuid4,
        primary_key=True,
        unique=True
    )

    is_available: bool = Field(default=True)

    # Asumiendo que la relación con Specialties sigue siendo uno a muchos o muchos a uno:
    speciality: Optional["Specialties"] = Relationship(back_populates="doctors")
    speciality_id: UUID = Field(foreign_key="specialties.specialty_id", ondelete="CASCADE")

    # Relación muchos a muchos con MedicalSchedules
    medical_schedules: List["MedicalSchedules"] = Relationship(
        back_populates="doctors",
        link_model=DoctorMedicalScheduleLink
    )
    turns: List["Turns"] = Relationship(back_populates="doctor")
    appointments: List["Appointments"] = Relationship(back_populates="doctor")

    doctor_state: DoctorStates = Field(
        sa_type=SQLEnum(DoctorStates),
        default=DoctorStates.available,
        nullable=False,
        max_length=10,
        sa_column_kwargs={"name":"state"}
    )


class Chat(SQLModel, table=True):
    id: UUID = Field(
        sa_type=UUID_TYPE,
        sa_column_kwargs={"name":"chat_id"},
        default_factory=uuid.uuid4,
        primary_key=True
    )
    messages: List["ChatMessages"] = Relationship(
        back_populates="chat",
    )
    doc_1_id: UUID
    doc_2_id: UUID


class ChatMessages(SQLModel, table=True):
    id: UUID = Field(
        sa_type=UUID_TYPE,
        sa_column_kwargs={"name":"message_id", "comment": "The primary key of the chat_messages table"},
        default_factory=uuid.uuid4,
        primary_key=True,
        unique=True
    )
    sender_id: UUID
    chat_id: UUID = Field(foreign_key="chat.chat_id")
    chat: Optional[Chat] = Relationship(back_populates="messages")
    content: str = Field()
    created_at: datetime = Field(nullable=False, default=datetime.now())
    deleted_at: datetime = Field(nullable=False, default=datetime.fromtimestamp((datetime.now() + timedelta(days=1)).timestamp()))

#TODO: completar este tabla con datos importantes
class HealthInsurance(SQLModel, table=True):
    __tablename__ = "health_insurance"
    id: UUID = Field(
        sa_type=UUID_TYPE,
        sa_column_kwargs={"name":"health_insurance_id"},
        default_factory=uuid.uuid4,
        primary_key=True,
        unique=True
    )
    name: str = Field(max_length=50)
    description: str = Field(max_length=500)
    discount: float = Field(default=0, nullable=False, ge=0, le=100)

    users: List["User"] = Relationship(
        back_populates="health_insurance",
        link_model=UserHealthInsuranceLink
    )


User.model_rebuild()
Doctors.model_rebuild()
Services.model_rebuild()
Locations.model_rebuild()
Departments.model_rebuild()
Specialties.model_rebuild()
MedicalSchedules.model_rebuild()
Turns.model_rebuild()
Appointments.model_rebuild()
Cashes.model_rebuild()
CashesDetails.model_rebuild()
Chat.model_rebuild()
ChatMessages.model_rebuild()
HealthInsurance.model_rebuild()
DoctorMedicalScheduleLink.model_rebuild()