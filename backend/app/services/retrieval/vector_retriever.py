from sqlalchemy.orm import Session

from app.schemas.retrieval import RetrievedChunk
from app.services.retrieval.filters import RetrievalFilters
from app.services.vector_store.service import VectorStoreService


class VectorRetriever:
    """Retrieves relevant chunks using the existing vector store."""

    def __init__(self, db: Session) -> None:
        self._vector_store = VectorStoreService(db)

    def search(
        self,
        *,
        query_vector: list[float],
        repository_id: int,
        model: str,
        top_k: int,
        filters: RetrievalFilters | None = None,
        candidate_chunk_ids: list[int] | None = None,
    ) -> list[RetrievedChunk]:
        """Perform repository-scoped vector similarity search."""

        results = self._vector_store.similarity_search(
            query_vector=query_vector,
            repository_id=repository_id,
            model=model,
            top_k=top_k,
            filters=filters,
            candidate_chunk_ids=candidate_chunk_ids,
        )

        retrieved_chunks = []

        for result in results:
            chunk = result.chunk

            retrieved_chunks.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    content=chunk.content,
                    file_path=result.file_path or "unknown",
                    similarity_score=result.score,
                )
            )

        return retrieved_chunks
