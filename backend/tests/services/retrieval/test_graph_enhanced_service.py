
from unittest.mock import Mock

import pytest

from app.schemas.retrieval import (
    RetrievalRequest,
    RetrievalResponse,
    RetrievedChunk,
)
from app.services.retrieval.graph_enhanced_service import (
    GraphEnhancedRetrievalService,
)
from app.services.retrieval.graph_retriever import GraphRetrievalResult
from app.services.retrieval.result import RetrievalResult


@pytest.fixture
def retrieval_request() -> RetrievalRequest:
    return RetrievalRequest(
        repository_id=49,
        query="How does authentication work?",
        top_k=3,
    )


def make_chunk(
    chunk_id: int,
    score: float,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        content=f"Content for chunk {chunk_id}",
        file_path=f"app/module_{chunk_id}.py",
        similarity_score=score,
        retrieval_score=score,
    )


def test_orchestrates_baseline_graph_fusion_and_hydration(
    retrieval_request: RetrievalRequest,
) -> None:
    baseline = Mock()
    baseline.retrieve.return_value = RetrievalResponse(
        repository_id=49,
        query=retrieval_request.query,
        results=[
            make_chunk(10, 0.9),
            make_chunk(20, 0.4),
        ],
    )

    graph = Mock()
    graph.retrieve.return_value = [
        GraphRetrievalResult(
            chunk_id=30,
            file_id=3,
            hop_count=0,
            score=1.0,
        ),
    ]

    fusion = Mock()
    fusion.fuse.return_value = [
        RetrievalResult(chunk_id=10, score=0.75),
        RetrievalResult(chunk_id=30, score=0.25),
    ]

    hydrator = Mock()
    hydrator.hydrate.return_value = [
        make_chunk(10, 0.75),
        make_chunk(30, 0.25),
    ]

    service = GraphEnhancedRetrievalService(
        Mock(),
        baseline_service=baseline,
        graph_retriever=graph,
        graph_fusion=fusion,
        hydrator=hydrator,
    )

    response = service.retrieve(retrieval_request)

    baseline.retrieve.assert_called_once_with(retrieval_request)
    graph.retrieve.assert_called_once_with(
        repository_id=49,
        seed_chunk_ids=[10, 20],
        max_hops=1,
        top_k=100,
    )
    fusion.fuse.assert_called_once()
    hydrator.hydrate.assert_called_once_with(
        fusion.fuse.return_value
    )

    assert response.repository_id == 49
    assert response.query == retrieval_request.query
    assert [result.chunk_id for result in response.results] == [10, 30]


def test_empty_baseline_skips_graph_expansion(
    retrieval_request: RetrievalRequest,
) -> None:
    baseline = Mock()
    baseline.retrieve.return_value = RetrievalResponse(
        repository_id=49,
        query=retrieval_request.query,
        results=[],
    )

    graph = Mock()
    fusion = Mock()
    hydrator = Mock()

    service = GraphEnhancedRetrievalService(
        Mock(),
        baseline_service=baseline,
        graph_retriever=graph,
        graph_fusion=fusion,
        hydrator=hydrator,
    )

    response = service.retrieve(retrieval_request)

    assert response.results == []
    graph.retrieve.assert_not_called()
    fusion.fuse.assert_not_called()
    hydrator.hydrate.assert_not_called()


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"max_hops": -1}, "max_hops"),
        ({"graph_candidate_multiplier": 0}, "graph_candidate_multiplier"),
        ({"max_graph_candidates": 0}, "max_graph_candidates"),
    ],
)
def test_invalid_configuration_is_rejected(
    kwargs: dict,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        GraphEnhancedRetrievalService(Mock(), **kwargs)
