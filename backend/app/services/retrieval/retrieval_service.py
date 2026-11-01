import logging
import re
from functools import lru_cache
from time import perf_counter

from sqlalchemy.orm import Session

from app.schemas.retrieval import (
    RetrievalRequest,
    RetrievalResponse,
    RetrievedChunk,
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

_DEFINITION_QUERY_RE = re.compile(
    r"^\s*(?:"
    r"what\s+does\s+.+\s+do|"
    r"which\s+file\s+(?:defines|contains)\s+.+|"
    r"where\s+is\s+.+\s+(?:defined|implemented)"
    r")\??\s*$",
    re.IGNORECASE,
)
_CONFIGURATION_QUERY_RE = re.compile(
    r"^\s*(?:(?:what|which|how(?:\s+many)?|where)\s+.{0,100}"
    r"\b(?:embedding\s+model|batch\s+size|"
    r"dimensions?|configuration|settings?)\b|"
    r"(?:what|which)\s+(?:embedding\s+)?provider\b|"
    r"where\s+.{0,100}\b(?:configured|set|stored)\b)"
    r"\??\s*$",
    re.IGNORECASE,
)
_BATCHING_QUERY_RE = re.compile(
    r"\b(?:batch(?:ed|ing)?|batcher)\b",
    re.IGNORECASE,
)
_LEXICAL_NAVIGATION_QUERY_RE = re.compile(
    r"\b(?:alembic|migrations?|file\s+paths?|filenames?|source\s+paths?)\b|"
    r"\b[a-zA-Z0-9_.-]+/[a-zA-Z0-9_./-]+\b",
    re.IGNORECASE,
)


def _is_definition_query(query: str) -> bool:
    return bool(_DEFINITION_QUERY_RE.match(query))


def _is_configuration_query(query: str) -> bool:
    return bool(_CONFIGURATION_QUERY_RE.match(query))


def _is_batching_query(query: str) -> bool:
    return bool(_BATCHING_QUERY_RE.search(query))


def _is_lexical_navigation_query(query: str) -> bool:
    return bool(_LEXICAL_NAVIGATION_QUERY_RE.search(query))


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
        conditional_rerank_threshold: float | None = 0.0005,
        candidate_pool_k: int = 10,
        rerank_candidate_pool_k: int = 5,
        rrf_weight: float = 0.90,
        cross_encoder_weight: float = 0.10,
    ) -> None:
        if (
            conditional_rerank_threshold is not None
            and conditional_rerank_threshold < 0
        ):
            raise ValueError("conditional_rerank_threshold must be non-negative")
        if candidate_pool_k < 1:
            raise ValueError("candidate_pool_k must be at least 1")
        if rerank_candidate_pool_k < 1:
            raise ValueError("rerank_candidate_pool_k must be at least 1")

        self._db = db
        self._conditional_rerank_threshold = conditional_rerank_threshold
        self._candidate_pool_k = candidate_pool_k
        self._rerank_candidate_pool_k = rerank_candidate_pool_k

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
            fusion=RRFFusion(source_weights=(0.8, 0.2)),
            candidate_filter=RetrievalCandidateFilter(db),
        )

        # Load the cross-encoder only when this request actually needs a
        # rerank. Requests that safely keep the RRF order avoid model-load
        # cost on cold start.
        self._cross_encoder: CrossEncoderReranker | None = None
        self._weighted_fusion = WeightedFusion(
            rrf_weight=rrf_weight,
            cross_encoder_weight=cross_encoder_weight,
        )
        self._configuration_fusion = WeightedFusion(
            rrf_weight=0.9,
            cross_encoder_weight=0.1,
        )

        self._hydrator = RetrievalResultHydrator(db)

    @staticmethod
    def _limit_file_repetition(
        results: list[RetrievedChunk],
        *,
        top_k: int,
        max_per_file: int = 1,
    ) -> list[RetrievedChunk]:
        """Prefer distinct files, backfilling only when needed to fill top-k."""
        selected: list[RetrievedChunk] = []
        deferred: list[RetrievedChunk] = []
        file_counts: dict[str, int] = {}

        for result in results:
            file_key = result.file_path.replace("\\", "/").casefold()
            if file_counts.get(file_key, 0) >= max_per_file:
                deferred.append(result)
                continue

            selected.append(result)
            file_counts[file_key] = file_counts.get(file_key, 0) + 1

        if len(selected) < top_k:
            selected.extend(deferred[: top_k - len(selected)])

        return selected[:top_k]

    def retrieve_hybrid_rrf(
        self,
        request: RetrievalRequest,
        *,
        query_vector: list[float] | None = None,
    ) -> list:
        """Retrieve and hydrate results using dense + BM25 + RRF only."""
        if query_vector is None:
            query_vector = self.embed_query(request.query)

        definition_question = _is_definition_query(request.query)
        configuration_question = _is_configuration_query(request.query)
        lexical_navigation_question = _is_lexical_navigation_query(request.query)
        targeted_question = (
            definition_question
            or configuration_question
            or lexical_navigation_question
            or _is_batching_query(request.query)
        )

        candidate_k = max(
            request.top_k,
            self._candidate_pool_k,
            10 if targeted_question else 0,
        )

        rrf_results = self._hybrid_retriever.search(
            query_vector=query_vector,
            repository_id=request.repository_id,
            model=self._embedding_service.model_name,
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
            candidate_k=candidate_k,
        )

        return self._hydrator.hydrate(rrf_results[: request.top_k])

    def retrieve(
        self,
        request: RetrievalRequest,
        *,
        query_vector: list[float] | None = None,
    ) -> RetrievalResponse:
        """Retrieve, rerank, and fuse repository code chunks."""
        total_start = perf_counter()

        # Stage 1: Embed the query.
        stage_start = perf_counter()
        if query_vector is None:
            query_vector = self.embed_query(request.query)
        query_embedding_ms = (perf_counter() - stage_start) * 1000

        definition_question = _is_definition_query(request.query)
        configuration_question = _is_configuration_query(request.query)
        lexical_navigation_question = _is_lexical_navigation_query(request.query)
        targeted_question = (
            definition_question
            or configuration_question
            or lexical_navigation_question
            or _is_batching_query(request.query)
        )

        # Stage 2: Dense + lexical retrieval and RRF fusion.
        # Fetch a larger candidate pool so the reranker has enough candidates
        # to surface relevant results that rank beyond top_k in RRF alone.
        stage_start = perf_counter()
        candidate_k = max(
            request.top_k,
            self._candidate_pool_k,
            10 if targeted_question else 0,
        )
        if lexical_navigation_question:
            # Keep narrow lexical lookups stable; extra ranks can otherwise
            # dilute exact file evidence in the primary RRF positions.
            candidate_k = request.top_k
        rrf_results = self._hybrid_retriever.search(
            query_vector=query_vector,
            repository_id=request.repository_id,
            model=self._embedding_service.model_name,
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
            candidate_k=candidate_k,
            preserve_top_k_order=True,
        )
        hybrid_search_ms = (perf_counter() - stage_start) * 1000

        if not rrf_results:
            total_ms = (perf_counter() - total_start) * 1000
            latency_breakdown = {
                "query_embedding_ms": query_embedding_ms,
                "hybrid_search_ms": hybrid_search_ms,
                "candidate_fetch_ms": 0.0,
                "cross_encoder_ms": 0.0,
                "weighted_fusion_ms": 0.0,
                "hydration_ms": 0.0,
                "service_total_ms": total_ms,
            }

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
                latency_ms=total_ms,
                reranking_applied=False,
                reranking_skip_reason="no_candidates",
                latency_breakdown_ms=latency_breakdown,
                results=[],
            )

        # Preserve the existing conditional reranking behavior.
        should_skip_reranking = (
            definition_question
            or lexical_navigation_question
            or (
                not configuration_question
                and self._conditional_rerank_threshold is not None
                and (
                    len(rrf_results) < 2
                    or (
                        rrf_results[0].score - rrf_results[1].score
                        >= self._conditional_rerank_threshold
                    )
                )
            )
        )

        # Hydrate the wider RRF pool once. The same rows supply both the
        # cross-encoder text and final response fields, avoiding a second DB
        # round trip later in the request.
        candidate_fetch_start = perf_counter()
        hydrated_by_id = {
            chunk.chunk_id: chunk for chunk in self._hydrator.hydrate(rrf_results)
        }
        candidate_fetch_ms = (perf_counter() - candidate_fetch_start) * 1000
        cross_encoder_ms = 0.0
        weighted_fusion_ms = 0.0
        reranking_skip_reason = (
            "definition_lookup_uses_hybrid_order"
            if definition_question
            else (
                "lexical_navigation_uses_hybrid_order"
                if lexical_navigation_question
                else ("rrf_margin_exceeded" if should_skip_reranking else None)
            )
        )
        ranking_policy = (
            "hybrid_rrf"
            if should_skip_reranking
            else (
                "cross_encoder_for_definition_or_location_query"
                if definition_question or configuration_question
                else "weighted_rrf_90_cross_encoder_10"
            )
        )

        if should_skip_reranking:
            final_results = rrf_results[:candidate_k]
        else:
            # Stage 3: Fetch candidate content for reranking.
            rerank_candidate_count = min(
                len(rrf_results),
                max(request.top_k, self._rerank_candidate_pool_k),
            )
            diverse_rerank_chunks = self._limit_file_repetition(
                [
                    hydrated_by_id[result.chunk_id]
                    for result in rrf_results
                    if result.chunk_id in hydrated_by_id
                ],
                top_k=rerank_candidate_count,
            )
            rerank_ids = {chunk.chunk_id for chunk in diverse_rerank_chunks}
            rerank_candidates = [
                result for result in rrf_results if result.chunk_id in rerank_ids
            ]
            documents = {
                chunk.chunk_id: chunk.content for chunk in diverse_rerank_chunks
            }

            # Stage 4: Cross-encoder reranking.
            stage_start = perf_counter()
            if self._cross_encoder is None:
                self._cross_encoder = get_cross_encoder_reranker()
            cross_encoder_results = self._cross_encoder.rerank(
                query=request.query,
                results=rerank_candidates,
                documents=documents,
                top_k=len(rerank_candidates),
            )
            cross_encoder_ms = (perf_counter() - stage_start) * 1000

            # Stage 5: Weighted fusion.
            stage_start = perf_counter()
            fusion = (
                self._configuration_fusion
                if configuration_question
                else self._weighted_fusion
            )
            final_results = fusion.fuse(
                # Every candidate entering score fusion has a CE score. The
                # wider pool is used for coverage and file diversity, while
                # the bounded rerank pool remains the actual ranked set.
                rrf_results=rerank_candidates,
                cross_encoder_results=cross_encoder_results,
                top_k=max(request.top_k, self._rerank_candidate_pool_k),
            )
            weighted_fusion_ms = (perf_counter() - stage_start) * 1000

        # Stage 6: Hydrate final retrieval results.
        stage_start = perf_counter()
        hydrated_candidates = []
        for result in final_results[:candidate_k]:
            chunk = hydrated_by_id.get(result.chunk_id)
            if chunk is None:
                continue
            hydrated_candidates.append(
                chunk.model_copy(
                    update={
                        "similarity_score": result.dense_score,
                        "hybrid_score": result.hybrid_score,
                        "cross_encoder_score": result.cross_encoder_score,
                        "retrieval_score": (
                            result.retrieval_score
                            if result.retrieval_score is not None
                            else result.score
                        ),
                    }
                )
            )
        hydrated_results = self._limit_file_repetition(
            hydrated_candidates,
            top_k=request.top_k,
        )
        hydration_ms = (perf_counter() - stage_start) * 1000

        total_ms = (perf_counter() - total_start) * 1000
        latency_breakdown = {
            "query_embedding_ms": query_embedding_ms,
            "hybrid_search_ms": hybrid_search_ms,
            "candidate_fetch_ms": candidate_fetch_ms,
            "cross_encoder_ms": cross_encoder_ms,
            "weighted_fusion_ms": weighted_fusion_ms,
            "hydration_ms": hydration_ms,
            "service_total_ms": total_ms,
        }

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
            latency_ms=total_ms,
            reranking_applied=not should_skip_reranking,
            reranking_skip_reason=reranking_skip_reason,
            ranking_policy=ranking_policy,
            latency_breakdown_ms=latency_breakdown,
            results=hydrated_results,
        )

    def embed_query(self, query: str) -> list[float]:
        """Embed a query for reuse by later retrieval stages."""
        return self._embedding_service.embed_query(query)

    @property
    def embedding_model_name(self) -> str:
        """Return the model identifier used for query and document vectors."""
        return self._embedding_service.model_name
