"""add traceability fields to cashes

Revision ID: bb1b6f3d5b89
Revises: a8f3e1e78f5e
Create Date: 2025-11-30 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bb1b6f3d5b89'
down_revision: Union[str, None] = 'a8f3e1e78f5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'cashes',
        sa.Column('transaction_type', sa.String(length=50), nullable=False, server_default='income')
    )
    op.add_column(
        'cashes',
        sa.Column('reference_id', sa.UUID(), nullable=True)
    )
    op.add_column(
        'cashes',
        sa.Column('description', sa.String(length=255), nullable=True)
    )
    op.add_column(
        'cashes',
        sa.Column('metadata', sa.JSON(), nullable=True)
    )
    op.add_column(
        'cashes',
        sa.Column('created_by', sa.UUID(), nullable=True)
    )
    op.add_column(
        'cashes',
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now())
    )
    op.create_foreign_key(
        'fk_cashes_created_by_users',
        source_table='cashes',
        referent_table='users',
        local_cols=['created_by'],
        remote_cols=['user_id'],
        ondelete='SET NULL'
    )

    op.add_column(
        'cash_details',
        sa.Column('transaction_type', sa.String(length=50), nullable=False, server_default='income')
    )
    op.add_column(
        'cash_details',
        sa.Column('reference_id', sa.UUID(), nullable=True)
    )
    op.add_column(
        'cash_details',
        sa.Column('metadata', sa.JSON(), nullable=True)
    )
    op.add_column(
        'cash_details',
        sa.Column('created_by', sa.UUID(), nullable=True)
    )
    op.add_column(
        'cash_details',
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now())
    )
    op.create_foreign_key(
        'fk_cash_details_created_by_users',
        source_table='cash_details',
        referent_table='users',
        local_cols=['created_by'],
        remote_cols=['user_id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_cash_details_created_by_users', 'cash_details', type_='foreignkey')
    op.drop_column('cash_details', 'created_at')
    op.drop_column('cash_details', 'created_by')
    op.drop_column('cash_details', 'metadata')
    op.drop_column('cash_details', 'reference_id')
    op.drop_column('cash_details', 'transaction_type')

    op.drop_constraint('fk_cashes_created_by_users', 'cashes', type_='foreignkey')
    op.drop_column('cashes', 'created_at')
    op.drop_column('cashes', 'created_by')
    op.drop_column('cashes', 'metadata')
    op.drop_column('cashes', 'description')
    op.drop_column('cashes', 'reference_id')
    op.drop_column('cashes', 'transaction_type')
