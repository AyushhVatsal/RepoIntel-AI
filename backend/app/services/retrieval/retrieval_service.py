
from functools import lru_cache

from sqlalchemy.orm import Session

from app.crud.chunk import chunk_crud
from app.schemas.retrieval import (
    RetrievalRequest,
    RetrievalResponse,
)
from app.services.embedding.models.embedding_config import EmbeddingConfig
from app.services.embedding.providers.local import (
    get_local_embedding_provider,
)
from app.services.embedding.service import EmbeddingService
from app.services.retrieval.candidate_filter import RetrievalCandidateFilter
from app.services.retrieval.fusion.rrf import RRFFusion
from app.services.retrieval.fusion.weighted import WeightedFusion
from app.services.retrieval.hybrid.retriever import HybridRetriever
from app.services.retrieval.hydrator import RetrievalResultHydrator
from app.services.retrieval.lexical.manager import (
    get_bm25_index_manager,
)
from app.services.retrieval.lexical.retriever import LexicalRetriever
from app.services.retrieval.reranking.cross_encoder import (
    CrossEncoderReranker,
)
from app.services.retrieval.vector_retriever import VectorRetriever


@lru_cache(maxsize=1)
def get_cross_encoder_reranker() -> CrossEncoderReranker:
    """Reuse one cross-encoder instance per process."""
    return CrossEncoderReranker()


class RetrievalService:
    """Coordinate hybrid retrieval, reranking, and score fusion."""

    def __init__(
        self,
        db: Session,
        *,
        conditional_rerank_threshold: float | None = None,
    ) -> None:
        if (
            conditional_rerank_threshold is not None
            and conditional_rerank_threshold < 0
        ):
            raise ValueError(
                "conditional_rerank_threshold must be non-negative"
            )

        self._db = db
        self._conditional_rerank_threshold = (
            conditional_rerank_threshold
        )

        config = EmbeddingConfig()
        provider = get_local_embedding_provider(config.model)

        self._embedding_service = EmbeddingService(
            provider=provider,
            config=config,
        )

        vector_retriever = VectorRetriever(db)
        index_manager = get_bm25_index_manager()
        lexical_retriever = LexicalRetriever(
            db,
            index_manager,
        )

        self._hybrid_retriever = HybridRetriever(
            vector_retriever=vector_retriever,
            lexical_retriever=lexical_retriever,
            fusion=RRFFusion(),
            candidate_filter=RetrievalCandidateFilter(db),
        )

        self._cross_encoder = get_cross_encoder_reranker()
        self._weighted_fusion = WeightedFusion(
            rrf_weight=0.90,
            cross_encoder_weight=0.10,
        )

        self._hydrator = RetrievalResultHydrator(db)

    def retrieve(
        self,
        request: RetrievalRequest,
    ) -> RetrievalResponse:
        """Retrieve, rerank, and fuse repository code chunks."""

        # Retrieve up to request.top_k candidates using dense
        # and lexical search followed by RRF fusion.
        rrf_results = self._hybrid_retriever.search(
            query_vector=self._embedding_service.embed_query(
                request.query
            ),
            repository_id=request.repository_id,
            model=self._embedding_service.model_name,
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
        )

        if not rrf_results:
            return RetrievalResponse(
                repository_id=request.repository_id,
                query=request.query,
                results=[],
            )

        # Optionally skip reranking when the leading RRF score
        # gap meets the configured threshold.
        should_skip_reranking = (
            self._conditional_rerank_threshold is not None
            and (
                len(rrf_results) < 2
                or (
                    rrf_results[0].score - rrf_results[1].score
                    >= self._conditional_rerank_threshold
                )
            )
        )

        if should_skip_reranking:
            final_results = rrf_results[:request.top_k]
        else:
            # Load candidate documents for reranking.
            chunks = chunk_crud.get_by_ids(
                self._db,
                [result.chunk_id for result in rrf_results],
            )
            documents = {
                chunk.id: chunk.content
                for chunk in chunks
            }

            # Rerank the complete candidate pool.
            cross_encoder_results = self._cross_encoder.rerank(
                query=request.query,
                results=rrf_results,
                documents=documents,
                top_k=len(rrf_results),
            )

            # Combine normalized RRF and cross-encoder scores.
            final_results = self._weighted_fusion.fuse(
                rrf_results=rrf_results,
                cross_encoder_results=cross_encoder_results,
                top_k=request.top_k,
            )

        hydrated_results = self._hydrator.hydrate(final_results)

        return RetrievalResponse(
            repository_id=request.repository_id,
            query=request.query,
            results=hydrated_results,
        )
