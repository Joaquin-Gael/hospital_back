"""Database models for audit events."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from enum import Enum

from pydantic import field_validator
from sqlalchemy import Column, JSON
from sqlalchemy import Column, JSON, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import UUID as UUID_TYPE
from sqlalchemy.orm import validates

from sqlmodel import Field, SQLModel

from .taxonomy import AuditAction, AuditSeverity, AuditTargetType


def _utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


class AuditEvent(SQLModel, table=True):
    """Persistent representation of a domain audit event."""

    __tablename__ = "audit_events"

    def __init__(self, **data: Any) -> None:  # type: ignore[override]
        if "action" in data:
            data["action"] = self._coerce_enum_value(data["action"], AuditAction)
        if "severity" in data:
            data["severity"] = self._coerce_enum_value(data["severity"], AuditSeverity)
        if "target_type" in data:
            data["target_type"] = self._coerce_enum_value(data["target_type"], AuditTargetType)
        super().__init__(**data)

    @staticmethod
    def _coerce_enum_value(value: Any, enum: type[Enum]) -> Any:
        if isinstance(value, str):
            try:
                return enum(value)
            except ValueError:
                try:
                    return enum[value]
                except KeyError:
                    return value
        return value

    @field_validator("action", mode="before")
    @classmethod
    def _coerce_action(cls, value: Any) -> Any:
        return cls._coerce_enum_value(value, AuditAction)

    @field_validator("severity", mode="before")
    @classmethod
    def _coerce_severity(cls, value: Any) -> Any:
        return cls._coerce_enum_value(value, AuditSeverity)

    @field_validator("target_type", mode="before")
    @classmethod
    def _coerce_target_type(cls, value: Any) -> Any:
        return cls._coerce_enum_value(value, AuditTargetType)

    @validates("action")
    def _validate_action_enum(self, key: str, value: Any) -> Any:
        return self._coerce_enum_value(value, AuditAction)

    @validates("severity")
    def _validate_severity_enum(self, key: str, value: Any) -> Any:
        return self._coerce_enum_value(value, AuditSeverity)

    @validates("target_type")
    def _validate_target_type_enum(self, key: str, value: Any) -> Any:
        return self._coerce_enum_value(value, AuditTargetType)

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        sa_column_kwargs={"name": "audit_event_id"},
    )
    occurred_at: datetime = Field(
        default_factory=_utcnow,
        sa_type=DateTime(timezone=True),
        nullable=False,
        index=True,
        description="When the audited action happened in the domain.",
    )
    recorded_at: datetime = Field(
        default_factory=_utcnow,
        sa_type=DateTime(timezone=True),
        nullable=False,
        description="When the audit event was persisted by the backend.",
    )
    action: AuditAction = Field(
        sa_type=SQLEnum(
            AuditAction,
            name="audit_action",
            values_callable=lambda enum: [member.value for member in enum],
            validate_strings=True,
        ),
        index=True,
        nullable=False,
    )
    severity: AuditSeverity = Field(
        default=AuditSeverity.INFO,
        sa_type=SQLEnum(
            AuditSeverity,
            name="audit_severity",
            values_callable=lambda enum: [member.value for member in enum],
            validate_strings=True,
        ),
        nullable=False,
        index=True,
    )
    target_type: AuditTargetType = Field(
        sa_type=SQLEnum(
            AuditTargetType,
            name="audit_target_type",
            values_callable=lambda enum: [member.value for member in enum],
            validate_strings=True,
        ),
        nullable=False,
        index=True,
    )
    target_id: Optional[UUID] = Field(
        default=None,
        sa_type=UUID_TYPE,
        nullable=True,
        index=True,
    )
    actor_id: Optional[UUID] = Field(
        default=None,
        sa_type=UUID_TYPE,
        nullable=True,
        index=True,
    )
    request_id: Optional[str] = Field(
        default=None,
        nullable=True,
        max_length=64,
        description="Correlation identifier for the request that triggered the event.",
    )
    details: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
        description="Domain-specific structured payload.",
    )
    request_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
        description="HTTP metadata such as IP, user agent or headers.",
    )
