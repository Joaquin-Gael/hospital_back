from pathlib import Path

from fastapi import UploadFile
from sqlmodel import SQLModel, Field, Relationship, Session

from sqlalchemy import Column, UUID as UUID_TYPE, VARCHAR, event
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import declarative_mixin

from typing import Optional, List, Dict, Any

from dataclasses import dataclass, field

from passlib.context import CryptContext

import uuid
from uuid import UUID, uuid4

from datetime import time, datetime, timedelta
from datetime import date as date_type, time as time_type

from enum import Enum

import re

import random

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


@dataclass
class AuditRecord:
    """Structured audit information for domain events.

    The record is intentionally lightweight so it can be persisted or logged by the
    caller depending on the use case.
    """

    action: str
    target_type: str
    target_id: Optional[UUID]
    actor_id: Optional[UUID]
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)

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
    updated_at: datetime = Field(default=datetime.now(), nullable=True)
    dni: str = Field(max_length=8)
    telephone: Optional[str] = Field(max_length=50)
    address: Optional[str] = Field(nullable=True)
    blood_type: Optional[str] = Field(nullable=True)
    url_image_profile: Optional[str] = Field(nullable=True)
    
    @event.listens_for(Session, "before_flush")
    def _update_timestamp(session, flush_context, instances):
        for obj in session.dirty:
            if isinstance(obj, BaseUser):
                obj.updated_at = datetime.now()

    def set_url_image_profile(self, file_name: str):
        self.url_image_profile = f"{os.getenv("DOMINIO")}/media/{self.__class__.__name__.lower()}/{file_name}"

    async def save_profile_image(self, file: UploadFile | None, media_root: str = "media"):
        if file is None:
            return
        
        cls_name = self.__class__.__name__.lower()
        
        try:
            if self.url_image_profile:
                media_index = self.url_image_profile.find("/media")
                file_path = Path("app").joinpath(self.url_image_profile[media_index+1:]).resolve()
                os.remove(file_path)
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

    def _make_audit_record(
        self,
        action: str,
        actor_id: Optional[UUID] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditRecord:
        return AuditRecord(
            action=action,
            target_type=self.__class__.__name__,
            target_id=getattr(self, "id", None),
            actor_id=actor_id,
            timestamp=datetime.now(),
            details=details or {},
        )

    def mark_login(
        self,
        timestamp: Optional[datetime] = None,
        *,
        actor_id: Optional[UUID] = None,
    ) -> AuditRecord:
        if not self.is_active:
            raise ValueError("Inactive accounts cannot start a new session.")

        timestamp = timestamp or datetime.now()
        self.last_login = timestamp
        return self._make_audit_record(
            action="mark_login",
            actor_id=actor_id,
            details={"timestamp": timestamp.isoformat()},
        )

    def activate(
        self,
        *,
        actor_id: Optional[UUID] = None,
        reason: Optional[str] = None,
    ) -> AuditRecord:
        if self.is_active:
            raise ValueError("Account is already active.")

        self.is_active = True
        details = {"reason": reason} if reason else {}
        return self._make_audit_record("activate", actor_id, details)

    def deactivate(
        self,
        *,
        actor_id: Optional[UUID] = None,
        reason: Optional[str] = None,
    ) -> AuditRecord:
        if not self.is_active:
            raise ValueError("Account is already inactive.")

        self.is_active = False
        details = {"reason": reason} if reason else {}
        return self._make_audit_record("deactivate", actor_id, details)

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

    def ban(
        self,
        *,
        actor_id: Optional[UUID] = None,
        reason: Optional[str] = None,
    ) -> AuditRecord:
        return self.deactivate(actor_id=actor_id, reason=reason)

    def des_ban(
        self,
        *,
        actor_id: Optional[UUID] = None,
        reason: Optional[str] = None,
    ) -> AuditRecord:
        return self.activate(actor_id=actor_id, reason=reason)

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
    time: time_type = Field(
        nullable=False,
        default=datetime.now().time()
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

class TurnsSchedulesLink(SQLModel, table=True):
    __tablename__ = "turns_schedules_link"

    turn_id: UUID = Field(
        foreign_key='turns.turn_id',
        primary_key=True,
        ondelete='CASCADE'
    )

    medical_schedule_id: UUID = Field(
        foreign_key="medical_schedules.medical_schedule_id",
        primary_key=True,
        ondelete="CASCADE"
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

    schedules: List["MedicalSchedules"] = Relationship(
        back_populates="turns",
        link_model=TurnsSchedulesLink
    )

    appointment: Optional["Appointments"] = Relationship(back_populates="turn")
    documents: List["TurnDocument"] = Relationship(back_populates="turn")
    document_downloads: List["TurnDocumentDownload"] = Relationship(back_populates="turn")

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
                    "price": service.price,
                    "id": str(service.id)
                }
            )

        return details


    def price_total(self) -> float:
        total:float = 0.0
        for service in self.services:
            total += service.price

        return total

class TurnDocument(SQLModel, table=True):
    __tablename__ = "turn_documents"

    id: UUID = Field(
        sa_type=UUID_TYPE,
        sa_column_kwargs={"name": "turn_document_id"},
        default_factory=uuid4,
        primary_key=True,
        unique=True,
    )
    turn_id: UUID = Field(
        sa_type=UUID_TYPE,
        foreign_key="turns.turn_id",
        nullable=False,
        index=True,
        ondelete="CASCADE",
    )
    user_id: UUID = Field(
        sa_type=UUID_TYPE,
        foreign_key="users.user_id",
        nullable=False,
        index=True,
        ondelete="CASCADE",
    )
    file_path: str = Field(sa_type=VARCHAR(length=512))
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    turn: "Turns" = Relationship(back_populates="documents")
    user: "User" = Relationship(back_populates="documents")
    downloads: List["TurnDocumentDownload"] = Relationship(back_populates="document")


class TurnDocumentDownload(SQLModel, table=True):
    __tablename__ = "turn_document_downloads"

    id: UUID = Field(
        sa_type=UUID_TYPE,
        sa_column_kwargs={"name": "turn_document_download_id"},
        default_factory=uuid4,
        primary_key=True,
        unique=True,
    )
    turn_document_id: UUID = Field(
        sa_type=UUID_TYPE,
        foreign_key="turn_documents.turn_document_id",
        nullable=False,
        index=True,
        ondelete="CASCADE",
    )
    turn_id: UUID = Field(
        sa_type=UUID_TYPE,
        foreign_key="turns.turn_id",
        nullable=False,
        index=True,
        ondelete="CASCADE",
    )
    user_id: UUID = Field(
        sa_type=UUID_TYPE,
        foreign_key="users.user_id",
        nullable=False,
        index=True,
        ondelete="CASCADE",
    )
    downloaded_at: datetime = Field(default_factory=datetime.utcnow)

    document: TurnDocument = Relationship(back_populates="downloads")
    turn: Turns = Relationship(back_populates="document_downloads")
    user: "User" = Relationship(back_populates="turn_document_downloads")

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

    cash_details: List["CashDetails"] = Relationship(
        back_populates="appointment"
    )

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
    income: float = Field(default=0, nullable=False, ge=0)
    expense: float = Field(default=0, nullable=False, ge=0)
    date: date_type = Field(nullable=False)
    time_transaction: time_type = Field(nullable=False, default=datetime.now().time())
    balance: float = Field(default=0, nullable=False)

    details: List["CashDetails"] = Relationship(
        back_populates="cash",
        cascade_delete=True,
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    def make_balance(self):
        self.balance = self.income - self.expense

class CashDetails(SQLModel, table=True):
    __tablename__ = "cash_details"

    id: UUID = Field(
        sa_type=UUID_TYPE,
        sa_column_kwargs={"name":"cash_details_id", "comment": "The primary key of the cash_details table"},
        default_factory=uuid4,
        primary_key=True,
        unique=True
    )
    description: str = Field(max_length=255, nullable=False)
    amount: float = Field(default=0, nullable=False)
    date: date_type = Field(nullable=False)
    time_transaction: time_type = Field(nullable=False, default=datetime.now().time())
    discount: int = Field(nullable=False, le=100, ge=0)

    appointment_id: UUID = Field(
        sa_type=UUID_TYPE,
        foreign_key="appointments.appointment_id",
        nullable=False
    )
    appointment: Appointments = Relationship(
        back_populates="cash_details"
    )

    total: float = Field(nullable=False, description="this flied is the total of te service, the expense for the benefit of this service")

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
    details: List["CashDetails"] = Relationship(back_populates="service")

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

    max_patients: int = Field(nullable=True, ge=1, le=10, default_factory=lambda :random.randint(1,10))

    turns: List["Turns"] = Relationship(
        back_populates="schedules",
        link_model=TurnsSchedulesLink
    )

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
    documents: List["TurnDocument"] = Relationship(back_populates="user")
    turn_document_downloads: List["TurnDocumentDownload"] = Relationship(back_populates="user")

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

    def update_state(
        self,
        new_state: DoctorStates,
        *,
        actor_id: Optional[UUID] = None,
        reason: Optional[str] = None,
    ) -> AuditRecord:
        if not isinstance(new_state, DoctorStates):
            raise ValueError("Invalid doctor state provided.")

        self.doctor_state = new_state
        self.is_available = new_state == DoctorStates.available
        return self._make_audit_record(
            action="update_state",
            actor_id=actor_id,
            details={
                "new_state": new_state.value,
                **({"reason": reason} if reason else {}),
            },
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
        cascade_delete=True
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
    
class PasswordResetToken(SQLModel, table=True):
    __tablename__ = "password_reset_tokens"
    id: UUID = Field(
        sa_type=UUID_TYPE,
        sa_column_kwargs={"name":"password_reset_token_id"},
        default_factory=uuid4, 
        primary_key=True,
        unique=True)
    user_id: Optional[UUID] = Field(
        sa_type=UUID_TYPE,
        foreign_key="users.user_id",
        nullable=True,
    )
    token_hash: str = Field(nullable=False, index=True)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    expires_at: datetime = Field(nullable=False)
    used: bool = Field(default=False, nullable=False)
    attempts: int = Field(default=0, nullable=False)
    request_ip: str = Field(nullable=True)

class SistemSession(SQLModel):
    uuid: UUID = Field(
        sa_type=UUID_TYPE,
        sa_column_kwargs={"name":"session_id"},
        default_factory=uuid.uuid4,
        primary_key=True,
        unique=True
    )
    value_hash: str = Field(nullable=False)
    

class AlertLevels(Enum):
    low = "low"
    medium = "medium"
    high = "high"

class AlertDDoS(SQLModel):
    __tablename__ = "alert_ddos"
    id: UUID = Field(
        sa_type=UUID_TYPE,
        sa_column_kwargs={"name":"alert_ddos_id"},
        default_factory=uuid.uuid4,
        primary_key=True,
        unique=True
    )

    path: str = Field(nullable=False)
    ip: str = Field(nullable=False)
    count: int = Field(default=0, nullable=False)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.now, nullable=False)
    alert_level: AlertLevels = Field(
        nullable=False,
        default=AlertLevels.low
    )

class AdminRegister(SQLModel):
    __tablename__ = "admin_register"
    id: UUID = Field(
        sa_type=UUID_TYPE,
        sa_column_kwargs={"name":"admin_register_id"},
        default_factory=uuid.uuid4,
        primary_key=True,
        unique=True
    )
    user_id: UUID = Field(foreign_key="users.user_id", ondelete="CASCADE")
    user: User = Relationship(back_populates="admin_register")

    table_changed_name: str = Field(nullable=False)
    action: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)

AdminRegister.model_rebuild()
AlertDDoS.model_rebuild()
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
CashDetails.model_rebuild()
Chat.model_rebuild()
ChatMessages.model_rebuild()
HealthInsurance.model_rebuild()
DoctorMedicalScheduleLink.model_rebuild()