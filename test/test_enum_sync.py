from __future__ import annotations

import io
from contextlib import redirect_stdout

import pytest
from sqlalchemy import text
from sqlmodel import Session, create_engine

from app.audit.enum_utils import AUDIT_ENUM_DEFINITIONS, enum_labels


@pytest.fixture()
def fake_postgres():
    engine = create_engine("sqlite://", future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE pg_type (oid INTEGER PRIMARY KEY AUTOINCREMENT, typname TEXT NOT NULL)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE pg_enum (enumtypid INTEGER NOT NULL, enumlabel TEXT NOT NULL, "
                "enumsortorder INTEGER NOT NULL)"
            )
        )

        for oid, (enum_name, enum) in enumerate(AUDIT_ENUM_DEFINITIONS.items(), start=1):
            conn.execute(
                text("INSERT INTO pg_type (oid, typname) VALUES (:oid, :typname)"),
                {"oid": oid, "typname": enum_name},
            )
            labels = enum_labels(enum)
            if labels:
                conn.execute(
                    text(
                        "INSERT INTO pg_enum (enumtypid, enumlabel, enumsortorder) "
                        "VALUES (:enumtypid, :enumlabel, :enumsortorder)"
                    ),
                    {"enumtypid": oid, "enumlabel": labels[0], "enumsortorder": 1},
                )
    yield engine
    engine.dispose()


def _populate_missing(engine) -> None:
    with engine.begin() as conn:
        for oid, (enum_name, enum) in enumerate(AUDIT_ENUM_DEFINITIONS.items(), start=1):
            labels = enum_labels(enum)
            for index, label in enumerate(labels, start=1):
                exists = conn.execute(
                    text(
                        "SELECT 1 FROM pg_enum WHERE enumtypid = :enumtypid AND enumlabel = :enumlabel"
                    ),
                    {"enumtypid": oid, "enumlabel": label},
                ).first()
                if exists is None:
                    conn.execute(
                        text(
                            "INSERT INTO pg_enum (enumtypid, enumlabel, enumsortorder) "
                            "VALUES (:enumtypid, :enumlabel, :enumsortorder)"
                        ),
                        {"enumtypid": oid, "enumlabel": label, "enumsortorder": index},
                    )


def test_validate_enum_sync_detects_and_resolves_missing_values(fake_postgres):
    from scripts import validate_enum_sync

    def _session_factory() -> Session:
        return Session(fake_postgres)

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = validate_enum_sync.main([], session_factory_override=_session_factory)
    output = buffer.getvalue()

    assert exit_code == 1
    assert "Missing enum values detected" in output

    _populate_missing(fake_postgres)

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = validate_enum_sync.main([], session_factory_override=_session_factory)
    output = buffer.getvalue()

    assert exit_code == 0
    assert "synchronized" in output.lower()
