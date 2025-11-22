import importlib
import importlib.util
import types
import uuid
from datetime import date as date_type, time as time_type
from pathlib import Path
from typing import Any

import orjson
import pytest
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import ORJSONResponse
from sqlmodel import Session, SQLModel, create_engine

from app.models import Departments, Doctors, Locations, MedicalSchedules, Specialties, Turns
from app.schemas.medica_area.enums import DayOfWeek


def load_schedules_module():
    module_name = "app.api.medic_area.schedules_under_test"
    if module_name in importlib.sys.modules:
        return importlib.sys.modules[module_name]

    api_module = types.ModuleType("app.api")
    api_module.__path__ = [str(Path("app/api").resolve())]
    importlib.sys.modules.setdefault("app.api", api_module)

    medic_module = types.ModuleType("app.api.medic_area")
    medic_module.__path__ = [str(Path("app/api/medic_area").resolve())]
    importlib.sys.modules.setdefault("app.api.medic_area", medic_module)

    db_module = types.ModuleType("app.db")
    db_module.__path__ = [str(Path("app/db").resolve())]
    importlib.sys.modules.setdefault("app.db", db_module)

    db_main_stub = types.ModuleType("app.db.main")
    db_main_stub.SessionDep = Any
    importlib.sys.modules.setdefault("app.db.main", db_main_stub)

    common_stub = types.ModuleType("app.api.medic_area.common")
    common_stub.auth_dependency = lambda: Depends(lambda: None)
    common_stub.console = types.SimpleNamespace(print_exception=lambda *_, **__: None)
    common_stub.default_response_class = ORJSONResponse
    importlib.sys.modules.setdefault("app.api.medic_area.common", common_stub)

    spec = importlib.util.spec_from_file_location(
        module_name,
        Path(__file__).resolve().parent.parent
        / "app"
        / "api"
        / "medic_area"
        / "schedules.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    importlib.sys.modules[module_name] = module
    return module


@pytest.fixture()
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    import app.models  # noqa: F401
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def build_request() -> Request:
    return Request({"type": "http", "app": FastAPI(), "headers": []})


def setup_available_speciality(session: Session, target_date: date_type) -> Specialties:
    location = Locations(name="Location", description="Desc")
    session.add(location)
    session.commit()

    department = Departments(name="Department", description="Desc", location_id=location.id)
    session.add(department)
    session.commit()

    speciality = Specialties(
        name="Cardiology", description="Heart", department_id=department.id
    )
    session.add(speciality)
    session.commit()

    doctor = Doctors(
        name="Doc", email="doc@example.com", password="password", dni="12345678", speciality_id=speciality.id
    )
    session.add(doctor)
    speciality.doctors.append(doctor)

    monday_schedule_available = MedicalSchedules(
        day=DayOfWeek.monday,
        start_time=time_type(9, 0),
        end_time=time_type(10, 0),
        max_patients=2,
    )
    monday_schedule_overbooked = MedicalSchedules(
        day=DayOfWeek.monday,
        start_time=time_type(10, 0),
        end_time=time_type(11, 0),
        max_patients=1,
    )
    tuesday_schedule = MedicalSchedules(
        day=DayOfWeek.tuesday,
        start_time=time_type(9, 0),
        end_time=time_type(10, 0),
    )

    doctor.medical_schedules.extend(
        [monday_schedule_available, monday_schedule_overbooked, tuesday_schedule]
    )

    filled_turn = Turns(
        date=target_date, date_limit=target_date, doctor=doctor, time=time_type(9, 30)
    )
    monday_schedule_available.turns.append(filled_turn)

    overbooked_turn = Turns(
        date=target_date, date_limit=target_date, doctor=doctor, time=time_type(10, 0)
    )
    monday_schedule_overbooked.turns.append(overbooked_turn)

    session.add_all(
        [
            monday_schedule_available,
            monday_schedule_overbooked,
            tuesday_schedule,
            filled_turn,
            overbooked_turn,
        ]
    )
    session.commit()
    session.refresh(speciality)
    return speciality


@pytest.mark.asyncio
async def test_days_by_availability_returns_404_when_specialty_missing(session: Session):
    schedules = load_schedules_module()
    request = build_request()

    with pytest.raises(HTTPException) as exc:
        await schedules.days_by_availability(request, uuid.uuid4(), session)

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Specialty not found"


@pytest.mark.asyncio
async def test_days_by_availability_returns_all_when_date_missing(session: Session):
    schedules = load_schedules_module()
    request = build_request()
    target_date = date_type(2024, 5, 6)
    speciality = setup_available_speciality(session, target_date)

    response = await schedules.days_by_availability(request, speciality.id, session)

    assert response.status_code == status.HTTP_200_OK
    payload = orjson.loads(response.body)
    available_days = {
        (entry["day"], entry["start_time"], entry["end_time"]) for entry in payload["available_days"]
    }

    assert available_days == {
        ("monday", "09:00:00", "11:00:00"),
        ("tuesday", "09:00:00", "10:00:00"),
    }


@pytest.mark.asyncio
async def test_days_by_availability_filters_by_date_and_capacity(session: Session):
    schedules = load_schedules_module()
    request = build_request()
    target_date = date_type(2024, 5, 6)
    speciality = setup_available_speciality(session, target_date)

    response = await schedules.days_by_availability(
        request, speciality.id, session, date=target_date
    )

    assert response.status_code == status.HTTP_200_OK
    payload = orjson.loads(response.body)

    assert payload["available_days"] == [
        {
            "day": "monday",
            "start_time": "09:00:00",
            "end_time": "10:00:00",
        }
    ]
