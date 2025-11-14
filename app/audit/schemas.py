"""Pydantic schemas for the audit subsystem."""

from __future__ import annotations

from app.config import timezone as env_timezone

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Type
from zoneinfo import ZoneInfo
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .taxonomy import AuditAction, AuditSeverity, AuditTargetType


def _utcnow() -> datetime:
    return datetime.now(ZoneInfo(env_timezone))


class AuditEventBase(BaseModel):
    """Shared attributes for audit payloads."""

    action: str
    severity: str = Field(default=AuditSeverity.INFO.value)
    target_type: str
    target_id: Optional[UUID] = None
    actor_id: Optional[UUID] = None
    request_id: Optional[str] = Field(default=None, max_length=64)
    details: Dict[str, Any] = Field(default_factory=dict)
    request_metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(use_enum_values=True)

    @staticmethod
    def _normalise_enum_literal(
        raw: Any,
        enum_cls: Type[Enum],
    ) -> str | Any:
        """Return the canonical enum value when *raw* matches *enum_cls*."""

        if isinstance(raw, enum_cls):
            return raw.value  # type: ignore[return-value]

        if raw is None:
            return raw

        literal = str(raw).strip()
        if not literal:
            return literal

        for member in enum_cls:  # type: ignore[assignment]
            if literal == member.value:
                return member.value

        literal_fold = literal.casefold()
        for member in enum_cls:  # type: ignore[assignment]
            if literal_fold == member.value.casefold():
                return member.value

        literal_upper = literal.upper()
        try:
            return enum_cls[literal_upper].value  # type: ignore[index]
        except KeyError:
            pass

        for member in enum_cls:  # type: ignore[assignment]
            if literal_fold == member.name.lower():
                return member.value

        return literal

    @field_validator("action", mode="before")
    @classmethod
    def _coerce_action(cls, raw: Any) -> Any:
        return cls._normalise_enum_literal(raw, AuditAction)

    @field_validator("severity", mode="before")
    @classmethod
    def _coerce_severity(cls, raw: Any) -> Any:
        return cls._normalise_enum_literal(raw, AuditSeverity)

    @field_validator("target_type", mode="before")
    @classmethod
    def _coerce_target_type(cls, raw: Any) -> Any:
        return cls._normalise_enum_literal(raw, AuditTargetType)

    @model_validator(mode="after")
    def _revalidate_taxonomy(self) -> "AuditEventBase":
        errors: list[str] = []

        def _validate(member_cls: Type[Enum], value: Any, label: str) -> None:
            try:
                member_cls(value)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                errors.append(f"Unknown audit {label} literal: {value!r}")

        _validate(AuditAction, self.action, "action")
        _validate(AuditSeverity, self.severity, "severity")
        _validate(AuditTargetType, self.target_type, "target_type")

        if errors:
            raise ValueError("; ".join(errors))

        return self


class AuditEventCreate(AuditEventBase):
    """Schema used when persisting new audit events."""

    occurred_at: datetime = Field(default_factory=_utcnow)
    recorded_at: Optional[datetime] = Field(default=None)


class AuditEventRead(AuditEventBase):
    """Schema returned when reading audit events."""

    id: UUID
    occurred_at: datetime
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)
