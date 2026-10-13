from unittest.mock import Mock

from app.schemas.retrieval import RetrievedChunk
from app.services.retrieval.hybrid.retriever import HybridRetriever
from app.services.retrieval.result import RetrievalResult
from app.models.repository_file import FileRole
from app.services.retrieval.filters import RetrievalFilters


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

def test_hybrid_retriever_excludes_both_test_and_fixture_roles():
    vector_retriever = Mock()
    lexical_retriever = Mock()
    fusion = Mock()
    candidate_filter = Mock()

    candidate_filter.exclude_roles.return_value = []
    vector_retriever.search.return_value = []
    lexical_retriever.search.return_value = []
    fusion.fuse.return_value = []

    hybrid = HybridRetriever(
        vector_retriever=vector_retriever,
        lexical_retriever=lexical_retriever,
        fusion=fusion,
        candidate_filter=candidate_filter,
    )

    hybrid.search(
        query_vector=[0.1, 0.2, 0.3],
        repository_id=49,
        model="BAAI/bge-small-en-v1.5",
        query="authenticate user",
        top_k=5,
    )

    passed_filters = lexical_retriever.search.call_args.kwargs["filters"]
    excluded_roles = passed_filters.exclude_roles

    assert FileRole.TEST in excluded_roles
    assert FileRole.FIXTURE in excluded_roles


def test_hybrid_retriever_adds_fixture_when_test_already_excluded():
    vector_retriever = Mock()
    lexical_retriever = Mock()
    fusion = Mock()
    candidate_filter = Mock()

    candidate_filter.exclude_roles.return_value = []
    vector_retriever.search.return_value = []
    lexical_retriever.search.return_value = []
    fusion.fuse.return_value = []

    original_filters = RetrievalFilters(
        exclude_roles=[FileRole.TEST],
    )

    hybrid = HybridRetriever(
        vector_retriever=vector_retriever,
        lexical_retriever=lexical_retriever,
        fusion=fusion,
        candidate_filter=candidate_filter,
    )

    hybrid.search(
        query_vector=[0.1, 0.2, 0.3],
        repository_id=49,
        model="BAAI/bge-small-en-v1.5",
        query="authenticate user",
        top_k=5,
        filters=original_filters,
    )

    passed_filters = lexical_retriever.search.call_args.kwargs["filters"]
    excluded_roles = passed_filters.exclude_roles

    assert FileRole.TEST in excluded_roles
    assert FileRole.FIXTURE in excluded_roles

    # The original filters must remain unchanged.
    assert original_filters.exclude_roles == [FileRole.TEST]

def test_hybrid_retriever_adds_test_when_fixture_already_excluded():
    vector_retriever = Mock()
    lexical_retriever = Mock()
    fusion = Mock()
    candidate_filter = Mock()

    vector_retriever.search.return_value = []
    lexical_retriever.search.return_value = []
    candidate_filter.exclude_roles.return_value = []
    fusion.fuse.return_value = []

    original_filters = RetrievalFilters(
        exclude_roles=[FileRole.FIXTURE],
    )

    hybrid = HybridRetriever(
        vector_retriever=vector_retriever,
        lexical_retriever=lexical_retriever,
        fusion=fusion,
        candidate_filter=candidate_filter,
    )

    hybrid.search(
        query_vector=[0.1, 0.2, 0.3],
        repository_id=49,
        model="BAAI/bge-small-en-v1.5",
        query="authenticate user",
        top_k=5,
        filters=original_filters,
    )

    passed_filters = lexical_retriever.search.call_args.kwargs["filters"]
    excluded_roles = passed_filters.exclude_roles

    assert FileRole.TEST in excluded_roles
    assert FileRole.FIXTURE in excluded_roles
    assert len(excluded_roles) == 2

    # The caller's original filters must remain unchanged.
    assert original_filters.exclude_roles == [FileRole.FIXTURE]