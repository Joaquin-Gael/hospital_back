"""Persistence helpers for audit events."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Sequence
from uuid import UUID

from sqlmodel import Session, select

from .models import AuditEvent
from .schemas import AuditEventCreate
from .taxonomy import AuditAction, AuditTargetType


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditRepository:
    """Repository responsible for storing and querying audit events."""

    def __init__(self, session: Session):
        self._session = session

    def save(self, payload: AuditEventCreate) -> AuditEvent:
        """Persist a single audit event and return the stored model."""

        event = self._to_model(payload)
        self._session.add(event)
        self._session.commit()
        self._session.refresh(event)
        return event

    def save_many(self, payloads: Sequence[AuditEventCreate]) -> List[AuditEvent]:
        """Persist multiple audit events in a single transaction."""

        if not payloads:
            return []

        events = [self._to_model(payload) for payload in payloads]
        self._session.add_all(events)
        self._session.commit()
        for event in events:
            self._session.refresh(event)
        return events

    def list(
        self,
        *,
        actor_id: Optional[UUID] = None,
        action: Optional[AuditAction] = None,
        target_type: Optional[AuditTargetType] = None,
        occurred_after: Optional[datetime] = None,
        occurred_before: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """Retrieve audit events applying simple optional filters."""

        query = select(AuditEvent).order_by(AuditEvent.occurred_at.desc()).limit(limit)

        if actor_id:
            query = query.where(AuditEvent.actor_id == actor_id)
        if action:
            query = query.where(AuditEvent.action == action)
        if target_type:
            query = query.where(AuditEvent.target_type == target_type)
        if occurred_after:
            query = query.where(AuditEvent.occurred_at >= occurred_after)
        if occurred_before:
            query = query.where(AuditEvent.occurred_at <= occurred_before)

        return list(self._session.exec(query))

    def _to_model(self, payload: AuditEventCreate) -> AuditEvent:
        data = payload.model_dump()
        data.setdefault("recorded_at", _utcnow())
        return AuditEvent(**data)
