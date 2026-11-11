
import logging
from time import perf_counter
from typing import Literal

from sqlalchemy.orm import Session

from app.models.repository_file import FileRole
from app.schemas.retrieval import RetrievalRequest, RetrievalResponse
from app.services.retrieval.filters import RetrievalFilters
from app.services.retrieval.fusion.graph_fusion import GraphFusion
from app.services.retrieval.graph_candidate_selector import (
    select_graph_candidates,
)
from app.services.retrieval.graph_retriever import (
    MAX_GRAPH_CANDIDATES,
    MAX_GRAPH_HOPS,
    GraphRetriever,
)
from app.services.retrieval.graph_seeder import GraphSeedRetriever
from app.services.retrieval.hydrator import RetrievalResultHydrator
from app.services.retrieval.lexical.manager import get_bm25_index_manager
from app.services.retrieval.lexical.retriever import LexicalRetriever
from app.services.retrieval.result import RetrievalResult
from app.services.retrieval.retrieval_service import (
    RetrievalService,
    create_production_retrieval_service,
)

logger = logging.getLogger(__name__)
GraphSeedStrategy = Literal[
    "post_rerank",
    "pre_rerank",
    "dual_source",
    "independent",
    "combined",
]


class GraphEnhancedRetrievalService:
    """Coordinate baseline retrieval with bounded graph expansion."""

    def __init__(
        self,
        db: Session,
        *,
        baseline_service: RetrievalService | None = None,
        graph_retriever: GraphRetriever | None = None,
        graph_seeder: GraphSeedRetriever | None = None,
        graph_fusion: GraphFusion | None = None,
        hydrator: RetrievalResultHydrator | None = None,
        max_hops: int = 1,
        graph_candidate_multiplier: int = 2,
        max_graph_candidates: int = 100,
        max_graph_candidates_per_file: int = 2,
        graph_weight: float = 0.05,
        baseline_reserve: int = -1,
        seed_strategy: GraphSeedStrategy = "pre_rerank",
        seed_budget: int = 5,
        graph_only: bool = False,
    ) -> None:
        if type(max_hops) is not int or not 0 <= max_hops <= MAX_GRAPH_HOPS:
            raise ValueError(
                f"max_hops must be between 0 and {MAX_GRAPH_HOPS}"
            )
        if graph_candidate_multiplier < 1:
            raise ValueError(
                "graph_candidate_multiplier must be at least 1"
            )
        if (
            type(max_graph_candidates) is not int
            or not 1 <= max_graph_candidates <= MAX_GRAPH_CANDIDATES
        ):
            raise ValueError(
                f"max_graph_candidates must be between 1 and "
                f"{MAX_GRAPH_CANDIDATES}"
            )
        if max_graph_candidates_per_file < 1:
            raise ValueError(
                "max_graph_candidates_per_file must be at least 1"
            )
        if not 0.0 <= graph_weight <= 1.0:
            raise ValueError("graph_weight must be between 0 and 1")
        if baseline_reserve < -1:
            raise ValueError(
                "baseline_reserve must be non-negative or -1 (auto)"
            )
        if seed_strategy not in (
            "post_rerank",
            "pre_rerank",
            "dual_source",
            "independent",
            "combined",
        ):
            raise ValueError("unsupported graph seed strategy")
        if type(seed_budget) is not int or not 1 <= seed_budget <= 100:
            raise ValueError("seed_budget must be between 1 and 100")
        

        self._baseline_service = (
            baseline_service
            if baseline_service is not None
            else create_production_retrieval_service(db)
        )
        self._graph_retriever = (
            graph_retriever
            if graph_retriever is not None
            else GraphRetriever(db)
        )
        self._graph_seeder = graph_seeder or GraphSeedRetriever(
            db, LexicalRetriever(db, get_bm25_index_manager())
        )
        self._graph_fusion = (
            graph_fusion
            if graph_fusion is not None
            else GraphFusion(
                baseline_weight=1.0 - graph_weight,
                graph_weight=graph_weight,
            )
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
        self._seed_strategy = seed_strategy
        self._seed_budget = seed_budget
        self._graph_only = graph_only
        self.last_seed_chunk_ids: list[int] = []
        self.last_independent_seed_ids: list[int] = []

    def retrieve(
        self,
        request: RetrievalRequest,
        imported_symbol: str | None = None,
    ) -> RetrievalResponse:
        """Retrieve baseline results and augment them with graph context."""

        request_started = perf_counter()

        # Stage 1: Query embedding and, except for independent graph-only
        # evaluation, the frozen Hybrid V2 baseline.
        stage_started = perf_counter()
        query_vector: list[float] | None = None
        independent_only = (
            self._graph_only
            and self._seed_strategy == "independent"
            and isinstance(self._baseline_service, RetrievalService)
        )
        if independent_only:
            query_vector = self._baseline_service.embed_query(request.query)
            baseline_response = RetrievalResponse(
                repository_id=request.repository_id,
                query=request.query,
                results=[],
            )
        elif isinstance(self._baseline_service, RetrievalService):
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

        post_rerank_seed_ids = [
            result.chunk_id for result in baseline_results
        ]
        raw_pre_rerank_seed_ids = getattr(
            self._baseline_service,
            "last_rrf_chunk_ids",
            (),
        )
        pre_rerank_seed_ids = (
            list(raw_pre_rerank_seed_ids)
            if isinstance(raw_pre_rerank_seed_ids, (tuple, list))
            else []
        )
        graph_filters = self._graph_filters(request.filters)
        independent_seed_ids: list[int] = []
        independent_seed_generation_ms = 0.0
        if self._seed_strategy in ("independent", "combined"):
            independent_seed_ids = self._graph_seeder.retrieve(
                repository_id=request.repository_id,
                query=request.query,
                top_k=self._seed_budget,
                candidate_pool_k=min(80, max(self._seed_budget * 8, self._seed_budget)),
                filters=graph_filters,
                max_per_file=1,
            )
            independent_seed_generation_ms = (
                self._graph_seeder.last_latency_ms
            )
        seed_chunk_ids = self._select_seed_ids(
            pre_rerank_seed_ids=pre_rerank_seed_ids,
            post_rerank_seed_ids=post_rerank_seed_ids,
            independent_seed_ids=independent_seed_ids,
            budget=self._seed_budget,
        )
        self.last_seed_chunk_ids = list(seed_chunk_ids)
        self.last_independent_seed_ids = list(independent_seed_ids)
        baseline_dense_scores = [
            result.dense_score
            for result in baseline_results
            if result.dense_score is not None
        ]
        relevance_floor = (
            min(baseline_dense_scores) if baseline_dense_scores else None
        )

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
            if self._graph_only:
                return baseline_response.model_copy(
                    update={
                        "results": [],
                        "latency_ms": total_ms,
                        "ranking_policy": self._ranking_policy(),
                        "latency_breakdown_ms": {
                            **(baseline_response.latency_breakdown_ms or {}),
                            "independent_seed_generation_ms": (
                                independent_seed_generation_ms
                            ),
                            "service_total_ms": total_ms,
                        },
                    }
                )
            return baseline_response

        # Stage 2: Fetch a bounded graph candidate pool.
        stage_started = perf_counter()

        graph_top_k = min(
            request.top_k * self._graph_candidate_multiplier,
            self._max_graph_candidates,
        )

        selected_seed_set = set(seed_chunk_ids)

        if imported_symbol is not None:
            raw_graph_results = self._graph_retriever.retrieve_importers(
                repository_id=request.repository_id,
                imported_symbol=imported_symbol,
                top_k=graph_top_k,
                max_per_file=self._max_graph_candidates_per_file,
                filters=graph_filters,
            )
        else:
            raw_graph_results = self._graph_retriever.retrieve(
                repository_id=request.repository_id,
                seed_chunk_ids=seed_chunk_ids,
                max_hops=self._max_hops,
                top_k=graph_top_k,
                filters=graph_filters,
                max_per_file=self._max_graph_candidates_per_file,
                query_vector=query_vector,
                embedding_model=(
                    self._baseline_service.embedding_model_name
                    if query_vector is not None
                    else None
                ),
                include_seed_chunk_ids=[
                    chunk_id
                    for chunk_id in independent_seed_ids
                    if chunk_id in selected_seed_set
                ],
            )

        graph_ms = (perf_counter() - stage_started) * 1000

        raw_graph_stage_metrics = getattr(
            self._graph_retriever,
            "last_latency_breakdown_ms",
            None,
        )

        graph_stage_metrics = (
            raw_graph_stage_metrics
            if isinstance(raw_graph_stage_metrics, dict)
            else {}
        )

        # Stage 3: Limit graph candidates and improve file diversity.
        stage_started = perf_counter()
        graph_results = select_graph_candidates(
            raw_graph_results,
            top_k=graph_top_k,
            max_per_file=self._max_graph_candidates_per_file,
        )

        # In hybrid+graph mode, admit an expanded result only when its raw
        # cosine similarity is at least as strong as the weakest baseline
        # result's dense similarity. Graph-only evaluation intentionally
        # bypasses this gate so it measures graph candidates independently.
        # This uses the same query vector and avoids min-max normalization of
        # a weak graph pool granting its best (but still irrelevant) item a
        # full graph fusion bonus.
        graph_candidates_rejected_by_relevance = 0
        if not self._graph_only and baseline_dense_scores and any(
            result.query_score is not None for result in graph_results
        ):
            assert relevance_floor is not None
            before_gate = len(graph_results)
            graph_results = [
                result
                for result in graph_results
                if result.query_score is not None
                and result.query_score >= relevance_floor
            ]
            graph_candidates_rejected_by_relevance = (
                before_gate - len(graph_results)
            )

        if query_vector is not None and graph_results:
            graph_results = [
                result
                for result in graph_results
                if result.query_score is not None
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
            baseline_results=([] if self._graph_only else baseline_results),
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
            "baseline_reserve=%s seed_strategy=%s seed_count=%s",
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
            self._seed_strategy,
            len(seed_chunk_ids),
        )

        return RetrievalResponse(
            repository_id=request.repository_id,
            query=request.query,
            latency_ms=total_ms,
            reranking_applied=baseline_response.reranking_applied,
            reranking_skip_reason=baseline_response.reranking_skip_reason,
            ranking_policy=self._ranking_policy(),
            latency_breakdown_ms={
                "baseline_ms": baseline_ms,
                "graph_ms": graph_ms,
                "graph_candidate_generation_ms": graph_ms,
                **graph_stage_metrics,
                "selection_ms": selection_ms,
                "candidate_selection_ms": selection_ms,
                "fusion_ms": fusion_ms,
                "hydration_ms": hydration_ms,
                "graph_candidates": float(len(raw_graph_results)),
                "graph_candidates_rejected_by_relevance": float(
                    graph_candidates_rejected_by_relevance
                ),
                "independent_seed_generation_ms": (
                    independent_seed_generation_ms
                ),
                "service_total_ms": total_ms,
            },
            results=hydrated_results,
        )

    def _select_seed_ids(
        self,
        *,
        pre_rerank_seed_ids: list[int],
        post_rerank_seed_ids: list[int],
        budget: int,
        independent_seed_ids: list[int] | None = None,
    ) -> list[int]:
        """Choose deterministic graph seeds from the configured source(s)."""
        if self._seed_strategy == "pre_rerank":
            ordered = pre_rerank_seed_ids or post_rerank_seed_ids
        elif self._seed_strategy == "dual_source":
            ordered = []
            for index in range(max(len(pre_rerank_seed_ids), len(post_rerank_seed_ids))):
                if index < len(post_rerank_seed_ids):
                    ordered.append(post_rerank_seed_ids[index])
                if index < len(pre_rerank_seed_ids):
                    ordered.append(pre_rerank_seed_ids[index])
        elif self._seed_strategy == "independent":
            ordered = independent_seed_ids or []
        elif self._seed_strategy == "combined":
            ordered = []
            for index in range(
                max(len(post_rerank_seed_ids), len(independent_seed_ids or []))
            ):
                if index < len(post_rerank_seed_ids):
                    ordered.append(post_rerank_seed_ids[index])
                if independent_seed_ids and index < len(independent_seed_ids):
                    ordered.append(independent_seed_ids[index])
        else:
            ordered = post_rerank_seed_ids

        selected: list[int] = []
        seen: set[int] = set()
        for chunk_id in ordered:
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            selected.append(chunk_id)
            if len(selected) >= budget:
                break
        return selected

    def _ranking_policy(self) -> str:
        if self._graph_only and self._seed_strategy == "independent":
            return "graph_only_independent_seed_v1"
        if self._graph_only:
            return "graph_only_seeded_by_hybrid_v2"
        if self._seed_strategy in ("independent", "combined"):
            return "hybrid_v2_plus_independent_graph_seed_v1"
        return "hybrid_v2_plus_graph_v1"

    @staticmethod
    def _graph_filters(
        request_filters: RetrievalFilters | None,
    ) -> RetrievalFilters:
        filters = request_filters or RetrievalFilters()
        excluded_roles = list(filters.exclude_roles or [])
        for role in (FileRole.TEST, FileRole.FIXTURE):
            if role not in excluded_roles:
                excluded_roles.append(role)
        return filters.model_copy(update={"exclude_roles": excluded_roles})
