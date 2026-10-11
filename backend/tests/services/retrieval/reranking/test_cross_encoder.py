from unittest.mock import Mock

from app.services.retrieval.reranking.cross_encoder import (
    CrossEncoderReranker,
)
from app.services.retrieval.result import RetrievalResult


def test_reranker_sorts_by_cross_encoder_score():
    reranker = CrossEncoderReranker.__new__(
        CrossEncoderReranker
    )

    reranker._model = Mock()
    reranker._model.predict.return_value = [
        0.20,
        0.90,
        0.50,
    ]

    results = [
        RetrievalResult(chunk_id=1, score=0.01),
        RetrievalResult(chunk_id=2, score=0.02),
        RetrievalResult(chunk_id=3, score=0.03),
    ]

    documents = {
        1: "irrelevant document",
        2: "highly relevant document",
        3: "somewhat relevant document",
    }

    reranked = reranker.rerank(
        query="How does repository ingestion work?",
        results=results,
        documents=documents,
        top_k=3,
    )

    assert [result.chunk_id for result in reranked] == [
        2,
        3,
        1,
    ]

    assert [result.score for result in reranked] == [
        0.90,
        0.50,
        0.20,
    ]


def test_reranker_ignores_candidates_without_documents():
    reranker = CrossEncoderReranker.__new__(
        CrossEncoderReranker
    )

    reranker._model = Mock()
    reranker._model.predict.return_value = [0.80]

    results = [
        RetrievalResult(chunk_id=1, score=0.01),
        RetrievalResult(chunk_id=2, score=0.02),
    ]

    documents = {
        1: "available document",
    }

    reranked = reranker.rerank(
        query="test query",
        results=results,
        documents=documents,
        top_k=2,
    )

    assert len(reranked) == 1
    assert reranked[0].chunk_id == 1

    reranker._model.predict.assert_called_once_with(
        [
            ("test query", "available document"),
        ]
    )


def test_reranker_returns_empty_for_invalid_input():
    reranker = CrossEncoderReranker.__new__(
        CrossEncoderReranker
    )

    reranker._model = Mock()

    assert reranker.rerank(
        query="test",
        results=[],
        documents={},
        top_k=5,
    ) == []

    assert reranker.rerank(
        query="test",
        results=[
            RetrievalResult(chunk_id=1, score=0.1),
        ],
        documents={1: "document"},
        top_k=0,
    ) == []

    reranker._model.predict.assert_not_called()