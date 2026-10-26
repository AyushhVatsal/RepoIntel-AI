
import logging
from time import perf_counter

from sqlalchemy.orm import Session

from app.schemas.retrieval import RetrievalRequest, RetrievalResponse
from app.services.retrieval.graph_candidate_selector import (
    select_graph_candidates,
)
from app.services.retrieval.fusion.graph_fusion import GraphFusion
from app.services.retrieval.graph_retriever import GraphRetriever
from app.services.retrieval.hydrator import RetrievalResultHydrator
from app.services.retrieval.result import RetrievalResult
from app.services.retrieval.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)


class GraphEnhancedRetrievalService:
    """Coordinate baseline retrieval with bounded graph expansion."""

    def __init__(
        self,
        db: Session,
        *,
        baseline_service: RetrievalService | None = None,
        graph_retriever: GraphRetriever | None = None,
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
            else RetrievalService(db)
        )
        self._graph_retriever = (
            graph_retriever
            if graph_retriever is not None
            else GraphRetriever(db)
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

        logger.info(
            "graph_debug stage=baseline query=%r candidates=%s",
            request.query,
            [
                {
                    "chunk_id": result.chunk_id,
                    "score": round(result.score, 5),
                }
                for result in baseline_results
            ],
        )

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

        logger.info(
            "graph_debug stage=raw_graph query=%r candidates=%s",
            request.query,
            [
                {
                    "chunk_id": result.chunk_id,
                    "file_id": result.file_id,
                    "hop_count": result.hop_count,
                    "score": round(result.score, 5),
                }
                for result in raw_graph_results
            ],
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

        logger.info(
            "graph_debug stage=selected_graph query=%r candidates=%s",
            request.query,
            [
                {
                    "chunk_id": result.chunk_id,
                    "file_id": result.file_id,
                    "hop_count": result.hop_count,
                    "score": round(result.score, 5),
                }
                for result in graph_results
            ],
        )
        selection_ms = (perf_counter() - stage_started) * 1000

        # Stage 4: Fuse baseline and graph evidence.
        # Use request.top_k as baseline_reserve when auto (-1) so that genuine
        # baseline hits cannot be displaced by unverified graph candidates.
        stage_started = perf_counter()
        effective_reserve = (
            request.top_k
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

        logger.info(
            "graph_debug stage=fused query=%r candidates=%s",
            request.query,
            [
                {
                    "chunk_id": result.chunk_id,
                    "score": round(result.score, 5),
                }
                for result in fused_results
            ],
        )

        # Stage 5: Hydrate the final result set.
        stage_started = perf_counter()
        hydrated_results = self._hydrator.hydrate(fused_results)

        logger.info(
            "graph_debug stage=hydrated query=%r results=%s",
            request.query,
            [
                {
                    "chunk_id": getattr(result, "chunk_id", None),
                    "file_path": getattr(result, "file_path", None),
                    "score": getattr(result, "retrieval_score", None),
                }
                for result in hydrated_results
            ],
        )
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
