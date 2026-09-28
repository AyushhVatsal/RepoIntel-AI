from app.services.retrieval.lexical.index import (
    BM25Index,
    LexicalDocument,
)


def test_build_index():
    index = BM25Index()

    documents = [
        LexicalDocument(
            chunk_id=1,
            content="def authenticate_user(username, password):",
        ),
        LexicalDocument(
            chunk_id=2,
            content="class UserRepository:",
        ),
    ]

    index.build(documents)

    assert index.size == 2


def test_search_returns_matching_chunk():
    index = BM25Index()

    index.build(
        [
            LexicalDocument(
                chunk_id=1,
                content="def authenticate_user(username, password):",
            ),
            LexicalDocument(
                chunk_id=2,
                content="class UserRepository:",
            ),
        ]
    )

    results = index.search(
        query="authenticate_user",
        top_k=2,
    )

    assert results
    assert results[0].chunk_id == 1


def test_exact_identifier_gets_high_lexical_score():
    index = BM25Index()

    index.build(
        [
            LexicalDocument(
                chunk_id=1,
                content="def authenticate_user(username, password):",
            ),
            LexicalDocument(
                chunk_id=2,
                content="def create_user(username):",
            ),
        ]
    )

    results = index.search(
        query="authenticate_user",
        top_k=2,
    )

    assert results[0].chunk_id == 1
    assert results[0].score > results[1].score


def test_empty_index_returns_empty_results():
    index = BM25Index()

    results = index.search(
        query="authenticate_user",
        top_k=5,
    )

    assert results == []


def test_empty_query_returns_empty_results():
    index = BM25Index()

    index.build(
        [
            LexicalDocument(
                chunk_id=1,
                content="authenticate_user",
            ),
        ]
    )

    results = index.search(
        query="",
        top_k=5,
    )

    assert results == []


def test_top_k_limits_results():
    index = BM25Index()

    index.build(
        [
            LexicalDocument(chunk_id=1, content="user authentication"),
            LexicalDocument(chunk_id=2, content="user authentication"),
            LexicalDocument(chunk_id=3, content="user authentication"),
        ]
    )

    results = index.search(
        query="authentication",
        top_k=2,
    )

    assert len(results) == 2


def test_rebuilding_replaces_previous_index():
    index = BM25Index()

    index.build(
        [
            LexicalDocument(
                chunk_id=1,
                content="authenticate_user",
            ),
        ]
    )

    assert index.size == 1

    index.build(
        [
            LexicalDocument(
                chunk_id=2,
                content="UserRepository",
            ),
            LexicalDocument(
                chunk_id=3,
                content="DatabaseService",
            ),
        ]
    )

    assert index.size == 2

    results = index.search(
        query="authenticate_user",
        top_k=5,
    )

    assert all(result.chunk_id != 1 for result in results)