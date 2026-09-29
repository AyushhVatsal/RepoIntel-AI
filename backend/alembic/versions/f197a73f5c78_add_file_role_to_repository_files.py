"""add file role to repository files

Revision ID: f197a73f5c78
Revises: 59d528f0c29b
Create Date: 2026-09-29 19:14:50.617800
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f197a73f5c78"
down_revision: Union[str, Sequence[str], None] = "59d528f0c29b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    file_role_enum = sa.Enum(
        "SOURCE",
        "TEST",
        "FIXTURE",
        "CONFIG",
        "DOCUMENTATION",
        "UNKNOWN",
        name="filerole",
    )

    file_role_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "repository_files",
        sa.Column(
            "role",
            file_role_enum,
            nullable=True,
        ),
    )

    op.execute(
        "UPDATE repository_files SET role = 'UNKNOWN' "
        "WHERE role IS NULL"
    )

    op.alter_column(
        "repository_files",
        "role",
        nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_column(
        "repository_files",
        "role",
    )

    file_role_enum = sa.Enum(
        "SOURCE",
        "TEST",
        "FIXTURE",
        "CONFIG",
        "DOCUMENTATION",
        "UNKNOWN",
        name="filerole",
    )

    file_role_enum.drop(op.get_bind(), checkfirst=True)