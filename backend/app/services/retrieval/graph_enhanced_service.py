
import logging
from time import perf_counter

from sqlalchemy.orm import Session

from app.models.repository_file import FileRole
from app.schemas.retrieval import RetrievalRequest, RetrievalResponse
from app.services.retrieval.filters import RetrievalFilters
from app.services.retrieval.fusion.graph_fusion import GraphFusion
from app.services.retrieval.graph_candidate_selector import (
    select_graph_candidates,
)
from app.services.retrieval.graph_retriever import (
    GraphRetrievalResult,
    GraphRetriever,
)
from app.services.retrieval.hydrator import RetrievalResultHydrator
from app.services.retrieval.result import RetrievalResult
from app.services.retrieval.retrieval_service import RetrievalService
from app.services.retrieval.vector_retriever import VectorRetriever

logger = logging.getLogger(__name__)


class GraphEnhancedRetrievalService:
    """Coordinate baseline retrieval with bounded graph expansion."""

    def __init__(
        self,
        db: Session,
        *,
        baseline_service: RetrievalService | None = None,
        graph_retriever: GraphRetriever | None = None,
        vector_retriever: VectorRetriever | None = None,
        graph_fusion: GraphFusion | None = None,
        hydrator: RetrievalResultHydrator | None = None,
        max_hops: int = 1,
        graph_candidate_multiplier: int = 5,
        max_graph_candidates: int = 100,
        max_graph_candidates_per_file: int = 2,
        baseline_reserve: int = -1,
    ) -> None:
        if max_hops < 0:
            raise ValueError("max_hops must be non-negative")
        if graph_candidate_multiplier < 1:
            raise ValueError(
                "graph_candidate_multiplier must be at least 1"
            )
        if max_graph_candidates < 1:
            raise ValueError(
                "max_graph_candidates must be at least 1"
            )
        if max_graph_candidates_per_file < 1:
            raise ValueError(
                "max_graph_candidates_per_file must be at least 1"
            )
        if baseline_reserve < -1:
            raise ValueError(
                "baseline_reserve must be non-negative or -1 (auto)"
            )

        self._baseline_service = (
            baseline_service
            if baseline_service is not None
            else RetrievalService(
                db,
                conditional_rerank_threshold=0.001,
            )
        )
        self._graph_retriever = (
            graph_retriever
            if graph_retriever is not None
            else GraphRetriever(db)
        )
        self._vector_retriever = (
            vector_retriever
            if vector_retriever is not None
            else VectorRetriever(db)
        )
        self._graph_fusion = (
            graph_fusion
            if graph_fusion is not None
            else GraphFusion()
        )
        self._hydrator = (
            hydrator
            if hydrator is not None
            else RetrievalResultHydrator(db)
        )

        self._max_hops = max_hops
        self._graph_candidate_multiplier = graph_candidate_multiplier
        self._max_graph_candidates = max_graph_candidates
        self._max_graph_candidates_per_file = (
            max_graph_candidates_per_file
        )
        self._baseline_reserve = baseline_reserve

    def retrieve(
        self,
        request: RetrievalRequest,
    ) -> RetrievalResponse:
        """Retrieve baseline results and augment them with graph context."""

        request_started = perf_counter()

        # Stage 1: Existing hybrid baseline retrieval.
        stage_started = perf_counter()
        query_vector: list[float] | None = None
        if isinstance(self._baseline_service, RetrievalService):
            query_vector = self._baseline_service.embed_query(request.query)
            baseline_response = self._baseline_service.retrieve(
                request,
                query_vector=query_vector,
            )
        else:
            baseline_response = self._baseline_service.retrieve(request)
        baseline_ms = (perf_counter() - stage_started) * 1000

        baseline_results = [
            RetrievalResult(
                chunk_id=result.chunk_id,
                score=(
                    result.retrieval_score
                    if result.retrieval_score is not None
                    else result.similarity_score or 0.0
                ),
                dense_score=result.similarity_score,
                retrieval_score=result.retrieval_score,
            )
            for result in baseline_response.results
        ]

        seed_chunk_ids = [
            result.chunk_id for result in baseline_results
        ]

        if not seed_chunk_ids:
            total_ms = (perf_counter() - request_started) * 1000
            logger.info(
                "graph_retrieval_timing repository_id=%s "
                "top_k=%s baseline_ms=%.2f graph_ms=0 "
                "selection_ms=0 fusion_ms=0 hydration_ms=0 "
                "total_ms=%.2f",
                request.repository_id,
                request.top_k,
                baseline_ms,
                total_ms,
            )
            return baseline_response

        # Stage 2: Fetch a bounded graph candidate pool.
        stage_started = perf_counter()
        raw_graph_results = self._graph_retriever.retrieve(
            repository_id=request.repository_id,
            seed_chunk_ids=seed_chunk_ids,
            max_hops=self._max_hops,
            top_k=self._max_graph_candidates,
        )

        graph_ms = (perf_counter() - stage_started) * 1000

        # Stage 3: Limit graph candidates and improve file diversity.
        stage_started = perf_counter()
        graph_top_k = min(
            request.top_k * self._graph_candidate_multiplier,
            self._max_graph_candidates,
        )
        graph_results = select_graph_candidates(
            raw_graph_results,
            top_k=graph_top_k,
            max_per_file=self._max_graph_candidates_per_file,
        )

        # Graph distance establishes relatedness, not query relevance. Score
        # the bounded graph set with the same query embedding before fusion.
        if query_vector is not None and graph_results:
            graph_filters = request.filters or RetrievalFilters()
            excluded_roles = list(graph_filters.exclude_roles or [])
            for role in (FileRole.TEST, FileRole.FIXTURE):
                if role not in excluded_roles:
                    excluded_roles.append(role)
            graph_filters = graph_filters.model_copy(
                update={"exclude_roles": excluded_roles}
            )
            graph_scores = self._vector_retriever.search(
                query_vector=query_vector,
                repository_id=request.repository_id,
                model=self._baseline_service.embedding_model_name,
                top_k=len(graph_results),
                filters=graph_filters,
                candidate_chunk_ids=[
                    result.chunk_id for result in graph_results
                ],
            )
            score_by_chunk = {
                result.chunk_id: result.similarity_score or 0.0
                for result in graph_scores
            }
            graph_results = [
                GraphRetrievalResult(
                    chunk_id=result.chunk_id,
                    file_id=result.file_id,
                    hop_count=result.hop_count,
                    score=result.score,
                    query_score=score_by_chunk[result.chunk_id],
                )
                for result in graph_results
                if result.chunk_id in score_by_chunk
            ]

        selection_ms = (perf_counter() - stage_started) * 1000

        # Stage 4: Fuse baseline and graph evidence.
        # Protect half of the baseline results while allowing query-scored
        # graph candidates to compete for the remaining positions.
        stage_started = perf_counter()
        effective_reserve = (
            max(1, request.top_k // 2)
            if self._baseline_reserve == -1
            else self._baseline_reserve
        )
        fused_results = self._graph_fusion.fuse(
            baseline_results=baseline_results,
            graph_results=graph_results,
            top_k=request.top_k,
            baseline_reserve=effective_reserve,
        )
        fusion_ms = (perf_counter() - stage_started) * 1000

        # Stage 5: Hydrate the final result set.
        stage_started = perf_counter()
        hydrated_results = self._hydrator.hydrate(fused_results)
        hydration_ms = (perf_counter() - stage_started) * 1000

        total_ms = (perf_counter() - request_started) * 1000

        logger.info(
            "graph_retrieval_timing repository_id=%s "
            "top_k=%s baseline_ms=%.2f graph_ms=%.2f "
            "selection_ms=%.2f fusion_ms=%.2f "
            "hydration_ms=%.2f total_ms=%.2f "
            "baseline_count=%s raw_graph_count=%s "
            "selected_graph_count=%s fused_count=%s "
            "baseline_reserve=%s",
            request.repository_id,
            request.top_k,
            baseline_ms,
            graph_ms,
            selection_ms,
            fusion_ms,
            hydration_ms,
            total_ms,
            len(baseline_results),
            len(raw_graph_results),
            len(graph_results),
            len(fused_results),
            self._baseline_reserve,
        )

        return RetrievalResponse(
            repository_id=request.repository_id,
            query=request.query,
            results=hydrated_results,
        )
