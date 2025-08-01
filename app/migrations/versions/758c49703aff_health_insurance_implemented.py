"""health insurance implemented

Revision ID: 758c49703aff
Revises: 279f716380f3
Create Date: 2025-06-24 17:34:00.695408

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '758c49703aff'
down_revision: Union[str, None] = '279f716380f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
