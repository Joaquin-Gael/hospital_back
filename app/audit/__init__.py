"""Audit module primitives and schema definitions."""

from .taxonomy import AuditAction, AuditSeverity, AuditTargetType
from .models import AuditEvent
from .schemas import AuditEventCreate, AuditEventRead
from .repository import AuditRepository
from .service import AuditService
from .pipeline import AuditEmitter, AuditPipeline, audit_pipeline, get_audit_emitter
from .utils import build_request_metadata, get_request_identifier

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
