import importlib
import importlib.util
import types
import uuid
from pathlib import Path
from typing import Any

import pytest
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import ORJSONResponse
from sqlmodel import Session, SQLModel, create_engine


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


@pytest.mark.asyncio
async def test_days_by_availability_returns_404_when_specialty_missing(session: Session):
    schedules = load_schedules_module()
    request = build_request()

    with pytest.raises(HTTPException) as exc:
        await schedules.days_by_availability(request, uuid.uuid4(), session)

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Specialty not found"
