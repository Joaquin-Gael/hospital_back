import pytest

from datetime import datetime
from uuid import uuid4

from app.models import User, Doctors, DoctorStates


def build_user(*, is_active: bool = True) -> User:
    return User(
        name="Test User",
        email="user@example.com",
        password="Password1!",
        dni="12345678",
        is_active=is_active,
    )


def build_doctor(*, is_active: bool = True) -> Doctors:
    return Doctors(
        name="Doc",
        email="doc@example.com",
        password="Password1!",
        dni="87654321",
        speciality_id=uuid4(),
        is_active=is_active,
    )


def test_user_mark_login_updates_last_login_and_audit():
    user = build_user()
    reference = datetime(2024, 1, 1, 12, 0, 0)

    audit = user.mark_login(timestamp=reference)

    assert user.last_login == reference
    assert audit.action == "mark_login"
    assert audit.target_id == user.id
    assert audit.details["timestamp"] == reference.isoformat()


def test_user_mark_login_on_inactive_user_raises():
    user = build_user(is_active=False)

    with pytest.raises(ValueError):
        user.mark_login()


def test_user_activation_cycle_records_audit():
    user = build_user()

    deactivate_audit = user.deactivate(reason="policy violation")
    assert not user.is_active
    assert deactivate_audit.action == "deactivate"

    with pytest.raises(ValueError):
        user.deactivate()

    activate_audit = user.activate()
    assert user.is_active
    assert activate_audit.action == "activate"

    with pytest.raises(ValueError):
        user.activate()


def test_doctor_update_state_controls_availability():
    doctor = build_doctor()

    audit_busy = doctor.update_state(DoctorStates.busy)
    assert doctor.doctor_state == DoctorStates.busy
    assert not doctor.is_available
    assert audit_busy.details["new_state"] == DoctorStates.busy.value

    audit_available = doctor.update_state(DoctorStates.available)
    assert doctor.doctor_state == DoctorStates.available
    assert doctor.is_available
    assert audit_available.details["new_state"] == DoctorStates.available.value


def test_doctor_update_state_invalid_value_raises():
    doctor = build_doctor()

    with pytest.raises(ValueError):
        doctor.update_state("invalid")  # type: ignore[arg-type]


def test_doctor_ban_is_alias_of_deactivate():
    doctor = build_doctor()

    ban_audit = doctor.ban()
    assert not doctor.is_active
    assert ban_audit.action == "deactivate"

    with pytest.raises(ValueError):
        doctor.ban()
