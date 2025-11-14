"""Bring the audit_events table in sync with the domain model.

This migration is intentionally defensive: a few deployments ended up with an
``audit_events`` table that predates the current ORM model.  When that happens
the table is missing the ``action`` column altogether and the Postgres ENUM
types do not contain the newest taxonomy values.  As a consequence every audit
flush fails with ``UndefinedColumn`` and the pipeline keeps retrying forever.

The migration below makes the schema compatible regardless of the previous
state by:

* Ensuring the ENUM types expose the complete list of allowed values.
* Adding the missing ``action`` column (populating it from legacy columns when
  possible) and creating the required index.
* Recreating the whole table from scratch if it never existed in the first
  place – this keeps fresh databases working exactly as before.

Because Postgres ENUM additions are irreversible, the downgrade only drops the
column/index that were created in the upgrade phase.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


# revision identifiers, used by Alembic.
revision: str = "1f2bdb0a3f76"
down_revision: Union[str, None] = "9b6655ff4200"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


AUDIT_ACTION_VALUES = [
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
    "payment_succeeded",
    "payment_cancelled",
    "payment_failed",
    "turn_document_generated",
    "turn_document_downloaded",
]

AUDIT_SEVERITY_VALUES = ["info", "warning", "critical"]

AUDIT_TARGET_TYPE_VALUES = [
    "User",
    "Doctor",
    "Turn",
    "Payment",
    "StorageEntry",
    "AuthToken",
    "Session",
    "TurnDocument",
]


def _ensure_enum_values(bind, enum_name: str, values: list[str]) -> None:
    """Append the provided values to an ENUM type if they are missing."""

    has_type = bind.execute(
        text("SELECT 1 FROM pg_type WHERE typname = :enum_name"),
        {"enum_name": enum_name},
    ).scalar()

    if not has_type:
        sa.Enum(*values, name=enum_name).create(bind, checkfirst=True)
        existing: set[str] = set()
    else:
        existing = {
            row[0]
            for row in bind.execute(
                text(
                    "SELECT enumlabel FROM pg_enum "
                    "JOIN pg_type ON pg_enum.enumtypid = pg_type.oid "
                    "WHERE pg_type.typname = :enum_name"
                ),
                {"enum_name": enum_name},
            )
        }

    for value in values:
        if value not in existing:
            bind.execute(text(f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS '{value}'"))
            existing.add(value)


def _create_audit_events_table(bind) -> None:
    audit_action_enum = sa.Enum(*AUDIT_ACTION_VALUES, name="audit_action")
    audit_severity_enum = sa.Enum(*AUDIT_SEVERITY_VALUES, name="audit_severity")
    audit_target_type_enum = sa.Enum(*AUDIT_TARGET_TYPE_VALUES, name="audit_target_type")

    audit_action_enum.create(bind, checkfirst=True)
    audit_severity_enum.create(bind, checkfirst=True)
    audit_target_type_enum.create(bind, checkfirst=True)

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


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    table_names = set(inspector.get_table_names())

    if "audit_events" not in table_names:
        _create_audit_events_table(bind)
        return

    _ensure_enum_values(bind, "audit_action", AUDIT_ACTION_VALUES)
    _ensure_enum_values(bind, "audit_severity", AUDIT_SEVERITY_VALUES)
    _ensure_enum_values(bind, "audit_target_type", AUDIT_TARGET_TYPE_VALUES)

    columns = inspector.get_columns("audit_events")
    column_names = {column["name"] for column in columns}

    if "action" not in column_names:
        legacy_column = next(
            (candidate for candidate in ("event", "event_action", "name", "type") if candidate in column_names),
            None,
        )

        audit_action_enum = sa.Enum(
            *AUDIT_ACTION_VALUES, name="audit_action", create_type=False
        )

        op.add_column(
            "audit_events",
            sa.Column("action", audit_action_enum, nullable=False, server_default="update"),
        )

        if legacy_column:
            op.execute(
                text(
                    f"UPDATE audit_events SET action = LOWER({legacy_column}::text) "
                    "WHERE action IS NULL OR action = 'update'"
                )
            )

        op.execute(text("UPDATE audit_events SET action = 'update' WHERE action IS NULL"))
        op.alter_column("audit_events", "action", server_default=None)

    indexes = {index["name"] for index in inspector.get_indexes("audit_events")}
    if "ix_audit_events_action" not in indexes:
        op.create_index("ix_audit_events_action", "audit_events", ["action"])


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    table_names = set(inspector.get_table_names())
    if "audit_events" not in table_names:
        return

    indexes = {index["name"] for index in inspector.get_indexes("audit_events")}
    if "ix_audit_events_action" in indexes:
        op.drop_index("ix_audit_events_action", table_name="audit_events")

    columns = {column["name"] for column in inspector.get_columns("audit_events")}
    if "action" in columns:
        op.drop_column("audit_events", "action")
