
"""Opt-in integration tests for GraphRetriever against PostgreSQL.

Run from the backend directory after indexing a repository:

    set REPOINTEL_GRAPH_INTEGRATION=1
    set REPOINTEL_GRAPH_REPOSITORY_ID=49
    uv run pytest tests/services/retrieval/test_graph_retriever_integration.py -v

The integration test is skipped unless explicitly enabled.
It only reads existing graph data.
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import select

from app.db.database import SessionLocal
from app.models.graph_node import GraphNode, GraphNodeType
from app.services.retrieval.graph_retriever import (
    GraphRetrievalResult,
    GraphRetriever,
)


pytestmark = pytest.mark.integration


def _integration_enabled() -> bool:
    return os.getenv("REPOINTEL_GRAPH_INTEGRATION", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


@pytest.fixture
def repository_id() -> int:
    if not _integration_enabled():
        pytest.skip(
            "Set REPOINTEL_GRAPH_INTEGRATION=1 to run PostgreSQL integration tests."
        )

    raw_repository_id = os.getenv("REPOINTEL_GRAPH_REPOSITORY_ID", "49")

    try:
        value = int(raw_repository_id)
    except ValueError as exc:
        pytest.fail(
            "REPOINTEL_GRAPH_REPOSITORY_ID must be a positive integer."
        )
        raise exc

    if value <= 0:
        pytest.fail("REPOINTEL_GRAPH_REPOSITORY_ID must be a positive integer.")

    return value


def test_graph_retriever_against_indexed_repository(repository_id: int) -> None:
    """Verify graph retrieval against real, persisted graph nodes."""

    with SessionLocal() as db:
        # Confirm that the requested repository has persisted CHUNK nodes.
        seed_chunk_id = db.scalar(
            select(GraphNode.chunk_id)
            .where(
                GraphNode.repository_id == repository_id,
                GraphNode.node_type == GraphNodeType.CHUNK.value,
                GraphNode.chunk_id.is_not(None),
            )
            .order_by(GraphNode.chunk_id)
            .limit(1)
        )

        if seed_chunk_id is None:
            pytest.skip(
                f"Repository {repository_id} has no persisted CHUNK graph nodes. "
                "Index the repository and build its knowledge graph first."
            )

        retriever = GraphRetriever(db)

        results = retriever.retrieve(
            repository_id=repository_id,
            seed_chunk_ids=[seed_chunk_id],
            max_hops=1,
            top_k=20,
        )

        # The result contract must hold even when the selected seed has no
        # same-file siblings or import-connected files.
        assert isinstance(results, list)
        assert all(isinstance(item, GraphRetrievalResult) for item in results)

        returned_chunk_ids = [item.chunk_id for item in results]

        # Results must be unique and must not include the seed chunk.
        assert len(returned_chunk_ids) == len(set(returned_chunk_ids))
        assert seed_chunk_id not in returned_chunk_ids

        # Retrieval output must obey the requested result limit.
        assert len(results) <= 20

        # Every result must contain valid, bounded metadata.
        for item in results:
            assert item.chunk_id > 0
            assert item.file_id > 0
            assert 0 <= item.hop_count <= 1
            assert item.score == pytest.approx(1.0 / (item.hop_count + 1))

        # Verify every returned chunk exists in the same repository.
        if returned_chunk_ids:
            persisted_chunk_ids = set(
                db.scalars(
                    select(GraphNode.chunk_id).where(
                        GraphNode.repository_id == repository_id,
                        GraphNode.node_type == GraphNodeType.CHUNK.value,
                        GraphNode.chunk_id.in_(returned_chunk_ids),
                    )
                ).all()
            )

            assert set(returned_chunk_ids) <= persisted_chunk_ids