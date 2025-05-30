"""initial migration

Revision ID: 13ff8febe410
Revises: ab59d6beae39
Create Date: 2025-05-09 23:48:51.147246

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '13ff8febe410'
down_revision: Union[str, None] = 'ab59d6beae39'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('appointments_service_id_fkey', 'appointments', type_='foreignkey')
    op.drop_column('appointments', 'date_created')
    op.drop_column('appointments', 'service_id')
    op.drop_column('appointments', 'reason')
    op.drop_column('appointments', 'date_limit')
    op.drop_column('appointments', 'appointments_state')
    op.drop_column('appointments', 'date')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('appointments', sa.Column('date', sa.DATE(), autoincrement=False, nullable=False))
    op.add_column('appointments', sa.Column('appointments_state', postgresql.ENUM('waiting', 'finished', 'cancelled', 'rejected', 'accepted', name='turnsstate'), autoincrement=False, nullable=False))
    op.add_column('appointments', sa.Column('date_limit', sa.DATE(), autoincrement=False, nullable=False))
    op.add_column('appointments', sa.Column('reason', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('appointments', sa.Column('service_id', sa.UUID(), autoincrement=False, nullable=True))
    op.add_column('appointments', sa.Column('date_created', sa.DATE(), autoincrement=False, nullable=False))
    op.create_foreign_key('appointments_service_id_fkey', 'appointments', 'services', ['service_id'], ['service_id'])
    # ### end Alembic commands ###
