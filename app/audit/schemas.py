"""Pydantic schemas for the audit subsystem."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .taxonomy import AuditAction, AuditSeverity, AuditTargetType


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditEventBase(BaseModel):
    """Shared attributes for audit payloads."""

    action: AuditAction
    severity: AuditSeverity = AuditSeverity.INFO
    target_type: AuditTargetType
    target_id: Optional[UUID] = None
    actor_id: Optional[UUID] = None
    request_id: Optional[str] = Field(default=None, max_length=64)
    details: Dict[str, Any] = Field(default_factory=dict)
    request_metadata: Dict[str, Any] = Field(default_factory=dict)


class AuditEventCreate(AuditEventBase):
    """Schema used when persisting new audit events."""

    occurred_at: datetime = Field(default_factory=_utcnow)
    recorded_at: Optional[datetime] = Field(default=None)


class AuditEventRead(AuditEventBase):
    """Schema returned when reading audit events."""

    id: UUID
    occurred_at: datetime
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)
