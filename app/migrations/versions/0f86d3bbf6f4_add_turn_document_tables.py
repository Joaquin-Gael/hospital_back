"""add turn document tables

Revision ID: 0f86d3bbf6f4
Revises: 500a93020747
Create Date: 2025-09-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '0f86d3bbf6f4'
down_revision: Union[str, None] = '500a93020747'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'turn_documents',
        sa.Column('turn_document_id', sa.Uuid(), nullable=False),
        sa.Column('turn_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('file_path', sa.String(length=512), nullable=False),
        sa.Column('generated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['turn_id'], ['turns.turn_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('turn_document_id')
    )
    op.create_index('ix_turn_documents_turn_id', 'turn_documents', ['turn_id'], unique=False)
    op.create_index('ix_turn_documents_user_id', 'turn_documents', ['user_id'], unique=False)

    op.create_table(
        'turn_document_downloads',
        sa.Column('turn_document_download_id', sa.Uuid(), nullable=False),
        sa.Column('turn_document_id', sa.Uuid(), nullable=False),
        sa.Column('turn_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('downloaded_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['turn_document_id'], ['turn_documents.turn_document_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['turn_id'], ['turns.turn_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('turn_document_download_id')
    )
    op.create_index('ix_turn_document_downloads_document_id', 'turn_document_downloads', ['turn_document_id'], unique=False)
    op.create_index('ix_turn_document_downloads_turn_id', 'turn_document_downloads', ['turn_id'], unique=False)
    op.create_index('ix_turn_document_downloads_user_id', 'turn_document_downloads', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_turn_document_downloads_user_id', table_name='turn_document_downloads')
    op.drop_index('ix_turn_document_downloads_turn_id', table_name='turn_document_downloads')
    op.drop_index('ix_turn_document_downloads_document_id', table_name='turn_document_downloads')
    op.drop_table('turn_document_downloads')
    op.drop_index('ix_turn_documents_user_id', table_name='turn_documents')
    op.drop_index('ix_turn_documents_turn_id', table_name='turn_documents')
    op.drop_table('turn_documents')
