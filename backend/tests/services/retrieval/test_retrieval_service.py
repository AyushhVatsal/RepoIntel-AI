from unittest.mock import Mock

import pytest

from app.schemas.retrieval import (
    RetrievalRequest,
    RetrievalResponse,
    RetrievedChunk,
)
from app.services.retrieval.result import RetrievalResult
from app.services.retrieval.retrieval_service import (
    RetrievalService,
    _is_batching_query,
    _is_configuration_query,
    _is_lexical_navigation_query,
    warmup_recent_retrieval_indexes,
    warmup_retrieval_models,
)


def make_service(
    monkeypatch: pytest.MonkeyPatch,
    *,
    threshold: float | None,
) -> tuple[RetrievalService, list[RetrievalResult]]:
    """Build a service with mocked retrieval dependencies."""
    service = RetrievalService.__new__(RetrievalService)
    service._db = Mock()
    service._conditional_rerank_threshold = threshold
    service._candidate_pool_k = 10
    service._rerank_candidate_pool_k = 5

    service._embedding_service = Mock()
    service._embedding_service.embed_query.return_value = [0.1] * 384
    service._embedding_service.model_name = "test-model"

    service._hybrid_retriever = Mock()

    rrf_results = [
        RetrievalResult(chunk_id=1, score=0.020),
        RetrievalResult(chunk_id=2, score=0.0195),
    ]
    service._hybrid_retriever.search.return_value = rrf_results

    service._cross_encoder = Mock()
    service._cross_encoder.rerank.return_value = [
        RetrievalResult(chunk_id=2, score=0.90),
        RetrievalResult(chunk_id=1, score=0.20),
    ]

    service._weighted_fusion = Mock()
    service._weighted_fusion.fuse.return_value = [
        RetrievalResult(chunk_id=2, score=0.90)
    ]
    service._configuration_fusion = Mock()
    service._configuration_fusion.fuse.return_value = [
        RetrievalResult(chunk_id=2, score=0.90)
    ]

    service._hydrator = Mock()

    def hydrate(results: list[RetrievalResult]) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                chunk_id=result.chunk_id,
                content=f"code for chunk {result.chunk_id}",
                file_path=f"src/chunk_{result.chunk_id}.py",
                similarity_score=0.8,
                retrieval_score=result.score,
            )
            for result in results
        ]

    service._hydrator.hydrate.side_effect = hydrate

    return service, rrf_results


def test_configuration_question_is_targeted() -> None:
    assert _is_configuration_query(
        "Where are the embedding model and vector dimensions configured?"
    )


def test_warmup_retrieval_models_initializes_shared_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    embedding_provider = Mock()
    embedding_provider.embed.return_value = [[0.1] * 384]
    reranker = Mock()
    monkeypatch.setattr(
        "app.services.retrieval.retrieval_service.get_local_embedding_provider",
        lambda model_name: embedding_provider,
    )
    monkeypatch.setattr(
        "app.services.retrieval.retrieval_service.get_cross_encoder_reranker",
        lambda: reranker,
    )

    query_vector = warmup_retrieval_models()

    assert query_vector == [0.1] * 384
    embedding_provider.embed.assert_called_once_with(
        [
            "How does repository indexing batch code chunks before "
            "generating and storing retrieval embeddings?"
        ],
    )
    reranker.warmup.assert_called_once_with()


