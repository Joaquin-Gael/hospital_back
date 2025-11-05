"""Database models for audit events."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, JSON
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import UUID as UUID_TYPE

from sqlmodel import Field, SQLModel

from .taxonomy import AuditAction, AuditSeverity, AuditTargetType


def _utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


class AuditEvent(SQLModel, table=True):
    """Persistent representation of a domain audit event."""

    __tablename__ = "audit_events"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        sa_column_kwargs={"name": "audit_event_id"},
    )
    occurred_at: datetime = Field(
        default_factory=_utcnow,
        nullable=False,
        index=True,
        description="When the audited action happened in the domain.",
    )
    recorded_at: datetime = Field(
        default_factory=_utcnow,
        nullable=False,
        description="When the audit event was persisted by the backend.",
    )
    action: AuditAction = Field(
        sa_type=SQLEnum(AuditAction, name="audit_action"),
        index=True,
        nullable=False,
    )
    severity: AuditSeverity = Field(
        default=AuditSeverity.INFO,
        sa_type=SQLEnum(AuditSeverity, name="audit_severity"),
        nullable=False,
        index=True,
    )
    target_type: AuditTargetType = Field(
        sa_type=SQLEnum(AuditTargetType, name="audit_target_type"),
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
