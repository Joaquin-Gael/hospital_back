"""Add audit events table to persist structured audit logs.

Revision ID: 9b6655ff4200
Revises: 441c9277c345
Create Date: 2024-06-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "9b6655ff4200"
down_revision: Union[str, None] = "441c9277c345"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


audit_action_enum = postgresql.ENUM(
    "mark_login",
    "login_failed",
    "activate",
    "deactivate",
    "update_state",
    "appointment_state_updated",
    "create",
    "update",
    "delete",
    "token_issued",
    "token_revoked",
    "token_invalid",
    "rate_limit_triggered",
    "password_reset_requested",
    "password_reset_completed",
    "turn_document_generated",
    "turn_document_downloaded",
    "payment_succeeded",
    "payment_cancelled",
    "payment_failed",
    name="audit_action",
    create_type=False,
)

audit_severity_enum = postgresql.ENUM("info", "warning", "critical", name="audit_severity", create_type=False)

audit_target_type_enum = postgresql.ENUM(
    "User",
    "Doctor",
    "Turn",
    "Payment",
    "StorageEntry",
    "AuthToken",
    "Session",
    name="audit_target_type",
    create_type=False,
)


def upgrade() -> None:
    """Create audit_events table and supporting enums/indexes."""

    bind = op.get_bind()
    audit_action_enum.create(bind, checkfirst=True)
    audit_severity_enum.create(bind, checkfirst=True)
    audit_target_type_enum.create(bind, checkfirst=True)

    inspector = sa.inspect(bind)
    if "audit_events" in inspector.get_table_names():
        return

    op.create_table(
        "audit_events",
        sa.Column("audit_event_id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("action", audit_action_enum, nullable=False),
        sa.Column("severity", audit_severity_enum, nullable=False, server_default="info"),
        sa.Column("target_type", audit_target_type_enum, nullable=False),
        sa.Column("target_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("request_metadata", sa.JSON(), nullable=False),
    )

    op.create_index("ix_audit_events_occurred_at", "audit_events", ["occurred_at"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_severity", "audit_events", ["severity"])
    op.create_index("ix_audit_events_target_type", "audit_events", ["target_type"])
    op.create_index("ix_audit_events_target_id", "audit_events", ["target_id"])
    op.create_index("ix_audit_events_actor_id", "audit_events", ["actor_id"])


def downgrade() -> None:
    """Drop audit_events table and enums."""

    op.drop_index("ix_audit_events_actor_id", table_name="audit_events")
    op.drop_index("ix_audit_events_target_id", table_name="audit_events")
    op.drop_index("ix_audit_events_target_type", table_name="audit_events")
    op.drop_index("ix_audit_events_severity", table_name="audit_events")
    op.drop_index("ix_audit_events_action", table_name="audit_events")
    op.drop_index("ix_audit_events_occurred_at", table_name="audit_events")
    op.drop_table("audit_events")

    bind = op.get_bind()
    audit_target_type_enum.drop(bind, checkfirst=True)
    audit_severity_enum.drop(bind, checkfirst=True)
    audit_action_enum.drop(bind, checkfirst=True)
