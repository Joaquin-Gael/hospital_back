"""add metadata columns to turn_document_downloads

Revision ID: 1a2b3c4d5e67
Revises: 0f86d3bbf6f4
Create Date: 2025-09-19 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1a2b3c4d5e67"
down_revision: Union[str, None] = "0f86d3bbf6f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "turn_document_downloads",
        sa.Column("channel", sa.String(length=64), nullable=False, server_default="api"),
    )
    op.add_column(
        "turn_document_downloads",
        sa.Column("client_ip", sa.String(length=45), nullable=True),
    )
    op.add_column(
        "turn_document_downloads",
        sa.Column("user_agent", sa.String(length=512), nullable=True),
    )
    op.execute(
        sa.text("UPDATE turn_document_downloads SET channel = 'api' WHERE channel IS NULL")
    )
    op.alter_column(
        "turn_document_downloads",
        "channel",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("turn_document_downloads", "user_agent")
    op.drop_column("turn_document_downloads", "client_ip")
    op.drop_column("turn_document_downloads", "channel")
