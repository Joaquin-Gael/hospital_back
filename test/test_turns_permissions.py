import asyncio
import os
import sys
import types
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from sqlmodel import SQLModel, Session, create_engine
from starlette.requests import Request

os.environ.setdefault("DB_URL", "sqlite:///./test.db")

api_stub = types.ModuleType("app.api")
api_stub.__path__ = [str(Path("app/api"))]
sys.modules["app.api"] = api_stub

medic_area_stub = types.ModuleType("app.api.medic_area")
medic_area_stub.__path__ = [str(Path("app/api/medic_area"))]
sys.modules["app.api.medic_area"] = medic_area_stub

if "app.api.ai_assistant" not in sys.modules:
    fake_ai_module = types.ModuleType("app.api.ai_assistant")
    fake_ai_module.router = None
    sys.modules["app.api.ai_assistant"] = fake_ai_module

for _module in ("app.api.audit", "app.api.auth", "app.api.cashes", "app.api.users"):
    if _module not in sys.modules:
        sys.modules[_module] = types.ModuleType(_module)

interfaces_stub = types.ModuleType("app.core.interfaces.medic_area")
interfaces_stub.TurnAndAppointmentRepository = type("TurnAndAppointmentRepository", (), {})
sys.modules["app.core.interfaces.medic_area"] = interfaces_stub

stripe_stub = types.ModuleType("app.core.services.stripe_payment")
stripe_stub.StripeServices = type("StripeServices", (), {"proces_payment": staticmethod(lambda *_, **__: "")})
sys.modules["app.core.services.stripe_payment"] = stripe_stub

audit_stub = types.ModuleType("app.audit")
audit_stub.AuditAction = types.SimpleNamespace(RECORD_DELETED="record_deleted")
audit_stub.AuditEmitter = type(
    "AuditEmitter",
    (),
    {"emit_event": lambda self, *_, **__: None},
)
audit_stub.AuditEventCreate = type("AuditEventCreate", (), {})
audit_stub.AuditSeverity = types.SimpleNamespace(INFO="info", WARNING="warning")
audit_stub.AuditTargetType = types.SimpleNamespace(APPOINTMENT="appointment", WEB_SESSION="web_session")
audit_stub.build_request_metadata = lambda *_: {}
audit_stub.get_audit_emitter = lambda: types.SimpleNamespace(emit_event=lambda *_, **__: None)
audit_stub.get_request_identifier = lambda *_: "request-id"
sys.modules["app.audit"] = audit_stub

db_main_stub = types.ModuleType("app.db.main")
db_main_stub.SessionDep = Any
sys.modules["app.db.main"] = db_main_stub

config_stub = types.ModuleType("app.config")
config_stub.token_key = "secret"
config_stub.api_name = "hospital"
config_stub.version = "0.0.0"
config_stub.debug = False
config_stub.token_expire_minutes = 15
config_stub.token_refresh_expire_days = 7
config_stub.db_url = "sqlite:///./test.db"
config_stub.timezone = "UTC"
config_stub.email_host = "localhost"
config_stub.email_port = 25
config_stub.email_use_tls = False
config_stub.email_host_user = "no-reply@example.com"
config_stub.email_host_password = "password"
config_stub.templates = types.SimpleNamespace(
    TemplateResponse=lambda *_, **__: types.SimpleNamespace(body=b"")
)
config_stub.parser_name = lambda folders, name: name
sys.modules["app.config"] = config_stub

for _missing in ("torch", "polars"):
    if _missing not in sys.modules:
        module = types.ModuleType(_missing)
        if _missing == "polars":
            module.DataFrame = type("DataFrame", (), {})
            module.Series = type("Series", (), {})
            module.col = lambda *_, **__: None
        sys.modules[_missing] = module

from app.api.medic_area.turns import get_turns_by_user_id  # noqa: E402
from app.models import User  # noqa: E402


@pytest.fixture
def engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'turns_permissions.db'}", echo=False)
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session


def _make_user(*, email: str, name: str, is_superuser: bool = False) -> User:
    return User(
        name=name,
        email=email,
        password="Password123!",
        dni=str(uuid4()).replace("-", "")[:8],
        is_superuser=is_superuser,
    )


def test_get_turns_by_user_id_forbidden_for_other_user(session):
    requester = _make_user(email="user@example.com", name="user")
    other_user = _make_user(email="other@example.com", name="other")

    session.add(requester)
    session.add(other_user)
    session.commit()
    session.refresh(requester)
    session.refresh(other_user)

    request = Request({"type": "http"})
    request.state.user = requester

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_turns_by_user_id(request, session, other_user.id))

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "Unauthorized to inspect other users turns"


def test_get_turns_by_user_id_returns_404_when_authenticated_user_missing(session):
    missing_user = _make_user(email="ghost@example.com", name="ghost", is_superuser=True)
    other_user = _make_user(email="other@example.com", name="other")

    session.add(other_user)
    session.commit()
    session.refresh(other_user)

    request = Request({"type": "http"})
    request.state.user = missing_user

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_turns_by_user_id(request, session, other_user.id))

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "Authenticated user not found"
