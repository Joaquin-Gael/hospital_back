from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Integer, VARCHAR
from sqlalchemy import Enum as SQLEnum

from typing import Optional, List

import uuid
from uuid import UUID

from datetime import time

from enum import Enum

class Locations(SQLModel, table=True):
    id: str = Field(
        sa_column=Column(
            name="location_id",
            type_=String(36),
            primary_key=True,
            unique=True
        ),
        default_factory=lambda: str(uuid.uuid4()),
    )
    name: str = Field(max_length=50)
    description: str = Field(max_length=500)
    departments: List["Departments"] = Relationship(back_populates="location")


class Departments(SQLModel, table=True):
    id: str = Field(
        sa_column=Column(
            name="department_id",
            type_=String(36),
            primary_key=True,
            unique=True
        ),
        default_factory=lambda: str(uuid.uuid4()),
    )
    name: str = Field(max_length=50)
    description: str = Field(max_length=500)
    location: Optional["Locations"] = Relationship(back_populates="departments")
    location_id: str = Field(foreign_key="locations.location_id", ondelete="CASCADE")
    specialities: List["Specialties"] = Relationship(back_populates="departament")


class Specialties(SQLModel, table=True):
    id: str = Field(
        sa_column=Column(
            name="specialty_id",
            type_=String(36),
            primary_key=True,
            unique=True
        ),
        default_factory=lambda: str(uuid.uuid4()),
    )
    name: str = Field(max_length=50)
    description: str = Field(max_length=500)
    departament: Optional["Departments"] = Relationship(back_populates="specialities")
    department_id: str = Field(foreign_key="departments.department_id", ondelete="CASCADE")
    services: List["Services"] = Relationship(back_populates="speciality")
    doctors: List["Doctors"] = Relationship(back_populates="speciality")

class Services(SQLModel, table=True):
    id: str = Field(
        sa_column=Column(
            name="service_id",
            type_=String(36),
            primary_key=True,
            unique=True
        ),
        default_factory=lambda: str(uuid.uuid4()),
    )
    name: str = Field(max_length=50)
    description: str = Field(max_length=500)
    price: float = Field(default=0, nullable=False)
    speciality: Optional["Specialties"] = Relationship(back_populates="services")
    specialty_id: str = Field(foreign_key="specialties.specialty_id", ondelete="CASCADE")

class Doctors(SQLModel, table=True):
    id: str = Field(
        sa_column=Column(
            name="doctor_id",
            type_=String(36),
            primary_key=True,
            unique=True
        ),
        default_factory=lambda: str(uuid.uuid4()),
    )
    name: str = Field(max_length=50)
    lastname: str = Field(max_length=50)
    dni: int = Field(max_length=8)
    telephone: str = Field(max_length=50)
    email: str = Field(max_length=50)
    specialty: Optional["Specialties"] = Relationship(back_populates="services")
    specialty_id: str = Field(foreign_key="specialties.specialty_id", ondelete="CASCADE")
    medical_schedule: Optional["MedicalSchedules"] = Relationship(back_populates="doctors")
    medical_schedule_id : str = Field(foreign_key="medicalschedules.medical_schedule_id", ondelete="CASCADE")


class DayOfWeek(str, Enum):
    monday = "Monday"
    tuesday = "Tuesday"
    wednesday = "Wednesday"
    thursday = "Thursday"
    friday = "Friday"
    saturday = "Saturday"
    sunday = "Sunday"

class MedicalSchedules(SQLModel, table=True):
    id: str = Field(
        sa_column=Column(
            name="medical_schedule_id",
            type_=String(36),
            primary_key=True,
            unique=True
        ),
        default_factory=lambda: str(uuid.uuid4()),
    )
    day: DayOfWeek = Field(
        sa_column=Column(
            "day",
            SQLEnum(DayOfWeek),
            nullable=False,
        )
    )
    time_medic: time = Field(nullable=False)
    doctors: List["Doctors"] = Relationship(back_populates="medical_schedule")