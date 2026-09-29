from unittest.mock import Mock

from app.schemas.retrieval import RetrievedChunk
from app.services.retrieval.hybrid.retriever import HybridRetriever
from app.services.retrieval.result import RetrievalResult


def test_hybrid_retriever_fuses_dense_and_lexical_results():
    vector_retriever = Mock()
    lexical_retriever = Mock()
    fusion = Mock()

    vector_retriever.search.return_value = [
        RetrievedChunk(
            chunk_id=1,
            content="def authenticate_user():",
            file_path="auth.py",
            similarity_score=0.92,
            retrieval_score=0.92,
        ),
    ]

    lexical_retriever.search.return_value = [
        RetrievalResult(
            chunk_id=2,
            score=4.5,

        ),
    ]

    fusion.fuse.return_value = [
        RetrievalResult(
            chunk_id=2,
            score=0.032,
        ),
        RetrievalResult(
            chunk_id=1,
            score=0.031,
        ),
    ]

    candidate_filter = Mock()

    candidate_filter.exclude_roles.return_value = [
        RetrievalResult(
            chunk_id=1,
            score=0.92,
            dense_score=0.92,
        ),
    ]

    hybrid = HybridRetriever(
        vector_retriever=vector_retriever,
        lexical_retriever=lexical_retriever,
        fusion=fusion,
        candidate_filter=candidate_filter,
    )

    results = hybrid.search(
        query_vector=[0.1, 0.2, 0.3],
        repository_id=49,
        model="BAAI/bge-small-en-v1.5",
        query="authenticate user",
        top_k=5,
    )

    assert results == [
        RetrievalResult(chunk_id=2, score=0.032),
        RetrievalResult(chunk_id=1, score=0.031),
    ]

    fusion.fuse.assert_called_once_with(
        [
            [
                RetrievalResult(
                    chunk_id=1,
                    score=0.92,
                    dense_score=0.92,
                ),
            ],
            [
                RetrievalResult(
                    chunk_id=2,
                    score=4.5,
                ),
            ],
        ],
        top_k=5,
    )

def test_hybrid_retriever_returns_empty_for_non_positive_top_k():
    vector_retriever = Mock()
    lexical_retriever = Mock()
    fusion = Mock()

    candidate_filter = Mock()

    hybrid = HybridRetriever(
        vector_retriever=vector_retriever,
        lexical_retriever=lexical_retriever,
        fusion=fusion,
        candidate_filter=candidate_filter,
    )

    results = hybrid.search(
        query_vector=[0.1, 0.2, 0.3],
        repository_id=49,
        model="BAAI/bge-small-en-v1.5",
        query="authenticate user",
        top_k=0,
    )

    assert results == []

    vector_retriever.search.assert_not_called()
    lexical_retriever.search.assert_not_called()
    fusion.fuse.assert_not_called()