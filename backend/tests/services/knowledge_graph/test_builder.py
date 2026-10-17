from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.chunk import Chunk, ChunkType
from app.models.graph_edge import GraphEdge, GraphEdgeType
from app.models.graph_node import GraphNode, GraphNodeType
from app.models.repository import Repository, RepositoryStatus
from app.models.repository_file import (
    FileCategory,
    FileRole,
    LanguageSupportTier,
    RepositoryFile,
)
from app.models.repository_symbol import RepositorySymbol
from app.models.user import User
from app.services.knowledge_graph import knowledge_graph_builder


@pytest.fixture
def graph_dataset(db: Session):
    """Create synthetic repository records and clean them up after each test."""
    unique_id = uuid.uuid4().hex

    user = User(
        username=f"kg_test_{unique_id}",
        email=f"kg_test_{unique_id}@example.com",
        hashed_password="test-only-password",
        is_active=True,
    )
    db.add(user)
    db.flush()

    repository = Repository(
        owner_id=user.id,
        name=f"kg-test-{unique_id}",
        github_url=f"https://github.com/kg-tests/{unique_id}",
        clone_path=f"/tmp/kg-test-{unique_id}",
        default_branch="main",
        status=RepositoryStatus.INDEXED,
        primary_language="Python",
        primary_framework=None,
        total_files=2,
        supported_files=2,
        skipped_files=0,
        repository_size=200,
    )

    other_repository = Repository(
        owner_id=user.id,
        name=f"kg-other-{unique_id}",
        github_url=f"https://github.com/kg-tests/other-{unique_id}",
        clone_path=f"/tmp/kg-other-{unique_id}",
        default_branch="main",
        status=RepositoryStatus.INDEXED,
        primary_language="Python",
        primary_framework=None,
        total_files=1,
        supported_files=1,
        skipped_files=0,
        repository_size=100,
    )

    db.add_all([repository, other_repository])
    db.flush()

    source_file = RepositoryFile(
        repository_id=repository.id,
        path=f"/tmp/kg-test-{unique_id}/backend/services/auth.py",
        relative_path="backend/services/auth.py",
        filename="auth.py",
        extension=".py",
        language="python",
        category=FileCategory.SOURCE,
        role=FileRole.SOURCE,
        support_tier=LanguageSupportTier.TIER_1,
        size=100,
        sha256_hash=None,
        is_binary=False,
    )

    target_file = RepositoryFile(
        repository_id=repository.id,
        path=f"/tmp/kg-test-{unique_id}/backend/models/target.py",
        relative_path="backend/models/target.py",
        filename="target.py",
        extension=".py",
        language="python",
        category=FileCategory.SOURCE,
        role=FileRole.SOURCE,
        support_tier=LanguageSupportTier.TIER_1,
        size=100,
        sha256_hash=None,
        is_binary=False,
    )

    other_file = RepositoryFile(
        repository_id=other_repository.id,
        path=f"/tmp/kg-other-{unique_id}/other.py",
        relative_path="other.py",
        filename="other.py",
        extension=".py",
        language="python",
        category=FileCategory.SOURCE,
        role=FileRole.SOURCE,
        support_tier=LanguageSupportTier.TIER_1,
        size=100,
        sha256_hash=None,
        is_binary=False,
    )

    db.add_all([source_file, target_file, other_file])
    db.flush()

    import_symbol = RepositorySymbol(
        repository_id=repository.id,
        file_id=source_file.id,
        symbol_type="import",
        name="Target",
        qualified_name="backend.models.target.Target",
        location={"start_line": 1, "end_line": 1},
        symbol_metadata={
            "module": "backend.models.target",
            "symbol": "Target",
            "alias": None,
        },
    )

    function_symbol = RepositorySymbol(
        repository_id=repository.id,
        file_id=source_file.id,
        symbol_type="function",
        name="authenticate",
        qualified_name="backend.services.auth.authenticate",
        location={"start_line": 3, "end_line": 5},
        symbol_metadata={},
    )

    db.add_all([import_symbol, function_symbol])
    db.flush()

    source_chunk = Chunk(
        repository_id=repository.id,
        file_id=source_file.id,
        chunk_index=0,
        chunk_type=ChunkType.FUNCTION,
        content="def authenticate():\n    return Target()",
        start_line=1,
        end_line=5,
        token_count=12,
        symbol_name="authenticate",
        qualified_name="backend.services.auth.authenticate",
        parent_symbol=None,
        metadata_={"language": "python"},
    )

    target_chunk = Chunk(
        repository_id=repository.id,
        file_id=target_file.id,
        chunk_index=0,
        chunk_type=ChunkType.CLASS,
        content="class Target:\n    pass",
        start_line=1,
        end_line=2,
        token_count=8,
        symbol_name="Target",
        qualified_name="backend.models.target.Target",
        parent_symbol=None,
        metadata_={"language": "python"},
    )

    db.add_all([source_chunk, target_chunk])
    db.flush()

    ids = {
        "user_id": user.id,
        "repository_id": repository.id,
        "other_repository_id": other_repository.id,
        "source_file_id": source_file.id,
        "target_file_id": target_file.id,
        "other_file_id": other_file.id,
    }

    # Commit the fixture before invoking the builder, which commits internally.
    db.commit()

    try:
        yield ids
    finally:
        # The builder commits, so rollback alone cannot clean up its writes.
        db.rollback()

        repository_ids = [
            ids["repository_id"],
            ids["other_repository_id"],
        ]

        db.execute(
            delete(GraphEdge).where(
                GraphEdge.repository_id.in_(repository_ids)
            )
        )
        db.execute(
            delete(GraphNode).where(
                GraphNode.repository_id.in_(repository_ids)
            )
        )
        db.execute(
            delete(Chunk).where(
                Chunk.repository_id.in_(repository_ids)
            )
        )
        db.execute(
            delete(RepositorySymbol).where(
                RepositorySymbol.repository_id.in_(repository_ids)
            )
        )
        db.execute(
            delete(RepositoryFile).where(
                RepositoryFile.repository_id.in_(repository_ids)
            )
        )
        db.execute(
            delete(Repository).where(
                Repository.id.in_(repository_ids)
            )
        )
        db.execute(
            delete(User).where(User.id == ids["user_id"])
        )
        db.commit()


