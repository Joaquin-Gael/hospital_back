"""Asynchronous pipeline to persist audit events without blocking requests."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional, TYPE_CHECKING

from app.db.session import session_factory
from app.config import (
    audit_batch_size,
    audit_enabled,
    audit_linger_seconds,
    audit_minimum_severity,
    audit_queue_size,
    audit_redact_fields,
    audit_retention_days,
    audit_retry_delay,
)

from .schemas import AuditEventCreate
from .service import AuditService
from .taxonomy import AuditSeverity

if TYPE_CHECKING:  # pragma: no cover
    from app.models import AuditRecord


_LOGGER = logging.getLogger("app.audit.pipeline")

_SEVERITY_RANK = {
    AuditSeverity.INFO: 0,
    AuditSeverity.WARNING: 1,
    AuditSeverity.CRITICAL: 2,
}

try:
    _configured_minimum_severity = AuditSeverity(audit_minimum_severity)
except ValueError:  # pragma: no cover - configuration fallback
    _configured_minimum_severity = AuditSeverity.INFO


class AuditPipeline:
    """Background worker that flushes audit events in batches."""

    def __init__(
        self,
        service: AuditService,
        *,
        max_queue_size: int = 512,
        batch_size: int = 50,
        linger_seconds: float = 0.5,
        retry_delay: float = 1.0,
    ):
        self._service = service
        self._queue: asyncio.Queue[AuditEventCreate] = asyncio.Queue(maxsize=max_queue_size)
        self._batch_size = batch_size
        self._linger_seconds = linger_seconds
        self._retry_delay = retry_delay
        self._shutdown = asyncio.Event()
        self._worker: Optional[asyncio.Task[None]] = None

    async def start(self) -> None:
        if self._worker and not self._worker.done():
            return
        self._shutdown.clear()
        self._worker = asyncio.create_task(self._run(), name="audit-pipeline-worker")

    async def stop(self) -> None:
        if not self._worker:
            return
        self._shutdown.set()
        await self._queue.join()
        await self._worker
        self._worker = None

    async def enqueue(self, event: AuditEventCreate) -> None:
        """Queue an event for asynchronous persistence."""

        if not self._worker or self._worker.done():
            await asyncio.to_thread(self._service.persist, [event])
            return

        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            _LOGGER.warning("Audit queue full; persisting event synchronously.")
            await asyncio.to_thread(self._service.persist, [event])

    async def drain(self) -> None:
        """Flush queued events. Primarily useful in tests."""

        await self._queue.join()

    async def _run(self) -> None:
        pending: list[AuditEventCreate] = []
        while True:
            if self._shutdown.is_set() and not pending and self._queue.empty():
                break

            flush_due_to_timeout = False
            try:
                item = await asyncio.wait_for(self._queue.get(), timeout=self._linger_seconds)
                pending.append(item)
            except asyncio.TimeoutError:
                flush_due_to_timeout = True

            if not pending:
                continue

            should_flush = (
                flush_due_to_timeout
                or len(pending) >= self._batch_size
                or (self._shutdown.is_set() and self._queue.empty())
            )

            if not should_flush:
                continue

            if await self._flush(pending):
                processed = len(pending)
                for _ in range(processed):
                    self._queue.task_done()
                pending.clear()
            else:
                await asyncio.sleep(self._retry_delay)

        if pending:
            if await self._flush(pending):
                processed = len(pending)
                for _ in range(processed):
                    self._queue.task_done()
            else:
                _LOGGER.error("Dropping %s audit events after repeated failures.", len(pending))

    async def _flush(self, pending: list[AuditEventCreate]) -> bool:
        batch = [self._service.ensure_recorded_at(event) for event in pending]
        try:
            await asyncio.to_thread(self._service.persist, batch)
        except Exception:  # pragma: no cover - defensive logging
            _LOGGER.exception("Failed to persist audit events batch; will retry.")
            return False
        return True


audit_service = AuditService(
    session_factory,
    retention_days=audit_retention_days,
    redacted_fields=audit_redact_fields,
)


class _DisabledAuditPipeline:
    async def start(self) -> None:  # pragma: no cover - simple no-op
        return None

    async def stop(self) -> None:  # pragma: no cover - simple no-op
        return None

    async def enqueue(self, event: AuditEventCreate) -> None:  # pragma: no cover - simple no-op
        return None

    async def drain(self) -> None:  # pragma: no cover - simple no-op
        return None


if audit_enabled:
    audit_pipeline: AuditPipeline | _DisabledAuditPipeline = AuditPipeline(
        audit_service,
        max_queue_size=audit_queue_size,
        batch_size=audit_batch_size,
        linger_seconds=audit_linger_seconds,
        retry_delay=audit_retry_delay,
    )
else:
    audit_pipeline = _DisabledAuditPipeline()


class AuditEmitter:
    """Injectable helper that converts records and pushes them through the pipeline."""

    def __init__(
        self,
        service: AuditService,
        pipeline: AuditPipeline | _DisabledAuditPipeline,
        *,
        enabled: bool = True,
        minimum_severity: AuditSeverity = AuditSeverity.INFO,
    ):
        self._service = service
        self._pipeline = pipeline
        self._enabled = enabled
        self._minimum_severity = minimum_severity

    async def emit_record(
        self,
        record: "AuditRecord",
        *,
        severity: Optional[AuditSeverity | str] = None,
        request_id: Optional[str] = None,
        request_metadata: Optional[dict] = None,
    ) -> None:
        if not self._enabled:
            return

        level = self._normalize_severity(severity)
        event = self._service.build_event(
            record,
            severity=level,
            request_id=request_id,
            request_metadata=request_metadata,
        )
        if not self._should_emit(event.severity):
            return
        await self._pipeline.enqueue(event)

    async def emit_event(self, event: AuditEventCreate) -> None:
        if not self._enabled:
            return

        severity = self._normalize_severity(event.severity)
        if not self._should_emit(severity):
            return

        payload = event.model_copy(update={"severity": severity})
        payload = self._service.ensure_recorded_at(payload)
        await self._pipeline.enqueue(payload)

    def _normalize_severity(self, value: Optional[AuditSeverity | str]) -> AuditSeverity:
        if isinstance(value, AuditSeverity):
            return value
        if value is None:
            return AuditSeverity.INFO
        try:
            return AuditSeverity(value)
        except ValueError:
            return AuditSeverity.INFO

    def _should_emit(self, severity: AuditSeverity) -> bool:
        return _SEVERITY_RANK[severity] >= _SEVERITY_RANK[self._minimum_severity]


def get_audit_emitter() -> "AuditEmitter":
    return AuditEmitter(
        audit_service,
        audit_pipeline,
        enabled=audit_enabled,
        minimum_severity=_configured_minimum_severity,
    )
