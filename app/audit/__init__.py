"""Audit module primitives and schema definitions."""

from importlib import import_module
from typing import Any

from .taxonomy import AuditAction, AuditSeverity, AuditTargetType
from .models import AuditEvent
from .schemas import AuditEventCreate, AuditEventRead
from .repository import AuditRepository
from .service import AuditService
from .utils import build_request_metadata, get_request_identifier
from .pipeline import AuditPipeline, audit_pipeline, get_audit_emitter, AuditEmitter

_PIPELINE_EXPORTS = {
    "AuditEmitter",
    "AuditPipeline",
    "audit_pipeline",
    "get_audit_emitter",
}

__all__ = [
    "AuditAction",
    "AuditSeverity",
    "AuditTargetType",
    "AuditEvent",
    "AuditEventCreate",
    "AuditEventRead",
    "AuditRepository",
    "AuditService",
    "AuditEmitter",
    "AuditPipeline",
    "audit_pipeline",
    "get_audit_emitter",
    "build_request_metadata",
    "get_request_identifier",
]


def __getattr__(name: str) -> Any:  # pragma: no cover - passthrough accessor
    if name in _PIPELINE_EXPORTS:
        module = import_module("app.audit.pipeline")
        attr = getattr(module, name)
        globals()[name] = attr
        return attr
    raise AttributeError(f"module 'app.audit' has no attribute {name!r}")
