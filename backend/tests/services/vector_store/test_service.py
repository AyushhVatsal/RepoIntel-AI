import pytest

from app.services.vector_store import VectorStoreService


def test_store_embedding_rejects_invalid_chunk_id():
    service = VectorStoreService.__new__(VectorStoreService)

    with pytest.raises(ValueError, match="chunk_id must be greater than 0"):
        service.store_embedding(
            chunk_id=0,
            model="BAAI/bge-small-en-v1.5",
            dimensions=384,
            embedding=[0.0] * 384,
        )


def test_store_embedding_rejects_empty_model():
    service = VectorStoreService.__new__(VectorStoreService)

    with pytest.raises(ValueError, match="model must not be empty"):
        service.store_embedding(
            chunk_id=1,
            model="   ",
            dimensions=384,
            embedding=[0.0] * 384,
        )


def test_store_embedding_rejects_invalid_dimensions():
    service = VectorStoreService.__new__(VectorStoreService)

    with pytest.raises(
        ValueError,
        match="dimensions must be greater than 0",
    ):
        service.store_embedding(
            chunk_id=1,
            model="BAAI/bge-small-en-v1.5",
            dimensions=0,
            embedding=[],
        )


def test_store_embedding_rejects_dimension_mismatch():
    service = VectorStoreService.__new__(VectorStoreService)

    with pytest.raises(
        ValueError,
        match="embedding dimension mismatch",
    ):
        service.store_embedding(
            chunk_id=1,
            model="BAAI/bge-small-en-v1.5",
            dimensions=384,
            embedding=[0.0] * 383,
        )


def test_similarity_search_rejects_invalid_repository_id():
    service = VectorStoreService.__new__(VectorStoreService)

    with pytest.raises(
        ValueError,
        match="repository_id must be greater than 0",
    ):
        service.similarity_search(
            query_vector=[0.0] * 384,
            repository_id=0,
            model="BAAI/bge-small-en-v1.5",
        )


def test_similarity_search_rejects_empty_model():
    service = VectorStoreService.__new__(VectorStoreService)

    with pytest.raises(ValueError, match="model must not be empty"):
        service.similarity_search(
            query_vector=[0.0] * 384,
            repository_id=1,
            model="   ",
        )


def test_similarity_search_rejects_empty_vector():
    service = VectorStoreService.__new__(VectorStoreService)

    with pytest.raises(
        ValueError,
        match="query_vector must not be empty",
    ):
        service.similarity_search(
            query_vector=[],
            repository_id=1,
            model="BAAI/bge-small-en-v1.5",
        )


def test_similarity_search_rejects_invalid_top_k():
    service = VectorStoreService.__new__(VectorStoreService)

    with pytest.raises(
        ValueError,
        match="top_k must be greater than 0",
    ):
        service.similarity_search(
            query_vector=[0.0] * 384,
            repository_id=1,
            model="BAAI/bge-small-en-v1.5",
            top_k=0,
        )


def test_similarity_search_rejects_invalid_score_threshold():
    service = VectorStoreService.__new__(VectorStoreService)

    with pytest.raises(
        ValueError,
        match="score_threshold must be between 0 and 1",
    ):
        service.similarity_search(
            query_vector=[0.0] * 384,
            repository_id=1,
            model="BAAI/bge-small-en-v1.5",
            score_threshold=1.5,
        )