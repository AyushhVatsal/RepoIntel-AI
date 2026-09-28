import pytest

from app.db.database import SessionLocal
from app.services.retrieval.filters import RetrievalFilters
from app.services.retrieval.lexical.retriever import LexicalRetriever
from app.services.retrieval.filters import RetrievalFilters
from app.services.retrieval.lexical.retriever import LexicalRetriever

@pytest.fixture
def db():
    session = SessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()

def test_search_respects_repository_isolation(
    db,
    retrieval_dataset,
):
    retriever = LexicalRetriever(db)

    results = retriever.search(
        repository_id=retrieval_dataset["repository_id"],
        query="authenticate_user",
        top_k=10,
    )

    result_ids = {result.chunk_id for result in results}

    assert retrieval_dataset["other_chunk"].id not in result_ids

    expected_ids = {
        chunk.id
        for chunk in retrieval_dataset["chunks"]
    }

    assert result_ids <= expected_ids


def test_search_respects_language_filter(
    db,
    retrieval_dataset,
):
    retriever = LexicalRetriever(db)

    results = retriever.search(
        repository_id=retrieval_dataset["repository_id"],
        query="authenticate",
        top_k=10,
        filters=RetrievalFilters(
            language="python",
        ),
    )

    result_ids = {result.chunk_id for result in results}

    assert result_ids <= {
        retrieval_dataset["chunks"][0].id,
        retrieval_dataset["chunks"][1].id,
    }

    assert retrieval_dataset["chunks"][2].id not in result_ids


def test_search_respects_file_path_filter(
    db,
    retrieval_dataset,
):
    retriever = LexicalRetriever(db)

    results = retriever.search(
        repository_id=retrieval_dataset["repository_id"],
        query="authenticate_user",
        top_k=10,
        filters=RetrievalFilters(
            file_path="backend/auth/",
        ),
    )

    assert len(results) == 1
    assert results[0].chunk_id == retrieval_dataset["chunks"][0].id


def test_search_respects_chunk_type_filter(
    db,
    retrieval_dataset,
):
    retriever = LexicalRetriever(db)

    results = retriever.search(
        repository_id=retrieval_dataset["repository_id"],
        query="user",
        top_k=10,
        filters=RetrievalFilters(
            chunk_type="function",
        ),
    )

    result_ids = {result.chunk_id for result in results}

    assert retrieval_dataset["chunks"][1].id not in result_ids


def test_search_respects_symbol_name_filter(
    db,
    retrieval_dataset,
):
    retriever = LexicalRetriever(db)

    results = retriever.search(
        repository_id=retrieval_dataset["repository_id"],
        query="authenticate_user",
        top_k=10,
        filters=RetrievalFilters(
            symbol_name="authenticate_user",
        ),
    )

    assert len(results) == 1
    assert results[0].chunk_id == retrieval_dataset["chunks"][0].id


def test_search_combines_filters_with_and_logic(
    db,
    retrieval_dataset,
):
    retriever = LexicalRetriever(db)

    results = retriever.search(
        repository_id=retrieval_dataset["repository_id"],
        query="authenticate_user",
        top_k=10,
        filters=RetrievalFilters(
            language="python",
            chunk_type="function",
            symbol_name="authenticate_user",
        ),
    )

    assert len(results) == 1
    assert results[0].chunk_id == retrieval_dataset["chunks"][0].id


def test_empty_query_returns_empty_results(
    db,
    retrieval_dataset,
):
    retriever = LexicalRetriever(db)

    results = retriever.search(
        repository_id=retrieval_dataset["repository_id"],
        query="",
        top_k=10,
    )

    assert results == []