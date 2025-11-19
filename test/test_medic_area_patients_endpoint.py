import importlib.util
import json
import sys
import types
import uuid
from pathlib import Path

import orjson
import pytest
from fastapi import FastAPI
from fastapi import HTTPException, status
from fastapi import Request
from sqlmodel import Session, SQLModel, create_engine


class _DummyItem:
    def __init__(self, name: str | None = None, content: dict | None = None):
        self.item_name = name or ""
        self.content = content or {}
        self.expired_at = None
        self.created_at = None
        self.updated_at = None
        self.uuid_id = str(uuid.uuid4())

    def to_json(self) -> str:
        return json.dumps({"name": self.item_name, "content": self.content})


class _DummySet:
    def __init__(self, name: str | None = None):
        self.name = name or ""

    def items(self):
        return []

    def to_json(self) -> str:
        return json.dumps({"name": self.name, "content": []})


sys.modules.setdefault(
    "encript_storage",
    types.SimpleNamespace(
        Set=_DummySet,
        Item=_DummyItem,
        py_read_set=lambda name: _DummySet(name),
        py_create_set=lambda name: _DummySet(name),
        py_save_data=lambda *_, **__: None,
        py_find_item_in_set=lambda *_, **__: _DummyItem(),
        py_create_item=lambda *_, **__: _DummyItem(),
        py_add_item=lambda *_, **__: None,
        py_update_item_content_by_name=lambda *_, **__: None,
    ),
)
sys.modules.setdefault(
    "polars",
    types.SimpleNamespace(DataFrame=object, Series=object, col=lambda *_, **__: None),
)
sys.modules.setdefault(
    "stripe", types.SimpleNamespace()
)
spec = importlib.util.spec_from_file_location(
    "app.api.medic_area",
    Path(__file__).resolve().parent.parent / "app" / "api" / "medic_area.py",
)
medic_area = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(medic_area)

get_patients_by_doctor = medic_area.get_patients_by_doctor

from app.models import Appointments, Departments, Doctors, Locations, Specialties, User


@pytest.fixture()
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def build_specialty(session: Session) -> Specialties:
    location = Locations(name="loc", description="location")
    department = Departments(name="dep", description="department", location=location)
    specialty = Specialties(name="spec", description="specialty", departament=department)
    session.add_all([location, department, specialty])
    session.commit()
    session.refresh(specialty)
    return specialty


def build_request(user: User | Doctors) -> Request:
    request = Request({"type": "http", "app": FastAPI(), "headers": []})
    request.state.user = user
    return request


def build_doctor(*, session: Session, specialty: Specialties, email: str) -> Doctors:
    doctor = Doctors(
        name=email,
        email=email,
        password="Password123!",
        speciality_id=specialty.id,
        dni="12345678",
    )
    session.add(doctor)
    session.commit()
    session.refresh(doctor)
    return doctor


def build_user(*, session: Session, email: str, is_admin: bool = False, is_superuser: bool = False) -> User:
    user = User(
        name=email,
        email=email,
        password="Password123!",
        dni="12345678",
        is_admin=is_admin,
        is_superuser=is_superuser,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_get_patients_returns_404_when_doctor_missing(session: Session):
    admin_user = build_user(session=session, email="admin@example.com", is_admin=True)
    request = build_request(admin_user)

    with pytest.raises(HTTPException) as exc:
        await get_patients_by_doctor(request, uuid.uuid4(), session, current_user=admin_user)

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_patients_rejects_doctor_without_access(session: Session):
    specialty = build_specialty(session)
    primary_doctor = build_doctor(session=session, specialty=specialty, email="doc@example.com")
    outsider_doctor = build_doctor(session=session, specialty=specialty, email="outsider@example.com")
    request = build_request(outsider_doctor)

    with pytest.raises(HTTPException) as exc:
        await get_patients_by_doctor(request, primary_doctor.id, session, current_user=outsider_doctor)

    assert exc.value.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_patients_filters_duplicates_and_null_users(session: Session):
    specialty = build_specialty(session)
    doctor = build_doctor(session=session, specialty=specialty, email="doc@example.com")
    admin_user = build_user(session=session, email="admin@example.com", is_admin=True)
    patient = build_user(session=session, email="patient@example.com")

    session.add_all(
        [
            Appointments(user=patient, doctor=doctor),
            Appointments(user=patient, doctor=doctor),
            Appointments(doctor=doctor),
        ]
    )
    session.commit()

    request = build_request(admin_user)
    response = await get_patients_by_doctor(request, doctor.id, session, current_user=admin_user)
    payload = orjson.loads(response.body)

    assert response.status_code == status.HTTP_200_OK
    assert len(payload) == 1
    assert payload[0]["id"] == str(patient.id)
