"""scope repository URL uniqueness to repository owner

Revision ID: 7c0d2f1a4b6e
Revises: 29e9809be8c8
Create Date: 2026-08-12

"""
from typing import Sequence, Union

from alembic import op

revision: str = "7c0d2f1a4b6e"
down_revision: Union[str, Sequence[str], None] = "29e9809be8c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Replace global GitHub URL uniqueness with owner-scoped uniqueness."""
    op.drop_constraint(
        "repositories_github_url_key",
        "repositories",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_owner_repository",
        "repositories",
        ["owner_id", "github_url"],
    )


def downgrade() -> None:
    """Restore global GitHub URL uniqueness."""
    op.drop_constraint(
        "uq_owner_repository",
        "repositories",
        type_="unique",
    )
    op.create_unique_constraint(
        "repositories_github_url_key",
        "repositories",
        ["github_url"],
    )