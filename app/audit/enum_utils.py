"""Utilities for synchronising application enums with the database."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping, Sequence

from sqlalchemy import text
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import literal
from sqlmodel import Session

from .taxonomy import AuditAction, AuditSeverity, AuditTargetType

_POSTGRES_DIALECT = postgresql.dialect()
_PREPARER = _POSTGRES_DIALECT.identifier_preparer


@dataclass(frozen=True)
class EnumSyncState:
    """Representation of the sync status for a single PostgreSQL enum type."""

    name: str
    expected_labels: Sequence[str]
    database_labels: Sequence[str]

    @property
    def missing_labels(self) -> list[str]:
        """Labels defined in code but not yet present in the database enum."""

        existing = set(self.database_labels)
        return [label for label in self.expected_labels if label not in existing]

    @property
    def statements(self) -> list[str]:
        """SQL statements required to bring the database enum up to date."""

        return [make_add_enum_value_sql(self.name, label) for label in self.missing_labels]


AUDIT_ENUM_DEFINITIONS: Mapping[str, type[Enum]] = {
    "audit_action": AuditAction,
    "audit_severity": AuditSeverity,
    "audit_target_type": AuditTargetType,
}


def enum_labels(enum: type[Enum]) -> list[str]:
    """Return the values defined by an Enum as strings."""

    return [member.value for member in enum]


def database_enum_labels(session: Session, enum_name: str) -> list[str]:
    """Read the labels currently registered for a PostgreSQL enum type."""

    statement = text(
        """
        SELECT e.enumlabel
        FROM pg_type t
        JOIN pg_enum e ON t.oid = e.enumtypid
        WHERE t.typname = :enum_name
        ORDER BY e.enumsortorder
        """
    ).bindparams(enum_name=enum_name)

    result = session.exec(statement)
    return [row[0] for row in result]


def make_add_enum_value_sql(enum_name: str, label: str) -> str:
    """Return an ``ALTER TYPE`` statement to add ``label`` to ``enum_name``."""

    quoted_enum = _PREPARER.format_type(enum_name)
    literal_label = literal(label).compile(
        dialect=_POSTGRES_DIALECT, compile_kwargs={"literal_binds": True}
    )
    return f"ALTER TYPE {quoted_enum} ADD VALUE IF NOT EXISTS {literal_label};"


def load_enum_sync_state(session: Session, enum_name: str, enum: type[Enum]) -> EnumSyncState:
    """Return the synchronisation state for ``enum_name``."""

    expected = enum_labels(enum)
    current = database_enum_labels(session, enum_name)
    return EnumSyncState(name=enum_name, expected_labels=expected, database_labels=current)


def build_sync_plan(
    session: Session, enum_definitions: Mapping[str, type[Enum]]
) -> list[EnumSyncState]:
    """Return the sync states for all provided enum definitions."""

    return [load_enum_sync_state(session, name, enum) for name, enum in enum_definitions.items()]


def missing_statements(states: Iterable[EnumSyncState]) -> list[str]:
    """Collect SQL statements for every enum state that is out of sync."""

    statements: list[str] = []
    for state in states:
        statements.extend(state.statements)
    return statements


__all__ = [
    "AUDIT_ENUM_DEFINITIONS",
    "EnumSyncState",
    "build_sync_plan",
    "database_enum_labels",
    "enum_labels",
    "load_enum_sync_state",
    "make_add_enum_value_sql",
    "missing_statements",
]
