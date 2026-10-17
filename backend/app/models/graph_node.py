from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class GraphNodeType(str, Enum):
    REPOSITORY = "REPOSITORY"
    FILE = "FILE"
    SYMBOL = "SYMBOL"
    CHUNK = "CHUNK"


class GraphNode(Base):
    __tablename__ = "graph_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    repository_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "repositories.id",
            ondelete="CASCADE",
            name="fk_graph_nodes_repository_id_repositories",
        ),
        nullable=False,
    )

    node_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    entity_key: Mapped[str] = mapped_column(
        String(1200),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    qualified_name: Mapped[str | None] = mapped_column(
        String(1200),
        nullable=True,
    )

    file_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    symbol_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    chunk_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # The database column is named "metadata".
    # Use node_metadata in Python because SQLAlchemy reserves "metadata".
    node_metadata: Mapped[dict] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["repository_id", "file_id"],
            ["repository_files.repository_id", "repository_files.id"],
            name="fk_graph_nodes_repository_file",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["repository_id", "file_id", "symbol_id"],
            [
                "repository_symbols.repository_id",
                "repository_symbols.file_id",
                "repository_symbols.id",
            ],
            name="fk_graph_nodes_repository_file_symbol",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["repository_id", "file_id", "chunk_id"],
            ["chunks.repository_id", "chunks.file_id", "chunks.id"],
            name="fk_graph_nodes_repository_file_chunk",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "repository_id",
            "id",
            name="uq_graph_nodes_repository_id_id",
        ),
        UniqueConstraint(
            "repository_id",
            "node_type",
            "entity_key",
            name="uq_graph_nodes_entity_identity",
        ),
        CheckConstraint(
            "node_type IN ('REPOSITORY', 'FILE', 'SYMBOL', 'CHUNK')",
            name="ck_graph_nodes_node_type",
        ),
        CheckConstraint(
            """
            (
                node_type = 'REPOSITORY'
                AND file_id IS NULL
                AND symbol_id IS NULL
                AND chunk_id IS NULL
            )
            OR
            (
                node_type = 'FILE'
                AND file_id IS NOT NULL
                AND symbol_id IS NULL
                AND chunk_id IS NULL
            )
            OR
            (
                node_type = 'SYMBOL'
                AND file_id IS NOT NULL
                AND symbol_id IS NOT NULL
                AND chunk_id IS NULL
            )
            OR
            (
                node_type = 'CHUNK'
                AND file_id IS NOT NULL
                AND symbol_id IS NULL
                AND chunk_id IS NOT NULL
            )
            """,
            name="ck_graph_nodes_entity_shape",
        ),
        Index(
            "uq_graph_nodes_repository_root",
            "repository_id",
            unique=True,
            postgresql_where=text("node_type = 'REPOSITORY'"),
        ),
        Index(
            "ix_graph_nodes_repository_type",
            "repository_id",
            "node_type",
        ),
    )