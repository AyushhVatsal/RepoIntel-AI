import pytest

from app.services.retrieval.lexical.manager import get_bm25_index_manager


@pytest.fixture(autouse=True)
def isolate_retrieval_index_cache():
    """Keep one evaluation's BM25 snapshot from affecting another's metrics."""
    manager = get_bm25_index_manager()
    manager.clear()
    yield
    manager.clear()