def test_build_creates_expected_nodes_and_edges(db, graph_dataset):
    repository_id = graph_dataset["repository_id"]

    result = knowledge_graph_builder.build(db, repository_id)

    assert result == {
        "nodes": 7,
        "edges": 7,
        "files": 2,
        "symbols": 2,
        "chunks": 2,
    }

    node_counts = dict(
        db.execute(
            select(GraphNode.node_type, func.count(GraphNode.id))
            .where(GraphNode.repository_id == repository_id)
            .group_by(GraphNode.node_type)
        ).all()
    )

    assert node_counts == {
        GraphNodeType.REPOSITORY.value: 1,
        GraphNodeType.FILE.value: 2,
        GraphNodeType.SYMBOL.value: 2,
        GraphNodeType.CHUNK.value: 2,
    }

    edge_counts = dict(
        db.execute(
            select(GraphEdge.edge_type, func.count(GraphEdge.id))
            .where(GraphEdge.repository_id == repository_id)
            .group_by(GraphEdge.edge_type)
        ).all()
    )

    assert edge_counts == {
        GraphEdgeType.CONTAINS.value: 2,
        GraphEdgeType.DEFINES.value: 2,
        GraphEdgeType.HAS_CHUNK.value: 2,
        GraphEdgeType.IMPORTS.value: 1,
    }