def test_warmup_recent_retrieval_indexes_primes_selected_repositories(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = Mock()
    db.__enter__ = Mock(return_value=db)
    db.__exit__ = Mock(return_value=None)
    db.scalars.return_value.all.return_value = [1752, 1753]
    manager = Mock()
    lexical_retriever = Mock()
    vector_retriever = Mock()
    monkeypatch.setattr("app.db.database.SessionLocal", lambda: db)
    monkeypatch.setattr(
        "app.services.retrieval.retrieval_service.get_bm25_index_manager",
        lambda: manager,
    )
    monkeypatch.setattr(
        "app.services.retrieval.retrieval_service.LexicalRetriever",
        lambda _db, _manager: lexical_retriever,
    )
    monkeypatch.setattr(
        "app.services.retrieval.vector_retriever.VectorRetriever",
        lambda _db: vector_retriever,
    )

    repository_ids = warmup_recent_retrieval_indexes([0.1] * 384)

    assert repository_ids == [1752, 1753]
    assert [call.kwargs for call in lexical_retriever.search.call_args_list] == [
        {
            "repository_id": 1752,
            "query": "repository retrieval warmup",
            "top_k": 1,
        },
        {
            "repository_id": 1753,
            "query": "repository retrieval warmup",
            "top_k": 1,
        },
    ]
    assert [call.kwargs for call in vector_retriever.search.call_args_list] == [
        {
            "query_vector": [0.1] * 384,
            "repository_id": 1752,
            "model": "BAAI/bge-small-en-v1.5",
            "top_k": 5,
        },
        {
            "query_vector": [0.1] * 384,
            "repository_id": 1753,
            "model": "BAAI/bge-small-en-v1.5",
            "top_k": 5,
        },
    ]


def test_batching_question_is_targeted_without_being_config_question() -> None:
    query = "How are chunks batched before they are sent to the embedding provider?"

    assert _is_batching_query(query)
    assert not _is_configuration_query(query)


def test_alembic_migration_navigation_query_uses_lexical_ranking() -> None:
    assert _is_lexical_navigation_query(
        "Alembic migration adding the vector similarity index"
    )


def test_retrieval_service_defaults_to_always_rerank(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, rrf_results = make_service(
        monkeypatch,
        threshold=None,
    )

    response = service.retrieve(
        RetrievalRequest(
            repository_id=7,
            query="How does repository indexing work?",
            top_k=1,
        )
    )

    assert isinstance(response, RetrievalResponse)
    assert response.results[0].chunk_id == 2

    service._cross_encoder.rerank.assert_called_once()
    service._weighted_fusion.fuse.assert_called_once_with(
        rrf_results=rrf_results,
        cross_encoder_results=service._cross_encoder.rerank.return_value,
        top_k=5,
    )


def test_retrieval_service_skips_reranking_when_score_gap_is_large(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _rrf_results = make_service(
        monkeypatch,
        threshold=0.001,
    )
    service._hybrid_retriever.search.return_value = [
        RetrievalResult(chunk_id=1, score=0.020),
        RetrievalResult(chunk_id=2, score=0.018),
    ]

    response = service.retrieve(
        RetrievalRequest(
            repository_id=7,
            query="How does repository indexing work?",
            top_k=1,
        )
    )

    assert isinstance(response, RetrievalResponse)
    assert response.results[0].chunk_id == 1

    service._cross_encoder.rerank.assert_not_called()
    service._weighted_fusion.fuse.assert_not_called()
    service._hydrator.hydrate.assert_called_once_with(
        service._hybrid_retriever.search.return_value
    )


def test_retrieval_service_reranks_when_score_gap_is_small(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, rrf_results = make_service(
        monkeypatch,
        threshold=0.001,
    )

    response = service.retrieve(
        RetrievalRequest(
            repository_id=7,
            query="How does repository indexing work?",
            top_k=1,
        )
    )

    assert isinstance(response, RetrievalResponse)
    assert response.results[0].chunk_id == 2

    service._cross_encoder.rerank.assert_called_once()
    service._weighted_fusion.fuse.assert_called_once_with(
        rrf_results=rrf_results,
        cross_encoder_results=service._cross_encoder.rerank.return_value,
        top_k=5,
    )


def test_configuration_query_uses_targeted_candidates_and_cross_encoder_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _rrf_results = make_service(monkeypatch, threshold=0.001)

    service.retrieve(
        RetrievalRequest(
            repository_id=7,
            query="Where are embedding dimensions configured?",
            top_k=1,
        )
    )

    assert service._hybrid_retriever.search.call_args.kwargs["candidate_k"] == 10
    service._configuration_fusion.fuse.assert_called_once()
    service._weighted_fusion.fuse.assert_not_called()


def test_decisive_batching_query_keeps_rrf_order_without_reranking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _rrf_results = make_service(monkeypatch, threshold=0.001)
    service._hybrid_retriever.search.return_value = [
        RetrievalResult(chunk_id=1, score=0.020),
        RetrievalResult(chunk_id=2, score=0.018),
    ]

    response = service.retrieve(
        RetrievalRequest(
            repository_id=7,
            query="How are chunks batched before they are sent to the provider?",
            top_k=1,
        )
    )

    assert not response.reranking_applied
    assert response.reranking_skip_reason == "rrf_margin_exceeded"
    assert service._hybrid_retriever.search.call_args.kwargs["candidate_k"] == 10
    service._cross_encoder.rerank.assert_not_called()


def test_configuration_reranking_is_capped_at_candidate_pool_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _rrf_results = make_service(monkeypatch, threshold=0.001)
    service._candidate_pool_k = 5
    service._hybrid_retriever.search.return_value = [
        RetrievalResult(chunk_id=chunk_id, score=0.020 - chunk_id / 10000)
        for chunk_id in range(1, 11)
    ]
    service._cross_encoder.rerank.return_value = [
        RetrievalResult(chunk_id=chunk_id, score=1.0 - chunk_id / 100)
        for chunk_id in range(1, 6)
    ]
    service.retrieve(
        RetrievalRequest(
            repository_id=7,
            query="Where are embedding dimensions configured?",
            top_k=5,
        )
    )

    rerank_call = service._cross_encoder.rerank.call_args.kwargs
    assert len(rerank_call["results"]) == 5
    assert rerank_call["top_k"] == 5


def test_reranking_pool_prefers_distinct_files_from_wider_candidate_pool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _rrf_results = make_service(monkeypatch, threshold=None)
    service._hybrid_retriever.search.return_value = [
        RetrievalResult(chunk_id=chunk_id, score=0.03 - chunk_id / 10000)
        for chunk_id in range(1, 11)
    ]
    service._hydrator.hydrate.side_effect = lambda results: [
        RetrievedChunk(
            chunk_id=result.chunk_id,
            content=f"content {result.chunk_id}",
            file_path=(
                "src/repeated.py"
                if result.chunk_id in (1, 2, 3)
                else f"src/file_{result.chunk_id}.py"
            ),
        )
        for result in results
    ]

    service.retrieve(
        RetrievalRequest(
            repository_id=7,
            query="How does indexing work?",
            top_k=5,
        )
    )

    rerank_call = service._cross_encoder.rerank.call_args.kwargs
    assert [result.chunk_id for result in rerank_call["results"]] == [1, 4, 5, 6, 7]
    assert set(rerank_call["documents"]) == {1, 4, 5, 6, 7}


def test_configuration_response_respects_requested_top_k(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _rrf_results = make_service(monkeypatch, threshold=0.001)
    service._candidate_pool_k = 5
    service._hybrid_retriever.search.return_value = [
        RetrievalResult(chunk_id=chunk_id, score=0.02 - chunk_id / 10000)
        for chunk_id in range(1, 11)
    ]
    service._configuration_fusion.fuse.return_value = [
        RetrievalResult(chunk_id=chunk_id, score=1.0 - chunk_id / 100)
        for chunk_id in range(1, 11)
    ]
    response = service.retrieve(
        RetrievalRequest(
            repository_id=7,
            query="Where are embedding dimensions configured?",
            top_k=1,
        )
    )

    assert len(response.results) == 1
    service._hydrator.hydrate.assert_called_once_with(
        service._hybrid_retriever.search.return_value
    )


def test_file_diversity_promotes_other_files_before_repeating_a_file() -> None:
    chunks = [
        RetrievedChunk(chunk_id=1, content="a1", file_path="src/a.py"),
        RetrievedChunk(chunk_id=2, content="a2", file_path="src/a.py"),
        RetrievedChunk(chunk_id=3, content="b1", file_path="src/b.py"),
        RetrievedChunk(chunk_id=4, content="c1", file_path="src/c.py"),
    ]

    selected = RetrievalService._limit_file_repetition(chunks, top_k=3)

    assert [chunk.chunk_id for chunk in selected] == [1, 3, 4]


def test_file_diversity_backfills_when_candidate_files_are_insufficient() -> None:
    chunks = [
        RetrievedChunk(chunk_id=1, content="a1", file_path="src/a.py"),
        RetrievedChunk(chunk_id=2, content="a2", file_path="src/a.py"),
    ]

    selected = RetrievalService._limit_file_repetition(chunks, top_k=2)

    assert [chunk.chunk_id for chunk in selected] == [1, 2]


def test_file_definition_query_preserves_hybrid_order_without_reranking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _rrf_results = make_service(monkeypatch, threshold=0.001)

    response = service.retrieve(
        RetrievalRequest(
            repository_id=7,
            query="Which file defines LoginResponse?",
            top_k=1,
        )
    )

    assert not response.reranking_applied
    assert response.reranking_skip_reason == "definition_lookup_uses_hybrid_order"
    service._cross_encoder.rerank.assert_not_called()


def test_migration_navigation_query_skips_cross_encoder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _rrf_results = make_service(monkeypatch, threshold=None)

    response = service.retrieve(
        RetrievalRequest(
            repository_id=7,
            query="Alembic migration adding the vector similarity index",
            top_k=5,
        )
    )

    assert response.reranking_skip_reason == "lexical_navigation_uses_hybrid_order"
    service._cross_encoder.rerank.assert_not_called()
    assert service._hybrid_retriever.search.call_args.kwargs["candidate_k"] == 5
