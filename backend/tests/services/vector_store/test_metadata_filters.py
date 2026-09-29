import uuid

import pytest

from app.models.chunk import Chunk, ChunkType
from app.models.embedding import Embedding
from app.models.repository import Repository, RepositoryStatus
from app.models.repository_file import (
    FileCategory,
    LanguageSupportTier,
    RepositoryFile,
    FileRole
)
from app.models.user import User
from app.services.retrieval.filters import RetrievalFilters
from app.services.vector_store.repository import VectorStoreRepository
from app.services.vector_store.service import VectorStoreService


def test_no_filters_preserves_v1_behavior(db, retrieval_dataset):
    repository = VectorStoreRepository(db)

    results = repository.similarity_search(
        query_vector=retrieval_dataset["query_vector"],
        repository_id=retrieval_dataset["repository_id"],
        model="filter-test-model",
        top_k=10,
        filters=None,
    )

    assert len(results) == 3

    result_chunk_ids = {result.chunk.id for result in results}

    expected_ids = {
        chunk.id
        for chunk in retrieval_dataset["chunks"]
    }

    assert result_chunk_ids == expected_ids


def test_language_filter(db, retrieval_dataset):
    repository = VectorStoreRepository(db)

    results = repository.similarity_search(
        query_vector=retrieval_dataset["query_vector"],
        repository_id=retrieval_dataset["repository_id"],
        model="filter-test-model",
        top_k=10,
        filters=RetrievalFilters(language="python"),
    )

    assert len(results) == 2

    assert {
        result.chunk.id
        for result in results
    } == {
        retrieval_dataset["chunks"][0].id,
        retrieval_dataset["chunks"][1].id,
    }


def test_file_path_filter(db, retrieval_dataset):
    repository = VectorStoreRepository(db)

    results = repository.similarity_search(
        query_vector=retrieval_dataset["query_vector"],
        repository_id=retrieval_dataset["repository_id"],
        model="filter-test-model",
        top_k=10,
        filters=RetrievalFilters(
            file_path="backend/auth/",
        ),
    )

    assert len(results) == 1

    result = results[0]

    assert result.chunk.id == retrieval_dataset["chunks"][0].id

def test_chunk_type_filter(db, retrieval_dataset):
    repository = VectorStoreRepository(db)

    results = repository.similarity_search(
        query_vector=retrieval_dataset["query_vector"],
        repository_id=retrieval_dataset["repository_id"],
        model="filter-test-model",
        top_k=10,
        filters=RetrievalFilters(
            chunk_type="function",
        ),
    )

    assert len(results) == 2

    assert all(
        result.chunk.chunk_type == ChunkType.FUNCTION
        for result in results
    )


def test_symbol_name_filter(db, retrieval_dataset):
    repository = VectorStoreRepository(db)

    results = repository.similarity_search(
        query_vector=retrieval_dataset["query_vector"],
        repository_id=retrieval_dataset["repository_id"],
        model="filter-test-model",
        top_k=10,
        filters=RetrievalFilters(
            symbol_name="authenticate_user",
        ),
    )

    assert len(results) == 1

    result = results[0]

    assert result.chunk.symbol_name == "authenticate_user"


def test_multiple_filters_use_and_logic(db, retrieval_dataset):
    repository = VectorStoreRepository(db)

    results = repository.similarity_search(
        query_vector=retrieval_dataset["query_vector"],
        repository_id=retrieval_dataset["repository_id"],
        model="filter-test-model",
        top_k=10,
        filters=RetrievalFilters(
            language="python",
            chunk_type="function",
        ),
    )

    assert len(results) == 1

    result = results[0]

    assert result.chunk.id == retrieval_dataset["chunks"][0].id
    assert result.chunk.symbol_name == "authenticate_user"
    assert result.chunk.chunk_type == ChunkType.FUNCTION


def test_repository_isolation_is_always_enforced(
    db,
    retrieval_dataset,
):
    repository = VectorStoreRepository(db)

    results = repository.similarity_search(
        query_vector=retrieval_dataset["query_vector"],
        repository_id=retrieval_dataset["repository_id"],
        model="filter-test-model",
        top_k=10,
        filters=RetrievalFilters(
            language="python",
            symbol_name="authenticate_user",
        ),
    )

    result_chunk_ids = {
        result.chunk.id
        for result in results
    }

    assert retrieval_dataset["other_chunk"].id not in result_chunk_ids

    assert all(
        result.chunk.repository_id
        == retrieval_dataset["repository_id"]
        for result in results
    )

def test_role_filter(db, retrieval_dataset):
    service = VectorStoreService(db)

    results = service.similarity_search(
        query_vector=retrieval_dataset["query_vector"],
        repository_id=retrieval_dataset["repository_id"],
        model="filter-test-model",
        top_k=10,
        filters=RetrievalFilters(
            role=FileRole.SOURCE,
        ),
    )

    assert len(results) == 3

    result_chunk_ids = {
        result.chunk.id
        for result in results
    }

    expected_chunk_ids = {
        chunk.id
        for chunk in retrieval_dataset["chunks"]
    }

    assert result_chunk_ids == expected_chunk_ids