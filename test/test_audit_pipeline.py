"""Regression tests for the audit persistence layer."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlmodel import SQLModel, Session, create_engine, select

os.environ.setdefault("PASSLIB_PURE", "1")

from app.audit.models import AuditEvent
from app.audit.repository import AuditRepository
from app.audit.schemas import AuditEventCreate
from app.audit.service import AuditService
from app.audit.taxonomy import AuditAction, AuditSeverity, AuditTargetType


def _make_payload() -> AuditEventCreate:
    return AuditEventCreate(
        action=AuditAction.TOKEN_INVALID,
        severity=AuditSeverity.WARNING,
        target_type=AuditTargetType.AUTH_TOKEN,
        target_id=uuid4(),
        actor_id=uuid4(),
        request_id="req-42",
        details={"reason": "invalid_or_expired"},
        request_metadata={"ip": "127.0.0.1"},
        occurred_at=datetime.now(timezone.utc),
    )


def test_audit_payload_serializes_enum_values() -> None:
    payload = _make_payload()
    data = payload.model_dump()

    assert data["action"] == "token_invalid"
    assert data["severity"] == "warning"
    assert data["target_type"] == "AuthToken"


def test_audit_service_coerces_varied_actions() -> None:
    service = AuditService(lambda: None)

    assert service._coerce_action("token_invalid") is AuditAction.TOKEN_INVALID
    assert service._coerce_action("TOKEN_INVALID") is AuditAction.TOKEN_INVALID
    assert service._coerce_action(AuditAction.TOKEN_INVALID) is AuditAction.TOKEN_INVALID
    assert service._coerce_action("does-not-exist") is AuditAction.RECORD_UPDATED


@pytest.mark.parametrize("raw,expected", [
    ("Doctor", AuditTargetType.DOCTOR),
    ("Doctors", AuditTargetType.DOCTOR),
    ("Turns", AuditTargetType.APPOINTMENT),
    (AuditTargetType.AUTH_TOKEN, AuditTargetType.AUTH_TOKEN),
    ("unknown", AuditTargetType.STORAGE_ENTRY),
])
def test_audit_service_coerces_target_types(raw, expected) -> None:
    service = AuditService(lambda: None)
    assert service._coerce_target_type(raw) is expected


def test_repository_persists_audit_events(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'audit.db'}", echo=False)
    SQLModel.metadata.create_all(engine)

    payload = _make_payload()

    with Session(engine) as session:
        repo = AuditRepository(session)
        repo.save_many([payload])
        stored = session.exec(select(AuditEvent)).first()

    assert stored is not None
    assert stored.action == AuditAction.TOKEN_INVALID
    assert stored.severity == AuditSeverity.WARNING
    assert stored.target_type == AuditTargetType.AUTH_TOKEN
