import asyncio
import os
import sys
import types
from datetime import date, time, timedelta

import pytest
from fastapi import HTTPException, status
from sqlmodel import SQLModel, Session, create_engine
from starlette.requests import Request

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

from app.api.medic_area.turns import reschedule_turn as reschedule_turn_route  # noqa: E402
from app.core.interfaces.medic_area import TurnAndAppointmentRepository  # noqa: E402
from app.models import (  # noqa: E402
    DayOfWeek,
    Departments,
    Doctors,
    Locations,
    MedicalSchedules,
    Turns,
    TurnsState,
    User,
)
from app.schemas.medica_area.turns import TurnReschedule  # noqa: E402


@pytest.fixture
def engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'turns.db'}", echo=False)
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session


def _create_base_entities(session: Session):
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
        from app.models import Specialties  # local import to avoid circular issues

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

    user = User(
        name="Tony Stark",
        email="patient@example.com",
        password="Password123!",
        dni="87654321",
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    schedule_monday = MedicalSchedules(
        day=DayOfWeek.monday,
        start_time=time(9, 0),
        end_time=time(17, 0),
        max_patients=2,
        available=True,
    )
    schedule_tuesday = MedicalSchedules(
        day=DayOfWeek.tuesday,
        start_time=time(9, 0),
        end_time=time(17, 0),
        max_patients=1,
        available=True,
    )
    session.add(schedule_monday)
    session.add(schedule_tuesday)
    session.commit()
    session.refresh(schedule_monday)
    session.refresh(schedule_tuesday)

    schedule_monday.doctors.append(doctor)
    schedule_tuesday.doctors.append(doctor)
    session.add(schedule_monday)
    session.add(schedule_tuesday)
    session.commit()
    session.refresh(schedule_monday)
    session.refresh(schedule_tuesday)

    turn = Turns(
        reason="Initial appointment",
        state=TurnsState.waiting,
        date=date(2024, 1, 1),
        date_limit=date(2024, 1, 2),
        user_id=user.id,
        doctor_id=doctor.id,
        time=time(9, 0),
    )
    session.add(turn)
    session.commit()
    session.refresh(turn)

    schedule_monday.turns.append(turn)
    session.add(schedule_monday)
    session.commit()
    session.refresh(schedule_monday)
    session.refresh(turn)

    return {
        "turn": turn,
        "user": user,
        "doctor": doctor,
        "monday_schedule": schedule_monday,
        "tuesday_schedule": schedule_tuesday,
        "new_date": date(2024, 1, 2),
    }


def test_reschedule_turn_success(session):
    data = _create_base_entities(session)
    turn = data["turn"]
    new_time = time(10, 0)

    updated_turn = asyncio.run(
        TurnAndAppointmentRepository.reschedule_turn(
            session=session,
            turn=turn,
            date=data["new_date"],
            time=new_time,
        )
    )

    session.refresh(updated_turn)
    session.refresh(data["monday_schedule"])
    session.refresh(data["tuesday_schedule"])

    assert updated_turn.date == data["new_date"]
    assert updated_turn.time == new_time
    assert updated_turn.date_limit == data["new_date"] + timedelta(days=1)
    assert updated_turn not in data["monday_schedule"].turns
    assert updated_turn in data["tuesday_schedule"].turns
    assert data["monday_schedule"].available is True
    assert data["tuesday_schedule"].available is False


def test_reschedule_turn_without_availability(session):
    data = _create_base_entities(session)
    tuesday_schedule = data["tuesday_schedule"]
    turn = data["turn"]

    other_turn = Turns(
        reason="Another appointment",
        state=TurnsState.waiting,
        date=data["new_date"],
        date_limit=data["new_date"] + timedelta(days=1),
        user_id=data["user"].id,
        doctor_id=data["doctor"].id,
        time=time(10, 0),
    )
    session.add(other_turn)
    session.commit()
    session.refresh(other_turn)

    tuesday_schedule.turns.append(other_turn)
    session.add(tuesday_schedule)
    session.commit()
    session.refresh(tuesday_schedule)

    with pytest.raises(ValueError, match="No available slots"):
        asyncio.run(
            TurnAndAppointmentRepository.reschedule_turn(
                session=session,
                turn=turn,
                date=data["new_date"],
                time=time(11, 0),
            )
        )

    session.refresh(data["monday_schedule"])
    assert turn in data["monday_schedule"].turns


def test_reschedule_turn_requires_authorized_user(session, monkeypatch):
    data = _create_base_entities(session)
    turn = data["turn"]

    other_user = User(
        name="Pepper Potts",
        email="pepper@example.com",
        password="Password123!",
        dni="11223344",
    )
    session.add(other_user)
    session.commit()
    session.refresh(other_user)

    async def fail_reschedule(*args, **kwargs):
        fail_reschedule.called = True
        raise AssertionError("Repository should not be invoked")

    fail_reschedule.called = False
    monkeypatch.setattr(TurnAndAppointmentRepository, "reschedule_turn", fail_reschedule)

    async def dummy_receive():
        return {"type": "http.request"}

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "PATCH",
        "scheme": "http",
        "path": f"/turns/{turn.id}/reschedule",
        "raw_path": f"/turns/{turn.id}/reschedule".encode(),
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "state": {},
    }
    request = Request(scope, dummy_receive)
    request.state.user = other_user
    request.state.scopes = []

    payload = TurnReschedule(date=data["new_date"], time=time(11, 0))

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(reschedule_turn_route(request, session, turn.id, payload))

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert fail_reschedule.called is False
