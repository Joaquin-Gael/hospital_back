"""add payment tables

Revision ID: a8f3e1e78f5e
Revises: d53e602779d3
Create Date: 2025-06-03 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8f3e1e78f5e'
down_revision: Union[str, None] = 'd53e602779d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


payment_status_enum = sa.Enum(
    'pending', 'succeeded', 'failed', 'cancelled', name='paymentstatus'
)
payment_method_enum = sa.Enum('card', 'cash', 'transfer', name='paymentmethod')


def upgrade() -> None:
    """Create payments and payment_items tables."""
    op.create_table(
        'payments',
        sa.Column('payment_id', sa.UUID(), nullable=False),
        sa.Column('turn_id', sa.UUID(), nullable=False),
        sa.Column('appointment_id', sa.UUID(), nullable=True),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('status', payment_status_enum, nullable=False),
        sa.Column('payment_method', payment_method_enum, nullable=False),
        sa.Column('amount_total', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=8), nullable=False),
        sa.Column('payment_url', sa.String(), nullable=True),
        sa.Column('gateway_session_id', sa.String(), nullable=True),
        sa.Column('gateway_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['turn_id'], ['turns.turn_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['appointment_id'], ['appointments.appointment_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('payment_id')
    )
    op.create_index('ix_payments_turn_id', 'payments', ['turn_id'])
    op.create_index('ix_payments_user_id', 'payments', ['user_id'])

    op.create_table(
        'payment_items',
        sa.Column('payment_item_id', sa.UUID(), nullable=False),
        sa.Column('payment_id', sa.UUID(), nullable=False),
        sa.Column('service_id', sa.UUID(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_amount', sa.Float(), nullable=False),
        sa.Column('total_amount', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.payment_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['service_id'], ['services.service_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('payment_item_id')
    )
    op.create_index('ix_payment_items_payment_id', 'payment_items', ['payment_id'])


def downgrade() -> None:
    """Drop payments and payment_items tables."""
    op.drop_index('ix_payment_items_payment_id', table_name='payment_items')
    op.drop_table('payment_items')

    op.drop_index('ix_payments_user_id', table_name='payments')
    op.drop_index('ix_payments_turn_id', table_name='payments')
    op.drop_table('payments')

    payment_status_enum.drop(op.get_bind(), checkfirst=True)
    payment_method_enum.drop(op.get_bind(), checkfirst=True)
