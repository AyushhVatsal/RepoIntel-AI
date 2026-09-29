from app.services.retrieval.lexical.index import LexicalDocument
from app.services.retrieval.lexical.manager import BM25IndexManager

def test_get_returns_none_for_uncached_repository():
    manager = BM25IndexManager()

    assert manager.get(1) is None


def test_build_caches_index():
    manager = BM25IndexManager()

    documents = [
        LexicalDocument(
            chunk_id=1,
            content="authenticate_user",
        )
    ]

    index = manager.build(1, documents)

    assert manager.get(1) is index
    assert index.size == 1


def test_cached_index_is_reused():
    manager = BM25IndexManager()

    documents = [
        LexicalDocument(
            chunk_id=1,
            content="authenticate_user",
        )
    ]

    first = manager.build(1, documents)
    second = manager.get(1)

    assert second is first


def test_repositories_have_independent_indexes():
    manager = BM25IndexManager()

    first = manager.build(
        1,
        [LexicalDocument(chunk_id=10, content="authenticate_user")],
    )

    second = manager.build(
        2,
        [LexicalDocument(chunk_id=20, content="create_user")],
    )

    assert manager.get(1) is first
    assert manager.get(2) is second
    assert first is not second


def test_invalidate_removes_repository_index():
    manager = BM25IndexManager()

    manager.build(
        1,
        [LexicalDocument(chunk_id=1, content="authenticate_user")],
    )

    manager.invalidate(1)

    assert manager.get(1) is None


def test_clear_removes_all_indexes():
    manager = BM25IndexManager()

    manager.build(
        1,
        [LexicalDocument(chunk_id=1, content="authenticate_user")],
    )

    manager.build(
        2,
        [LexicalDocument(chunk_id=2, content="create_user")],
    )

    manager.clear()

    assert manager.get(1) is None
    assert manager.get(2) is None