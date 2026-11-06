"""add persistent repository indexing progress

Revision ID: c43a9e172d04
Revises: b7e4c9d2a610
Create Date: 2026-11-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c43a9e172d04"
down_revision: str | Sequence[str] | None = "b7e4c9d2a610"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "repositories",
        sa.Column(
            "indexing_progress",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "repositories",
        sa.Column(
            "indexing_stage",
            sa.String(length=100),
            nullable=False,
            server_default="queued",
        ),
    )
    op.add_column(
        "repositories",
        sa.Column(
            "indexing_processed_files",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "repositories",
        sa.Column(
            "indexing_total_files",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "repositories",
        sa.Column("indexing_error", sa.String(length=2000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("repositories", "indexing_error")
    op.drop_column("repositories", "indexing_total_files")
    op.drop_column("repositories", "indexing_processed_files")
    op.drop_column("repositories", "indexing_stage")
    op.drop_column("repositories", "indexing_progress")
