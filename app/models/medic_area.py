from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, CheckConstraint, UUID as SQLUUID
from sqlalchemy import Enum as SQLEnum

from typing import Optional, List, Tuple

from passlib.context import CryptContext

import uuid
from uuid import UUID

from datetime import time, datetime, timedelta

from enum import Enum

from app.models.users import BaseUser
from app.db.main import metadata

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class DayOfWeek(str, Enum):
    monday = "Monday"
    tuesday = "Tuesday"
    wednesday = "Wednesday"
    thursday = "Thursday"
    friday = "Friday"
    saturday = "Saturday"
    sunday = "Sunday"

class Locations(SQLModel, table=True):
    id: UUID = Field(
        sa_column=Column(
            name="location_id",
            type_=SQLUUID,
            primary_key=True,
            unique=True
        ),
        default_factory=uuid.uuid4,
    )
    name: str = Field(max_length=50)
    description: str = Field(max_length=500)
    departments: List["Departments"] = Relationship(back_populates="location")


class Departments(SQLModel, table=True):
    id: UUID = Field(
        sa_column=Column(
            name="department_id",
            type_=SQLUUID,
            primary_key=True,
            unique=True
        ),
        default_factory=uuid.uuid4,
    )
    name: str = Field(max_length=50)
    description: str = Field(max_length=500)
    location: Optional["Locations"] = Relationship(back_populates="departments")
    location_id: UUID = Field(foreign_key="locations.location_id", ondelete="CASCADE")
    specialities: List["Specialties"] = Relationship(back_populates="departament")


class Specialties(SQLModel, table=True):
    id: UUID = Field(
        sa_column=Column(
            name="specialty_id",
            type_=SQLUUID,
            primary_key=True,
            unique=True
        ),
        default_factory=uuid.uuid4,
    )
    name: str = Field(max_length=50)
    description: str = Field(max_length=500)
    departament: Optional["Departments"] = Relationship(back_populates="specialities")
    department_id: UUID = Field(foreign_key="departments.department_id", ondelete="CASCADE")
    services: List["Services"] = Relationship(back_populates="speciality")
    doctors: List["Doctors"] = Relationship(back_populates="speciality")

class Services(SQLModel, table=True):
    id: UUID = Field(
        sa_column=Column(
            name="service_id",
            type_=SQLUUID,
            primary_key=True,
            unique=True
        ),
        default_factory=uuid.uuid4,
    )
    name: str = Field(max_length=50)
    description: str = Field(max_length=500)
    price: float = Field(default=0, nullable=False)
    speciality: Optional["Specialties"] = Relationship(back_populates="services")
    specialty_id: UUID = Field(foreign_key="specialties.specialty_id", ondelete="CASCADE")

class DoctorMedicalScheduleLink(SQLModel, table=True, metadata=metadata):
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

class MedicalSchedules(SQLModel, table=True, metadata=metadata):
    __tablename__ = "medical_schedules"
    id: UUID = Field(
        sa_column=Column(
            name="medical_schedule_id",
            type_=SQLUUID,
            primary_key=True
        ),
        default_factory=uuid.uuid4,
    )
    day: DayOfWeek = Field(
        sa_column=Column(
            name="day",
            type_=SQLEnum(DayOfWeek),
            nullable=False,
        )
    )
    start_time: time = Field(nullable=False)
    end_time: time = Field(nullable=False)


    doctors: List["Doctors"] = Relationship(
        back_populates="medical_schedules",
        link_model=DoctorMedicalScheduleLink
    )

class Doctors(BaseUser, table=True, metadata=metadata):
    __tablename__ = "doctors"
    id: UUID = Field(
        sa_column=Column(
            name="doctor_id",
            type_=SQLUUID,
            primary_key=True,
            unique=True
        ),
        default_factory=uuid.uuid4,
    )

    # Asumiendo que la relación con Specialties sigue siendo uno a muchos o muchos a uno:
    speciality: Optional["Specialties"] = Relationship(back_populates="doctors")
    speciality_id: UUID = Field(foreign_key="specialties.specialty_id", ondelete="CASCADE")

    # Relación muchos a muchos con MedicalSchedules
    medical_schedules: List["MedicalSchedules"] = Relationship(
        back_populates="doctors",
        link_model=DoctorMedicalScheduleLink
    )


class Chat(SQLModel, table=True):
    id: UUID = Field(
        sa_column=Column(
            name="chat_id",
            type_=SQLUUID,
            primary_key=True,
            unique=True
        ),
        default_factory=uuid.uuid4,
    )
    messages: List["ChatMessages"] = Relationship(
        back_populates="chat",
    )
    doc_1_id: UUID
    doc_2_id: UUID


class ChatMessages(SQLModel, table=True):
    id: UUID = Field(
        sa_column=Column(
            name="message_id",
            type_=SQLUUID,
            primary_key=True,
            unique=True
        ),
        default_factory=uuid.uuid4,
    )
    sender_id: UUID
    chat_id: UUID = Field(foreign_key="chat.chat_id")
    chat: Optional[Chat] = Relationship(back_populates="messages")
    content: str = Field()
    created_at: datetime = Field(nullable=False, default=datetime.now)
    deleted_at: datetime = Field(nullable=False, default=(datetime.now() + timedelta(days=1)).timestamp())