"""Domain service for converting and storing audit records."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Callable, Dict, Iterable, List, Optional

from sqlmodel import Session

from .repository import AuditRepository
from .schemas import AuditEventCreate
from .taxonomy import AuditAction, AuditSeverity, AuditTargetType
from app.models import AuditRecord


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditService:
    """Coordinates translation of domain audit records into persisted events."""

    def __init__(self, session_factory: Callable[[], Session]):
        self._session_factory = session_factory

    def build_event(
        self,
        record: AuditRecord,
        *,
        severity: AuditSeverity | None = None,
        request_id: str | None = None,
        request_metadata: Optional[Dict[str, object]] = None,
    ) -> AuditEventCreate:
        """Convert a domain :class:`AuditRecord` into a persistence payload."""

        action = self._coerce_action(record.action)
        target_type = self._coerce_target_type(record.target_type)
        metadata = dict(request_metadata or {})

        return AuditEventCreate(
            action=action,
            severity=severity or AuditSeverity.INFO,
            target_type=target_type,
            target_id=record.target_id,
            actor_id=record.actor_id,
            request_id=request_id,
            details=dict(record.details or {}),
            request_metadata=metadata,
            occurred_at=record.timestamp,
        )

    def ensure_recorded_at(self, event: AuditEventCreate) -> AuditEventCreate:
        """Return a copy of the event that includes a ``recorded_at`` timestamp."""

        if event.recorded_at is not None:
            return event
        return event.model_copy(update={"recorded_at": _utcnow()})

    async def persist_async(self, events: Iterable[AuditEventCreate]) -> None:
        """Persist events from an async context using a threadpool."""

        payloads = [self.ensure_recorded_at(event) for event in events]
        if not payloads:
            return

        await asyncio.to_thread(self.persist, payloads)

    def persist(self, events: Iterable[AuditEventCreate]) -> List[AuditEventCreate]:
        """Persist events synchronously and return the stored payloads."""

        payloads = [self.ensure_recorded_at(event) for event in events]
        if not payloads:
            return []

        with self._session_factory() as session:
            repo = AuditRepository(session)
            repo.save_many(payloads)
        return payloads

    def _coerce_action(self, raw: str) -> AuditAction:
        try:
            return AuditAction(raw)
        except ValueError:
            return AuditAction.RECORD_UPDATED

    def _coerce_target_type(self, raw: str) -> AuditTargetType:
        aliases = {
            "Doctors": AuditTargetType.DOCTOR,
            "Turns": AuditTargetType.APPOINTMENT,
            "Appointments": AuditTargetType.APPOINTMENT,
        }
        if raw in aliases:
            return aliases[raw]
        try:
            return AuditTargetType(raw)
        except ValueError:
            return AuditTargetType.STORAGE_ENTRY
