"""add graph build lifecycle fields to repositories

Revision ID: d152af743bc1
Revises: c43a9e172d04
Create Date: 2026-11-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d152af743bc1"
down_revision: str | Sequence[str] | None = "c43a9e172d04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "repositories",
        sa.Column(
            "graph_status",
            sa.String(length=30),
            nullable=False,
            server_default="not_built",
        ),
    )
    op.add_column(
        "repositories",
        sa.Column("graph_built_at", sa.DateTime(timezone=True)),
    )
    op.add_column(
        "repositories",
        sa.Column("graph_build_duration_ms", sa.Float()),
    )
    op.add_column(
        "repositories",
        sa.Column("graph_error", sa.String(length=2000)),
    )


def downgrade() -> None:
    op.drop_column("repositories", "graph_error")
    op.drop_column("repositories", "graph_build_duration_ms")
    op.drop_column("repositories", "graph_built_at")
    op.drop_column("repositories", "graph_status")
