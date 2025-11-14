"""merge heads

Revision ID: ff78846268cc
Revises: 1a2b3c4d5e67, 9b6655ff4200
Create Date: 2025-11-13 22:09:29.201889

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'ff78846268cc'
down_revision: Union[str, None] = ('1a2b3c4d5e67', '9b6655ff4200')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
