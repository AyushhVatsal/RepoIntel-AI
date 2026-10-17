"""Add Knowledge Graph V1 tables.

Revision ID: b7e4c9d2a610
Revises: f197a73f5c78
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7e4c9d2a610"
down_revision: Union[str, Sequence[str], None] = "f197a73f5c78"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # These constraints allow composite foreign keys to validate that
    # referenced records belong to the same repository and file.
    op.create_unique_constraint(
        "uq_repository_files_repository_id_id",
        "repository_files",
        ["repository_id", "id"],
    )

    op.create_unique_constraint(
        "uq_repository_symbols_repository_file_id_id",
        "repository_symbols",
        ["repository_id", "file_id", "id"],
    )

    op.create_unique_constraint(
        "uq_chunks_repository_file_id_id",
        "chunks",
        ["repository_id", "file_id", "id"],
    )

    # ---------------------------------------------------------
    # Graph nodes
    # ---------------------------------------------------------
    op.create_table(
        "graph_nodes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("node_type", sa.String(length=30), nullable=False),
        sa.Column("entity_key", sa.String(length=1200), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("qualified_name", sa.String(length=1200), nullable=True),
        sa.Column("file_id", sa.Integer(), nullable=True),
        sa.Column("symbol_id", sa.Integer(), nullable=True),
        sa.Column("chunk_id", sa.Integer(), nullable=True),
        sa.Column(
            "metadata",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repositories.id"],
            name="fk_graph_nodes_repository_id_repositories",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["repository_id", "file_id"],
            ["repository_files.repository_id", "repository_files.id"],
            name="fk_graph_nodes_repository_file",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["repository_id", "file_id", "symbol_id"],
            [
                "repository_symbols.repository_id",
                "repository_symbols.file_id",
                "repository_symbols.id",
            ],
            name="fk_graph_nodes_repository_file_symbol",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["repository_id", "file_id", "chunk_id"],
            ["chunks.repository_id", "chunks.file_id", "chunks.id"],
            name="fk_graph_nodes_repository_file_chunk",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "repository_id",
            "id",
            name="uq_graph_nodes_repository_id_id",
        ),
        sa.UniqueConstraint(
            "repository_id",
            "node_type",
            "entity_key",
            name="uq_graph_nodes_entity_identity",
        ),
        sa.CheckConstraint(
            "node_type IN ('REPOSITORY', 'FILE', 'SYMBOL', 'CHUNK')",
            name="ck_graph_nodes_node_type",
        ),
        sa.CheckConstraint(
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
    )

    # Only one root node is allowed for each repository.
    op.create_index(
        "uq_graph_nodes_repository_root",
        "graph_nodes",
        ["repository_id"],
        unique=True,
        postgresql_where=sa.text("node_type = 'REPOSITORY'"),
    )

    op.create_index(
        "ix_graph_nodes_repository_type",
        "graph_nodes",
        ["repository_id", "node_type"],
    )

    # ---------------------------------------------------------
    # Graph edges
    # ---------------------------------------------------------
    op.create_table(
        "graph_edges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("source_node_id", sa.Integer(), nullable=False),
        sa.Column("target_node_id", sa.Integer(), nullable=False),
        sa.Column("edge_type", sa.String(length=50), nullable=False),
        sa.Column(
            "metadata",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repositories.id"],
            name="fk_graph_edges_repository_id_repositories",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["repository_id", "source_node_id"],
            ["graph_nodes.repository_id", "graph_nodes.id"],
            name="fk_graph_edges_repository_source_node",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["repository_id", "target_node_id"],
            ["graph_nodes.repository_id", "graph_nodes.id"],
            name="fk_graph_edges_repository_target_node",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "repository_id",
            "source_node_id",
            "target_node_id",
            "edge_type",
            name="uq_graph_edges_identity",
        ),
        sa.CheckConstraint(
            "source_node_id <> target_node_id",
            name="ck_graph_edges_no_self_loop",
        ),
        sa.CheckConstraint(
            "edge_type IN ('CONTAINS', 'DEFINES', 'IMPORTS', 'HAS_CHUNK')",
            name="ck_graph_edges_edge_type",
        ),
    )

    # The unique edge constraint supports outgoing-edge lookups.
    # This index supports incoming-edge lookups.
    op.create_index(
        "ix_graph_edges_repository_target",
        "graph_edges",
        ["repository_id", "target_node_id"],
    )


def downgrade() -> None:
    # Drop graph tables first because they reference existing tables.
    op.drop_index(
        "ix_graph_edges_repository_target",
        table_name="graph_edges",
    )
    op.drop_table("graph_edges")

    op.drop_index(
        "ix_graph_nodes_repository_type",
        table_name="graph_nodes",
    )
    op.drop_index(
        "uq_graph_nodes_repository_root",
        table_name="graph_nodes",
    )
    op.drop_table("graph_nodes")

    # Remove only the composite constraints introduced by this migration.
    op.drop_constraint(
        "uq_chunks_repository_file_id_id",
        "chunks",
        type_="unique",
    )
    op.drop_constraint(
        "uq_repository_symbols_repository_file_id_id",
        "repository_symbols",
        type_="unique",
    )
    op.drop_constraint(
        "uq_repository_files_repository_id_id",
        "repository_files",
        type_="unique",
    )