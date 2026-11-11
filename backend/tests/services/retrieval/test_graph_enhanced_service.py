
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
        top_k=6,
        filters=service._graph_filters(None),
        max_per_file=2,
        query_vector=None,
        embedding_model=None,
        include_seed_chunk_ids=[],
        imported_symbol=None,
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


def test_graph_candidates_below_baseline_dense_floor_are_not_fused(
    retrieval_request: RetrievalRequest,
) -> None:
    baseline = Mock()
    baseline.retrieve.return_value = RetrievalResponse(
        repository_id=49,
        query=retrieval_request.query,
        results=[make_chunk(10, 0.8), make_chunk(20, 0.6)],
    )
    graph = Mock()
    graph.retrieve.return_value = [
        GraphRetrievalResult(
            chunk_id=30,
            file_id=3,
            hop_count=1,
            score=0.5,
            query_score=0.59,
        ),
        GraphRetrievalResult(
            chunk_id=40,
            file_id=4,
            hop_count=1,
            score=0.5,
            query_score=0.61,
        ),
    ]
    fusion = Mock()
    fusion.fuse.return_value = [RetrievalResult(chunk_id=20, score=1.0)]
    hydrator = Mock()
    hydrator.hydrate.return_value = [make_chunk(20, 1.0)]

    service = GraphEnhancedRetrievalService(
        Mock(),
        baseline_service=baseline,
        graph_retriever=graph,
        graph_fusion=fusion,
        hydrator=hydrator,
    )

    service.retrieve(retrieval_request)

    fused_graph_results = fusion.fuse.call_args.kwargs["graph_results"]
    assert [candidate.chunk_id for candidate in fused_graph_results] == [40]


def test_graph_only_diagnostic_does_not_apply_hybrid_relevance_floor(
    retrieval_request: RetrievalRequest,
) -> None:
    baseline = Mock()
    baseline.retrieve.return_value = RetrievalResponse(
        repository_id=49,
        query=retrieval_request.query,
        results=[make_chunk(10, 0.8), make_chunk(20, 0.6)],
    )
    graph = Mock()
    graph.retrieve.return_value = [
        GraphRetrievalResult(30, 3, 1, 0.5, query_score=0.59),
        GraphRetrievalResult(40, 4, 1, 0.5, query_score=0.61),
    ]
    fusion = Mock()
    fusion.fuse.return_value = [RetrievalResult(chunk_id=30, score=1.0)]
    hydrator = Mock()
    hydrator.hydrate.return_value = [make_chunk(30, 1.0)]
    service = GraphEnhancedRetrievalService(
        Mock(),
        baseline_service=baseline,
        graph_retriever=graph,
        graph_fusion=fusion,
        hydrator=hydrator,
        graph_only=True,
    )

    service.retrieve(retrieval_request)

    fused_graph_results = fusion.fuse.call_args.kwargs["graph_results"]
    assert {candidate.chunk_id for candidate in fused_graph_results} == {30, 40}


def test_independent_graph_mode_uses_lexical_seeds_without_hybrid_ids(
    retrieval_request: RetrievalRequest,
) -> None:
    baseline = Mock()
    baseline.retrieve.return_value = RetrievalResponse(
        repository_id=49,
        query=retrieval_request.query,
        results=[make_chunk(10, 0.8)],
    )
    seeder = Mock()
    seeder.retrieve.return_value = [30, 40]
    seeder.last_latency_ms = 1.5
    seeder.last_candidate_count = 12
    graph = Mock()
    graph.retrieve.return_value = [
        GraphRetrievalResult(30, 3, 0, 1.0, query_score=0.7),
        GraphRetrievalResult(50, 5, 1, 0.5, query_score=0.6),
    ]
    fusion = Mock()
    fusion.fuse.return_value = [RetrievalResult(chunk_id=30, score=1.0)]
    hydrator = Mock()
    hydrator.hydrate.return_value = [make_chunk(30, 1.0)]
    service = GraphEnhancedRetrievalService(
        Mock(),
        baseline_service=baseline,
        graph_retriever=graph,
        graph_seeder=seeder,
        graph_fusion=fusion,
        hydrator=hydrator,
        seed_strategy="independent",
        seed_budget=2,
        graph_only=True,
    )

    response = service.retrieve(retrieval_request)

    assert service.last_independent_seed_ids == [30, 40]
    assert service.last_seed_chunk_ids == [30, 40]
    assert response.ranking_policy == "graph_only_independent_seed_v1"
    graph.retrieve.assert_called_once_with(
        repository_id=49,
        seed_chunk_ids=[30, 40],
        max_hops=1,
        top_k=6,
        filters=service._graph_filters(None),
        max_per_file=2,
        query_vector=None,
        embedding_model=None,
        include_seed_chunk_ids=[30, 40],
        imported_symbol=None,
    )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"max_hops": -1}, "max_hops"),
        ({"max_hops": 4}, "max_hops"),
        ({"graph_candidate_multiplier": 0}, "graph_candidate_multiplier"),
        ({"graph_weight": 1.1}, "graph_weight"),
        ({"max_graph_candidates": 0}, "max_graph_candidates"),
        ({"max_graph_candidates": 201}, "max_graph_candidates"),
        ({"seed_strategy": "unknown"}, "seed strategy"),
        ({"seed_budget": 0}, "seed_budget"),
    ],
)
def test_invalid_configuration_is_rejected(
    kwargs: dict,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        GraphEnhancedRetrievalService(Mock(), **kwargs)


@pytest.mark.parametrize(
    ("strategy", "expected"),
    [
        ("post_rerank", [20, 30, 10]),
        ("pre_rerank", [10, 20, 40]),
        ("dual_source", [20, 10, 30]),
        ("independent", [50, 60, 70]),
        ("combined", [20, 50, 30]),
    ],
)
def test_seed_strategy_is_deduplicated_and_respects_fixed_budget(
    strategy: str,
    expected: list[int],
) -> None:
    service = GraphEnhancedRetrievalService(
        Mock(),
        baseline_service=Mock(),
        seed_strategy=strategy,
        seed_budget=3,
    )

    assert service._select_seed_ids(
        pre_rerank_seed_ids=[10, 20, 40],
        post_rerank_seed_ids=[20, 30, 10],
        independent_seed_ids=[50, 60, 70],
        budget=3,
    ) == expected


def test_graph_filters_include_request_filters_and_exclude_test_roles() -> None:
    from app.models.repository_file import FileRole
    from app.services.retrieval.filters import RetrievalFilters

    filters = GraphEnhancedRetrievalService._graph_filters(
        RetrievalFilters(language="python", role=FileRole.SOURCE)
    )

    assert filters.language == "python"
    assert filters.role == FileRole.SOURCE
    assert filters.exclude_roles == [FileRole.TEST, FileRole.FIXTURE]


def test_graph_service_uses_production_retrieval_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.retrieval import graph_enhanced_service

    db = Mock()
    production_service = Mock()
    factory = Mock(return_value=production_service)
    monkeypatch.setattr(
        graph_enhanced_service,
        "create_production_retrieval_service",
        factory,
    )

    service = GraphEnhancedRetrievalService(db)

    factory.assert_called_once_with(db)
    assert service._baseline_service is production_service
