from sqlalchemy.orm import Session

from app.schemas.retrieval import (
    RetrievalRequest,
    RetrievalResponse,
)
from app.services.embedding.models.embedding_config import EmbeddingConfig
from app.services.embedding.providers.local import LocalEmbeddingProvider
from app.services.embedding.service import EmbeddingService
from app.services.retrieval.vector_retriever import VectorRetriever


class RetrievalService:
    """Coordinates query embedding and repository retrieval."""

    def __init__(self, db: Session) -> None:
        config = EmbeddingConfig()

        provider = LocalEmbeddingProvider(
            config.model
        )

        self._embedding_service = EmbeddingService(
            provider=provider,
            config=config,
        )

        self._vector_retriever = VectorRetriever(db)

    def retrieve(
        self,
        request: RetrievalRequest,
    ) -> RetrievalResponse:
        """Retrieve relevant chunks for a query."""

        query_vector = self._embedding_service.embed_query(
            request.query
        )

        results = self._vector_retriever.search(
            query_vector=query_vector,
            repository_id=request.repository_id,
            model=self._embedding_service.model_name,
            top_k=request.top_k,
        )

        return RetrievalResponse(
            repository_id=request.repository_id,
            query=request.query,
            results=results,
        )