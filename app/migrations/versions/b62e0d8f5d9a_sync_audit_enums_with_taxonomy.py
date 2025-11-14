"""ensure audit enums include taxonomy literals

Revision ID: b62e0d8f5d9a
Revises: 1a2b3c4d5e67
Create Date: 2024-05-10 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

from app.audit.enum_utils import AUDIT_ENUM_DEFINITIONS, enum_labels, make_add_enum_value_sql

# revision identifiers, used by Alembic.
revision: str = "b62e0d8f5d9a"
down_revision: Union[str, None] = "1a2b3c4d5e67"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for enum_name, enum in AUDIT_ENUM_DEFINITIONS.items():
        for label in enum_labels(enum):
            op.execute(make_add_enum_value_sql(enum_name, label))


def downgrade() -> None:
    # Values added to PostgreSQL enums cannot be removed without manual intervention.
    pass
