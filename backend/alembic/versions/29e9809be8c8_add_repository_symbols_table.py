"""add repository symbols table

Revision ID: 29e9809be8c8
Revises: 2b08890419d6
Create Date: 2026-08-12 18:50:52.401885

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '29e9809be8c8'
down_revision: Union[str, Sequence[str], None] = '2b08890419d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enable pg_trgm extension for fuzzy search (optional, for future use)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Create repository_symbols table
    op.create_table(
        'repository_symbols',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('repository_id', sa.Integer(), nullable=False),
        sa.Column('file_id', sa.Integer(), nullable=False),
        sa.Column('symbol_type', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('qualified_name', sa.String(length=1000), nullable=False),
        sa.Column('location', sa.JSON(), nullable=False),
        sa.Column('symbol_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['file_id'], ['repository_files.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('file_id', 'symbol_type', 'qualified_name', name='uq_file_symbol')
    )

    # Create indexes for performance
    op.create_index('idx_symbols_repo_type', 'repository_symbols', ['repository_id', 'symbol_type'])
    op.create_index('idx_symbols_file', 'repository_symbols', ['file_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_symbols_file', table_name='repository_symbols')
    op.drop_index('idx_symbols_repo_type', table_name='repository_symbols')
    op.drop_table('repository_symbols')
