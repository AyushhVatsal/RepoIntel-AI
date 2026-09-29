from sqlalchemy.orm import Session

from app.schemas.retrieval import (
    RetrievalRequest,
    RetrievalResponse,
)
from app.services.embedding.models.embedding_config import EmbeddingConfig
from app.services.embedding.providers.local import LocalEmbeddingProvider
from app.services.embedding.service import EmbeddingService
from app.services.retrieval.fusion.rrf import RRFFusion
from app.services.retrieval.hydrator import RetrievalResultHydrator
from app.services.retrieval.hybrid.retriever import HybridRetriever
from app.services.retrieval.lexical.retriever import LexicalRetriever
from app.services.retrieval.vector_retriever import VectorRetriever
from app.services.retrieval.lexical.manager import BM25IndexManager
from app.services.retrieval.candidate_filter import RetrievalCandidateFilter

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

        vector_retriever = VectorRetriever(db)
        index_manager = BM25IndexManager()

        lexical_retriever = LexicalRetriever(
            db,
            index_manager,
        )
        
        fusion = RRFFusion()

        candidate_filter = RetrievalCandidateFilter(db)

        self._hybrid_retriever = HybridRetriever(
            vector_retriever=vector_retriever,
            lexical_retriever=lexical_retriever,
            fusion=fusion,
            candidate_filter=candidate_filter,
        )

        self._hydrator = RetrievalResultHydrator(db)

    def retrieve(
        self,
        request: RetrievalRequest,
    ) -> RetrievalResponse:
        """Retrieve relevant chunks for a query."""

        query_vector = self._embedding_service.embed_query(
            request.query
        )

        retrieval_results = self._hybrid_retriever.search(
            query_vector=query_vector,
            repository_id=request.repository_id,
            model=self._embedding_service.model_name,
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
        )

        results = self._hydrator.hydrate(
            retrieval_results
        )

        return RetrievalResponse(
            repository_id=request.repository_id,
            query=request.query,
            results=results,
        )