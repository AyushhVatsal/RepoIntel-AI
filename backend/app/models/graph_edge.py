from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    func,
    text,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class GraphEdgeType(str, Enum):
    CONTAINS = "CONTAINS"
    DEFINES = "DEFINES"
    IMPORTS = "IMPORTS"
    HAS_CHUNK = "HAS_CHUNK"


class GraphEdge(Base):
    """A directed relationship between two graph nodes."""

    __tablename__ = "graph_edges"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    repository_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    source_node_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    target_node_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    edge_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'::json"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["repository_id"],
            ["repositories.id"],
            name="fk_graph_edges_repository_id_repositories",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["repository_id", "source_node_id"],
            ["graph_nodes.repository_id", "graph_nodes.id"],
            name="fk_graph_edges_repository_source_node",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["repository_id", "target_node_id"],
            ["graph_nodes.repository_id", "graph_nodes.id"],
            name="fk_graph_edges_repository_target_node",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "repository_id",
            "source_node_id",
            "target_node_id",
            "edge_type",
            name="uq_graph_edges_identity",
        ),
        CheckConstraint(
            "source_node_id <> target_node_id",
            name="ck_graph_edges_no_self_loop",
        ),
        CheckConstraint(
            "edge_type IN ('CONTAINS', 'DEFINES', 'IMPORTS', 'HAS_CHUNK')",
            name="ck_graph_edges_edge_type",
        ),
        Index(
            "ix_graph_edges_repository_target",
            "repository_id",
            "target_node_id",
        ),
    )