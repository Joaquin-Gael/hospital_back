import asyncio
import os
import sys
import types
from datetime import date, time

import pytest
from sqlmodel import SQLModel, Session, create_engine, select
from rich.console import Console

os.environ.setdefault("DB_URL", "sqlite:///./test.db")

if "app.api.ai_assistant" not in sys.modules:
    fake_ai_module = types.ModuleType("app.api.ai_assistant")
    fake_ai_module.router = None
    sys.modules["app.api.ai_assistant"] = fake_ai_module

for _module in ("app.api.audit", "app.api.auth", "app.api.cashes", "app.api.users"):
    if _module not in sys.modules:
        sys.modules[_module] = types.ModuleType(_module)

for _missing in ("torch", "polars"):
    if _missing not in sys.modules:
        module = types.ModuleType(_missing)
        if _missing == "polars":
            module.DataFrame = type("DataFrame", (), {})
            module.Series = type("Series", (), {})
            module.col = lambda *_, **__: None
        sys.modules[_missing] = module

if "app.core.interfaces.oauth" not in sys.modules:
    fake_oauth = types.ModuleType("app.core.interfaces.oauth")
    fake_oauth.console = Console()
    sys.modules["app.core.interfaces.oauth"] = fake_oauth

from app.core.interfaces.medic_area import TurnAndAppointmentRepository  # noqa: E402
from app.models import (  # noqa: E402
    DayOfWeek,
    Departments,
    Doctors,
    Locations,
    MedicalSchedules,
    RenameTurnsStateMixin,
    Specialties,
    Services,
    Turns,
    User,
)
from app.schemas.medica_area.enums import TurnsState  # noqa: E402
from app.schemas.medica_area.turns import TurnsCreate  # noqa: E402

RenameTurnsStateMixin.__declare_last__ = classmethod(lambda cls: None)


@pytest.fixture
def engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'create_turns.db'}", echo=False)
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session


def _setup_entities(session: Session, *, max_patients: int = 1) -> dict:
    location = Locations(name="Main campus", description="Primary location")
    session.add(location)
    session.commit()
    session.refresh(location)

    department = Departments(
        name="Cardiology",
        description="Heart treatments",
        location_id=location.id,
    )
    session.add(department)
    session.commit()
    session.refresh(department)

    specialty = department.specialities[0] if department.specialities else None
    if specialty is None:
        specialty = Specialties(
            name="Adult Cardiology",
            description="General cardiology",
            department_id=department.id,
        )
        session.add(specialty)
        session.commit()
        session.refresh(specialty)

    doctor = Doctors(
        name="Dr. Strange",
        email="doctor@example.com",
        password="Password123!",
        dni="12345678",
        speciality_id=specialty.id,
    )
    session.add(doctor)
    session.commit()
    session.refresh(doctor)

    service = Services(
        name="Consultation",
        description="General checkup",
        price=100,
        specialty_id=specialty.id,
    )
    session.add(service)
    session.commit()
    session.refresh(service)

    schedule = MedicalSchedules(
        day=DayOfWeek.monday,
        start_time=time(9, 0),
        end_time=time(12, 0),
        max_patients=max_patients,
        available=True,
    )
    session.add(schedule)
    session.commit()
    session.refresh(schedule)

    schedule.doctors.append(doctor)
    session.add(schedule)
    session.commit()
    session.refresh(schedule)

    user = User(
        name="Tony Stark",
        email="patient@example.com",
        password="Password123!",
        dni="87654321",
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    return {
        "user": user,
        "doctor": doctor,
        "service": service,
        "schedule": schedule,
    }


def _make_turn_payload(data: dict, *, visit_time: time) -> TurnsCreate:
    return TurnsCreate(
        reason="Checkup",
        state=TurnsState.waiting,
        date=date(2024, 1, 1),
        user_id=data["user"].id,
        doctor_id=data["doctor"].id,
        services=[data["service"].id],
        time=visit_time,
    )


def test_create_turn_and_appointment_success(session):
    data = _setup_entities(session, max_patients=1)
    payload = _make_turn_payload(data, visit_time=time(9, 30))

    new_turn, new_appointment = asyncio.run(
        TurnAndAppointmentRepository.create_turn_and_appointment(
            session=session,
            turn=payload,
            doctor=data["doctor"],
        )
    )

    session.refresh(data["schedule"])

    assert new_turn is not None
    assert new_appointment is not None
    assert new_turn in data["schedule"].turns
    assert data["schedule"].available is False


def test_create_turn_and_appointment_out_of_range_time(session):
    data = _setup_entities(session, max_patients=1)
    payload = _make_turn_payload(data, visit_time=time(8, 0))

    new_turn, message = asyncio.run(
        TurnAndAppointmentRepository.create_turn_and_appointment(
            session=session,
            turn=payload,
            doctor=data["doctor"],
        )
    )

    assert new_turn is None
    assert message == "No matching schedule found for the selected date"
    assert session.exec(select(Turns)).all() == []


def test_create_turn_and_appointment_over_capacity(session):
    data = _setup_entities(session, max_patients=1)

    existing_turn = Turns(
        reason="Existing",
        state=TurnsState.waiting,
        date=date(2024, 1, 1),
        date_limit=date(2024, 1, 2),
        user_id=data["user"].id,
        doctor_id=data["doctor"].id,
        time=time(9, 0),
    )
    session.add(existing_turn)
    session.commit()
    session.refresh(existing_turn)

    data["schedule"].turns.append(existing_turn)
    session.add(data["schedule"])
    session.commit()
    session.refresh(data["schedule"])

    payload = _make_turn_payload(data, visit_time=time(10, 0))

    new_turn, message = asyncio.run(
        TurnAndAppointmentRepository.create_turn_and_appointment(
            session=session,
            turn=payload,
            doctor=data["doctor"],
        )
    )

    assert new_turn is None
    assert message == "No available slots in the schedule"
    all_turns = session.exec(select(Turns)).all()
    assert len(all_turns) == 1
    assert all_turns[0].id == existing_turn.id
