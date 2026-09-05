from sqlalchemy.orm import Session

from app.crud.embedding import upsert
from app.services.vector_store.repository import VectorStoreRepository
from app.services.vector_store.models import VectorSearchResult


class VectorStoreService:
    def __init__(self, db: Session) -> None:
        self.repository = VectorStoreRepository(db)

    def store_embedding(
        self,
        chunk_id: int,
        model: str,
        dimensions: int,
        embedding: list[float],
    ):
        if chunk_id <= 0:
            raise ValueError("chunk_id must be greater than 0")

        if not model.strip():
            raise ValueError("model must not be empty")

        if dimensions <= 0:
            raise ValueError("dimensions must be greater than 0")

        if len(embedding) != dimensions:
            raise ValueError(
                f"embedding dimension mismatch: "
                f"expected {dimensions}, got {len(embedding)}"
            )

        return upsert(
            db=self.repository.db,
            chunk_id=chunk_id,
            model=model,
            dimensions=dimensions,
            embedding=embedding,
        )

    def similarity_search(
        self,
        query_vector: list[float],
        repository_id: int,
        model: str,
        top_k: int = 10,
        score_threshold: float | None = None,
    ) -> list[VectorSearchResult]:
        if repository_id <= 0:
            raise ValueError("repository_id must be greater than 0")

        if not model.strip():
            raise ValueError("model must not be empty")

        if not query_vector:
            raise ValueError("query_vector must not be empty")

        if top_k <= 0:
            raise ValueError("top_k must be greater than 0")

        if score_threshold is not None and not 0 <= score_threshold <= 1:
            raise ValueError("score_threshold must be between 0 and 1")

        return self.repository.similarity_search(
            query_vector=query_vector,
            repository_id=repository_id,
            model=model,
            top_k=top_k,
            score_threshold=score_threshold,
        )