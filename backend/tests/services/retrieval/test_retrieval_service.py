
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.schemas.retrieval import (
    RetrievedChunk,
    RetrievalRequest,
    RetrievalResponse,
)
from app.services.retrieval import retrieval_service as service_module
from app.services.retrieval.retrieval_service import RetrievalService
from app.services.retrieval.result import RetrievalResult


def make_service(
    monkeypatch: pytest.MonkeyPatch,
    *,
    threshold: float | None,
) -> tuple[RetrievalService, list[RetrievalResult]]:
    """Build a service with mocked retrieval dependencies."""
    service = RetrievalService.__new__(RetrievalService)
    service._db = Mock()
    service._conditional_rerank_threshold = threshold

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

    monkeypatch.setattr(
        service_module,
        "chunk_crud",
        Mock(
            get_by_ids=Mock(
                return_value=[
                    SimpleNamespace(id=1, content="first document"),
                    SimpleNamespace(id=2, content="second document"),
                ]
            )
        ),
    )

    return service, rrf_results


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
        top_k=1,
    )


def test_retrieval_service_skips_reranking_when_score_gap_is_large(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, rrf_results = make_service(
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
        service._hybrid_retriever.search.return_value[:1]
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
        top_k=1,
    )
