import asyncio
import os
import sys
import types
from datetime import date, timedelta, time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from sqlmodel import SQLModel, Session, create_engine, select
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
stripe_stub.StripeServices = type(
    "StripeServices",
    (),
    {
        "proces_payment": staticmethod(
            lambda *_, **__: {
                "checkout_url": "",
                "session_id": "",
                "amount_total": 0,
                "discount": 0,
            }
        )
    },
)
sys.modules["app.core.services.stripe_payment"] = stripe_stub

audit_stub = types.ModuleType("app.audit")
audit_stub.AuditAction = types.SimpleNamespace(
    RECORD_DELETED="record_deleted",
    TURN_DOCUMENT_GENERATED="turn_document_generated",
    TURN_DOCUMENT_DOWNLOADED="turn_document_downloaded",
)
audit_stub.AuditEmitter = type(
    "AuditEmitter",
    (),
    {"emit_event": lambda self, *_, **__: None},
)
class _AuditEventCreate:
    def __init__(self, **payload):
        for key, value in payload.items():
            setattr(self, key, value)
        self.payload = payload


audit_stub.AuditEventCreate = _AuditEventCreate
audit_stub.AuditSeverity = types.SimpleNamespace(INFO="info", WARNING="warning")
audit_stub.AuditTargetType = types.SimpleNamespace(
    APPOINTMENT="appointment",
    WEB_SESSION="web_session",
    TURN_DOCUMENT="turn_document",
)
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
config_stub.media_dir = Path("media")
sys.modules["app.config"] = config_stub

for _missing in ("torch", "polars"):
    if _missing not in sys.modules:
        module = types.ModuleType(_missing)
        if _missing == "polars":
            module.DataFrame = type("DataFrame", (), {})
            module.Series = type("Series", (), {})
            module.col = lambda *_, **__: None
        sys.modules[_missing] = module

if "pymupdf" not in sys.modules:
    pymupdf_stub = types.ModuleType("pymupdf")

    class _FakePdfPage:
        def insert_text(self, *_args, **_kwargs):
            return None

    class _FakePdfDocument:
        def __init__(self):
            self._closed = False

        def new_page(self):
            return _FakePdfPage()

        def tobytes(self):
            return b"%PDF-stub"

        def close(self):
            self._closed = True

    pymupdf_stub.open = lambda *_, **__: _FakePdfDocument()
    sys.modules["pymupdf"] = pymupdf_stub

from app.api.medic_area.turns import get_turn_data_pdf, get_turns_by_user_id  # noqa: E402
from app.core.services.pdf import get_or_create_turn_document  # noqa: E402
from app.models import (  # noqa: E402
    Departments,
    Doctors,
    Locations,
    RenameTurnsStateMixin,
    Specialties,
    TurnDocument,
    TurnDocumentDownload,
    Turns,
    TurnsState,
    User,
)


@pytest.fixture
def engine(tmp_path):
    RenameTurnsStateMixin.__declare_last__.__func__(Turns)
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


@pytest.fixture
def in_memory_pdf_storage(monkeypatch):
    storage: Dict[str, bytes] = {}

    def fake_save_pdf(filename: str, content: bytes, *, subdir: Optional[str | Path] = None) -> str:
        normalized_name = Path(filename).name
        sub_parts = [part for part in Path(subdir or "").parts if part]
        relative_path = "/".join(["turns", *sub_parts, normalized_name])
        storage[relative_path] = bytes(content)
        return relative_path

    def fake_load_pdf(relative_path: str | Path) -> bytes:
        key = Path(relative_path).as_posix()
        if key not in storage:
            raise FileNotFoundError(relative_path)
        return storage[key]

    monkeypatch.setattr("app.core.services.pdf.save_pdf_file", fake_save_pdf)
    monkeypatch.setattr("app.core.services.pdf.load_pdf_file", fake_load_pdf)

    return storage


@pytest.fixture
def turn_factory(session):
    def factory(
        *,
        patient: Optional[User] = None,
        doctor_user: Optional[User] = None,
        reason: str = "Consulta general",
    ) -> tuple[Turns, User, User, Doctors]:
        patient = patient or _make_user(
            email=f"patient-{uuid4().hex}@example.com",
            name="patient",
        )
        if patient.id is None or session.get(User, patient.id) is None:
            session.add(patient)
            session.commit()
            session.refresh(patient)

        location = Locations(
            name=f"Location {uuid4().hex[:6]}",
            description="Ubicación de prueba",
        )
        session.add(location)
        session.commit()
        session.refresh(location)

        department = Departments(
            name=f"Departamento {uuid4().hex[:6]}",
            description="Departamento de prueba",
            location_id=location.id,
        )
        session.add(department)
        session.commit()
        session.refresh(department)

        specialty = Specialties(
            name=f"Especialidad {uuid4().hex[:6]}",
            description="Especialidad de prueba",
            department_id=department.id,
        )
        session.add(specialty)
        session.commit()
        session.refresh(specialty)

        doctor_user = doctor_user or _make_user(
            email=f"doctor-{uuid4().hex}@example.com",
            name="doctor",
        )
        if doctor_user.id is None or session.get(User, doctor_user.id) is None:
            session.add(doctor_user)
            session.commit()
            session.refresh(doctor_user)

        doctor = Doctors(
            id=doctor_user.id,
            name=doctor_user.name,
            email=doctor_user.email,
            password=doctor_user.password,
            dni=doctor_user.dni,
            speciality_id=specialty.id,
        )
        session.add(doctor)
        session.commit()
        session.refresh(doctor)

        turn = Turns(
            reason=reason,
            state=TurnsState.waiting,
            date=date.today(),
            date_limit=date.today() + timedelta(days=7),
            user_id=patient.id,
            doctor_id=doctor.id,
            time=time(hour=10, minute=0),
        )
        turn.user = patient
        turn.doctor = doctor
        session.add(turn)
        session.commit()
        session.refresh(turn)

        return turn, patient, doctor_user, doctor

    return factory


