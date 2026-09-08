from sqlalchemy.orm import Session

from app.crud.repository_file import repository_file_crud
from app.schemas.retrieval import RetrievedChunk
from app.services.vector_store.service import VectorStoreService


class VectorRetriever:
    """Retrieves relevant chunks using the existing vector store."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._vector_store = VectorStoreService(db)

    def search(
        self,
        *,
        query_vector: list[float],
        repository_id: int,
        model: str,
        top_k: int,
    ) -> list[RetrievedChunk]:
        """Perform repository-scoped vector similarity search."""

        results = self._vector_store.similarity_search(
            query_vector=query_vector,
            repository_id=repository_id,
            model=model,
            top_k=top_k,
        )

        retrieved_chunks = []

        for result in results:
            chunk = result.chunk

            repository_file = repository_file_crud.get(
                self._db,
                chunk.file_id,
            )

            file_path = (
                repository_file.relative_path
                if repository_file is not None
                else "unknown"
            )

            retrieved_chunks.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    content=chunk.content,
                    file_path=file_path,
                    similarity_score=result.score,
                )
            )

        return retrieved_chunks