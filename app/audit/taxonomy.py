"""Domain taxonomy for audit events.

This module centralises the vocabulary that the rest of the system must use when
emitting audit events. Keeping the values in a single place avoids subtle bugs
caused by typos and simplifies reporting by guaranteeing consistent labels.
"""

from enum import Enum


class AuditAction(str, Enum):
    """Canonical list of actions that can be audited."""

    USER_LOGIN = "mark_login"
    USER_LOGIN_FAILED = "login_failed"
    USER_ACTIVATED = "activate"
    USER_DEACTIVATED = "deactivate"
    DOCTOR_STATE_UPDATED = "update_state"
    APPOINTMENT_STATE_UPDATED = "appointment_state_updated"

    RECORD_CREATED = "create"
    RECORD_UPDATED = "update"
    RECORD_DELETED = "delete"

    TOKEN_ISSUED = "token_issued"
    TOKEN_REVOKED = "token_revoked"
    TOKEN_INVALID = "token_invalid"
    RATE_LIMIT_TRIGGERED = "rate_limit_triggered"

    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    PASSWORD_RESET_COMPLETED = "password_reset_completed"

    PAYMENT_SUCCEEDED = "payment_succeeded"
    PAYMENT_CANCELLED = "payment_cancelled"
    PAYMENT_FAILED = "payment_failed"


class AuditTargetType(str, Enum):
    """Entity types that commonly appear in audit records."""

    USER = "User"
    DOCTOR = "Doctor"
    APPOINTMENT = "Turn"
    PAYMENT = "Payment"
    STORAGE_ENTRY = "StorageEntry"
    AUTH_TOKEN = "AuthToken"
    WEB_SESSION = "Session"


class AuditSeverity(str, Enum):
    """Severity levels assigned to audit actions."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