class _RecorderEmitter:
    def __init__(self) -> None:
        self.events: list[Any] = []

    async def emit_event(self, event: Any) -> None:
        self.events.append(event)


def _build_request(
    user: User,
    *,
    headers: Optional[Dict[str, str]] = None,
    scopes: Optional[Iterable[str]] = None,
    client: tuple[str, int] = ("127.0.0.1", 0),
) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/turns",
        "headers": [
            (key.lower().encode(), value.encode())
            for key, value in (headers or {}).items()
        ],
        "client": client,
    }

    async def _receive() -> Dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    request = Request(scope, receive=_receive)
    request.state.user = user
    request.state.scopes = list(scopes or [])
    return request


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


def test_get_or_create_turn_document_generates_pdf(session, turn_factory, in_memory_pdf_storage):
    turn, patient, _, _ = turn_factory()

    document, pdf_bytes, created = get_or_create_turn_document(session, turn)

    assert created is True
    assert document.turn_id == turn.id
    assert document.user_id == patient.id
    assert pdf_bytes.startswith(b"%PDF")
    assert document.file_path in in_memory_pdf_storage
    assert in_memory_pdf_storage[document.file_path] == pdf_bytes


def test_get_or_create_turn_document_reuses_existing_pdf(session, turn_factory, in_memory_pdf_storage):
    turn, _, _, _ = turn_factory()

    first_document, first_bytes, first_created = get_or_create_turn_document(session, turn)
    assert first_created is True
    assert first_bytes.startswith(b"%PDF")

    second_document, second_bytes, second_created = get_or_create_turn_document(session, turn)

    assert second_created is False
    assert second_document.id == first_document.id
    assert second_bytes == first_bytes


def test_patient_downloads_turn_pdf_and_registers_download(
    session, turn_factory, in_memory_pdf_storage
):
    turn, patient, _, _ = turn_factory()
    request = _build_request(
        patient,
        headers={
            "x-download-channel": "  portal ",
            "user-agent": "pytest-agent",
        },
        scopes=[],
        client=("198.51.100.10", 443),
    )
    emitter = _RecorderEmitter()

    response = asyncio.run(
        get_turn_data_pdf(
            request,
            session,
            user_id=patient.id,
            turn_id=turn.id,
            emitter=emitter,
        )
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.media_type == "application/pdf"
    assert response.body.startswith(b"%PDF")
    assert response.headers["content-disposition"] == f"attachment; filename=turn_{turn.id}.pdf"

    documents = session.exec(select(TurnDocument)).all()
    assert len(documents) == 1
    document = documents[0]
    assert document.user_id == patient.id
    assert in_memory_pdf_storage[document.file_path] == response.body

    downloads = session.exec(select(TurnDocumentDownload)).all()
    assert len(downloads) == 1
    download = downloads[0]
    assert download.user_id == patient.id
    assert download.channel == "portal"
    assert download.client_ip == "198.51.100.10"
    assert download.user_agent == "pytest-agent"
    assert len(emitter.events) == 2


def test_assigned_doctor_with_scope_downloads_turn_pdf(
    session, turn_factory, in_memory_pdf_storage
):
    turn, patient, doctor_user, _ = turn_factory()
    request = _build_request(
        doctor_user,
        headers={"user-agent": "doctor-agent"},
        scopes=["doc"],
        client=("203.0.113.5", 8080),
    )
    emitter = _RecorderEmitter()

    response = asyncio.run(
        get_turn_data_pdf(
            request,
            session,
            user_id=doctor_user.id,
            turn_id=turn.id,
            emitter=emitter,
        )
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.body.startswith(b"%PDF")

    documents = session.exec(select(TurnDocument)).all()
    assert len(documents) == 1
    document = documents[0]
    assert document.user_id == patient.id
    assert document.file_path in in_memory_pdf_storage

    doctor_downloads = session.exec(
        select(TurnDocumentDownload).where(TurnDocumentDownload.user_id == doctor_user.id)
    ).all()
    assert len(doctor_downloads) == 1
    download = doctor_downloads[0]
    assert download.channel == "api"
    assert download.client_ip == "203.0.113.5"
    assert download.user_agent == "doctor-agent"
    assert len(emitter.events) == 2


def test_superuser_downloads_other_user_turn_pdf(session, turn_factory, in_memory_pdf_storage):
    turn, patient, _, _ = turn_factory()
    superuser = _make_user(
        email="admin@example.com",
        name="admin",
        is_superuser=True,
    )
    session.add(superuser)
    session.commit()
    session.refresh(superuser)

    request = _build_request(
        superuser,
        headers={"user-agent": "super-agent"},
        scopes=[],
        client=("192.0.2.1", 9000),
    )
    emitter = _RecorderEmitter()

    response = asyncio.run(
        get_turn_data_pdf(
            request,
            session,
            user_id=patient.id,
            turn_id=turn.id,
            emitter=emitter,
        )
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.body.startswith(b"%PDF")

    documents = session.exec(select(TurnDocument)).all()
    assert len(documents) == 1
    document = documents[0]
    assert document.user_id == patient.id
    assert document.file_path in in_memory_pdf_storage

    downloads = session.exec(
        select(TurnDocumentDownload).where(TurnDocumentDownload.user_id == superuser.id)
    ).all()
    assert len(downloads) == 1
    download = downloads[0]
    assert download.channel == "api"
    assert download.client_ip == "192.0.2.1"
    assert download.user_agent == "super-agent"
    assert len(emitter.events) == 2
