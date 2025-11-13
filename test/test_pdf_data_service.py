from datetime import date, time
from uuid import uuid4

from app.core.services.pdf_data import build_turn_pdf_data
from app.models import Appointments, Doctors, Services, Specialties, Turns, TurnsState, User


def _make_user(**kwargs) -> User:
    defaults = {
        "id": uuid4(),
        "name": "paciente1",
        "email": "paciente@example.com",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "password": "hashed",
        "dni": "12345678",
    }
    defaults.update(kwargs)
    return User(**defaults)


def _make_doctor(specialty: Specialties, **kwargs) -> Doctors:
    defaults = {
        "id": uuid4(),
        "name": "drhouse",
        "email": "house@example.com",
        "first_name": "Gregory",
        "last_name": "House",
        "password": "hashed",
        "dni": "87654321",
        "speciality_id": specialty.id,
    }
    defaults.update(kwargs)
    doctor = Doctors(**defaults)
    doctor.speciality = specialty
    return doctor


def _make_service(specialty: Specialties, **kwargs) -> Services:
    defaults = {
        "id": uuid4(),
        "name": "Consulta general",
        "description": "Consulta médica general",
        "price": 1500.0,
        "specialty_id": specialty.id,
    }
    defaults.update(kwargs)
    service = Services(**defaults)
    service.speciality = specialty
    return service


def test_build_turn_pdf_data_populates_core_fields():
    specialty = Specialties(id=uuid4(), name="Clínica médica", description="", department_id=uuid4())
    user = _make_user(telephone="555-1234")
    doctor = _make_doctor(specialty)
    service = _make_service(specialty)

    turn = Turns(
        id=uuid4(),
        reason="Control",
        state=TurnsState.waiting,
        date=date(2024, 6, 15),
        date_created=date(2024, 6, 1),
        date_limit=date(2024, 6, 10),
        time=time(9, 30),
        user=user,
        doctor=doctor,
        services=[service],
        appointment=Appointments(id=uuid4()),
    )

    pdf_data = build_turn_pdf_data(turn)

    assert pdf_data.turn_id == str(turn.id)
    assert pdf_data.patient_full_name == "Ada Lovelace"
    assert pdf_data.doctor_full_name == "Gregory House"
    assert pdf_data.doctor_specialty == "Clínica médica"
    assert pdf_data.scheduled_date == "2024-06-15"
    assert pdf_data.scheduled_time == "09:30"
    assert pdf_data.services_summary == "Consulta general ($ 1500.00)"
    assert pdf_data.total_price == 1500.0
    assert pdf_data.patient_phone == "555-1234"
    assert pdf_data.appointment_id == str(turn.appointment.id)
    assert pdf_data.services[0].name == service.name


def test_build_turn_pdf_data_handles_missing_values():
    turn = Turns(
        id=uuid4(),
        reason=None,
        state=TurnsState.waiting,
        date=date(2024, 6, 20),
        date_created=date(2024, 6, 1),
        date_limit=date(2024, 6, 19),
        time=time(11, 0),
        user=None,
        doctor=None,
        services=[],
    )

    pdf_data = build_turn_pdf_data(turn)

    assert pdf_data.patient_full_name == "Paciente sin datos"
    assert pdf_data.doctor_full_name == "Profesional no asignado"
    assert pdf_data.doctor_specialty == "Especialidad no especificada"
    assert pdf_data.services_summary == "Sin servicios asociados"
    assert pdf_data.total_price == 0.0
