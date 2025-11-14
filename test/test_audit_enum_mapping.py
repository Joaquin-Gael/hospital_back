import pytest

from app.audit.models import AuditEvent
from app.audit.taxonomy import AuditAction, AuditSeverity, AuditTargetType
from app.audit.service import AuditService
from app.models import AuditRecord


def test_audit_action_enum_values_are_lowercase():
    t = AuditEvent.__table__
    col = t.columns["action"]
    enums = list(getattr(col.type, "enums", []))
    assert "rate_limit_triggered" in enums
    assert "RATE_LIMIT_TRIGGERED" not in enums
    assert "mark_login" in enums and "login_failed" in enums


def test_build_event_coerces_action_value():
    from datetime import datetime
    record = AuditRecord(
        action="rate_limit_triggered",
        target_type="Session",
        target_id=None,
        actor_id=None,
        timestamp=datetime.now(),
        details={"ip": "127.0.0.1"},
    )
    service = AuditService(session_factory=lambda: None)
    event = service.build_event(record)
    assert event.action == AuditAction.RATE_LIMIT_TRIGGERED
    assert event.severity == AuditSeverity.INFO
    assert event.target_type == AuditTargetType.WEB_SESSION