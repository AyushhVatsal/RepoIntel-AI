"""add hnsw index for embedding similarity search

Revision ID: 59d528f0c29b
Revises: 7524bb189201
Create Date: 2026-09-06 01:08:26.359293

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "59d528f0c29b"
down_revision: Union[str, Sequence[str], None] = "7524bb189201"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE INDEX ix_embeddings_embedding_hnsw
        ON embeddings
        USING hnsw (embedding vector_cosine_ops)
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        DROP INDEX IF EXISTS ix_embeddings_embedding_hnsw
        """
    )