def test_build_is_idempotent(db, graph_dataset):
    repository_id = graph_dataset["repository_id"]

    first_result = knowledge_graph_builder.build(db, repository_id)

    first_node_ids = dict(
        db.execute(
            select(GraphNode.entity_key, GraphNode.id).where(
                GraphNode.repository_id == repository_id
            )
        ).all()
    )

    first_edge_count = db.scalar(
        select(func.count(GraphEdge.id)).where(
            GraphEdge.repository_id == repository_id
        )
    )

    second_result = knowledge_graph_builder.build(db, repository_id)

    second_node_ids = dict(
        db.execute(
            select(GraphNode.entity_key, GraphNode.id).where(
                GraphNode.repository_id == repository_id
            )
        ).all()
    )

    second_edge_count = db.scalar(
        select(func.count(GraphEdge.id)).where(
            GraphEdge.repository_id == repository_id
        )
    )

    assert second_result == first_result
    assert second_node_ids == first_node_ids
    assert second_edge_count == first_edge_count


def test_build_resolves_import_to_indexed_file(db, graph_dataset):
    repository_id = graph_dataset["repository_id"]

    knowledge_graph_builder.build(db, repository_id)

    import_edges = list(
        db.scalars(
            select(GraphEdge).where(
                GraphEdge.repository_id == repository_id,
                GraphEdge.edge_type == GraphEdgeType.IMPORTS.value,
            )
        ).all()
    )

    assert len(import_edges) == 1

    edge = import_edges[0]
    source_node = db.get(GraphNode, edge.source_node_id)
    target_node = db.get(GraphNode, edge.target_node_id)

    assert source_node is not None
    assert target_node is not None

    assert source_node.entity_key == (
        "file:backend/services/auth.py"
    )
    assert target_node.entity_key == (
        "file:backend/models/target.py"
    )


def test_build_removes_stale_file_node_after_rename(db, graph_dataset):
    repository_id = graph_dataset["repository_id"]

    knowledge_graph_builder.build(db, repository_id)

    old_key = "file:backend/services/auth.py"
    new_key = "file:backend/services/auth_v2.py"

    old_node = db.scalar(
        select(GraphNode).where(
            GraphNode.repository_id == repository_id,
            GraphNode.entity_key == old_key,
        )
    )
    assert old_node is not None

    source_file = db.get(
        RepositoryFile,
        graph_dataset["source_file_id"],
    )
    assert source_file is not None

    source_file.relative_path = "backend/services/auth_v2.py"
    source_file.filename = "auth_v2.py"
    source_file.path = (
        f"/tmp/kg-test-{graph_dataset['repository_id']}"
        "/backend/services/auth_v2.py"
    )
    db.commit()

    knowledge_graph_builder.build(db, repository_id)

    remaining_keys = set(
        db.scalars(
            select(GraphNode.entity_key).where(
                GraphNode.repository_id == repository_id
            )
        ).all()
    )

    assert old_key not in remaining_keys
    assert new_key in remaining_keys


def test_build_is_repository_scoped(db, graph_dataset):
    repository_id = graph_dataset["repository_id"]
    other_repository_id = graph_dataset["other_repository_id"]

    knowledge_graph_builder.build(db, repository_id)

    other_nodes = db.scalar(
        select(func.count(GraphNode.id)).where(
            GraphNode.repository_id == other_repository_id
        )
    )
    assert other_nodes == 0

    # Every edge for this build must point to nodes from the same repository.
    edge_endpoints = db.execute(
        select(
            GraphEdge.repository_id,
            GraphNode.repository_id,
        )
        .join(
            GraphNode,
            GraphNode.id == GraphEdge.source_node_id,
        )
        .where(GraphEdge.repository_id == repository_id)
    ).all()

    assert edge_endpoints
    assert all(
        edge_repository_id == node_repository_id
        for edge_repository_id, node_repository_id in edge_endpoints
    )

    target_endpoints = db.execute(
        select(
            GraphEdge.repository_id,
            GraphNode.repository_id,
        )
        .join(
            GraphNode,
            GraphNode.id == GraphEdge.target_node_id,
        )
        .where(GraphEdge.repository_id == repository_id)
    ).all()

    assert all(
        edge_repository_id == node_repository_id
        for edge_repository_id, node_repository_id in target_endpoints
    )


def test_build_rejects_missing_repository(db):
    missing_repository_id = -987654321

    with pytest.raises(
        ValueError,
        match=f"Repository {missing_repository_id} does not exist",
    ):
        knowledge_graph_builder.build(db, missing_repository_id)