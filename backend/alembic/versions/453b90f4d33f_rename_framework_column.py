"""rename framework column"""

from typing import Sequence, Union

from alembic import op


revision: str = "453b90f4d33f"
down_revision: Union[str, Sequence[str], None] = "2b08890419d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "repositories",
        "framework",
        new_column_name="primary_framework",
    )


def downgrade() -> None:
    op.alter_column(
        "repositories",
        "primary_framework",
        new_column_name="framework",
    )