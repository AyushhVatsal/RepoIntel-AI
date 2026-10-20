
import logging
from functools import lru_cache
from time import perf_counter

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

logger = logging.getLogger(__name__)


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
        total_start = perf_counter()

        # Stage 1: Embed the query.
        stage_start = perf_counter()
        query_vector = self._embedding_service.embed_query(
            request.query
        )
        query_embedding_ms = (
            perf_counter() - stage_start
        ) * 1000

        # Stage 2: Dense + lexical retrieval and RRF fusion.
        stage_start = perf_counter()
        rrf_results = self._hybrid_retriever.search(
            query_vector=query_vector,
            repository_id=request.repository_id,
            model=self._embedding_service.model_name,
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
        )
        hybrid_search_ms = (
            perf_counter() - stage_start
        ) * 1000

        if not rrf_results:
            total_ms = (perf_counter() - total_start) * 1000

            logger.info(
                "baseline_retrieval_timing "
                "repository_id=%s top_k=%s "
                "query_embedding_ms=%.2f "
                "hybrid_search_ms=%.2f "
                "candidate_fetch_ms=0.00 "
                "cross_encoder_ms=0.00 "
                "weighted_fusion_ms=0.00 "
                "hydration_ms=0.00 total_ms=%.2f "
                "candidate_count=0 result_count=0 "
                "reranking_skipped=%s",
                request.repository_id,
                request.top_k,
                query_embedding_ms,
                hybrid_search_ms,
                total_ms,
                False,
            )

            return RetrievalResponse(
                repository_id=request.repository_id,
                query=request.query,
                results=[],
            )

        # Preserve the existing conditional reranking behavior.
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

        candidate_fetch_ms = 0.0
        cross_encoder_ms = 0.0
        weighted_fusion_ms = 0.0

        if should_skip_reranking:
            final_results = rrf_results[:request.top_k]
        else:
            # Stage 3: Fetch candidate content for reranking.
            stage_start = perf_counter()
            chunks = chunk_crud.get_by_ids(
                self._db,
                [result.chunk_id for result in rrf_results],
            )
            documents = {
                chunk.id: chunk.content
                for chunk in chunks
            }
            candidate_fetch_ms = (
                perf_counter() - stage_start
            ) * 1000

            # Stage 4: Cross-encoder reranking.
            stage_start = perf_counter()
            cross_encoder_results = self._cross_encoder.rerank(
                query=request.query,
                results=rrf_results,
                documents=documents,
                top_k=len(rrf_results),
            )
            cross_encoder_ms = (
                perf_counter() - stage_start
            ) * 1000

            # Stage 5: Weighted fusion.
            stage_start = perf_counter()
            final_results = self._weighted_fusion.fuse(
                rrf_results=rrf_results,
                cross_encoder_results=cross_encoder_results,
                top_k=request.top_k,
            )
            weighted_fusion_ms = (
                perf_counter() - stage_start
            ) * 1000

        # Stage 6: Hydrate final retrieval results.
        stage_start = perf_counter()
        hydrated_results = self._hydrator.hydrate(final_results)
        hydration_ms = (
            perf_counter() - stage_start
        ) * 1000

        total_ms = (perf_counter() - total_start) * 1000

        logger.info(
            "baseline_retrieval_timing "
            "repository_id=%s top_k=%s "
            "query_embedding_ms=%.2f "
            "hybrid_search_ms=%.2f "
            "candidate_fetch_ms=%.2f "
            "cross_encoder_ms=%.2f "
            "weighted_fusion_ms=%.2f "
            "hydration_ms=%.2f total_ms=%.2f "
            "candidate_count=%s result_count=%s "
            "reranking_skipped=%s",
            request.repository_id,
            request.top_k,
            query_embedding_ms,
            hybrid_search_ms,
            candidate_fetch_ms,
            cross_encoder_ms,
            weighted_fusion_ms,
            hydration_ms,
            total_ms,
            len(rrf_results),
            len(hydrated_results),
            should_skip_reranking,
        )

        return RetrievalResponse(
            repository_id=request.repository_id,
            query=request.query,
            results=hydrated_results,
        )
