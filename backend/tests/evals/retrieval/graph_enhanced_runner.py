from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.repository_file import RepositoryFile
from app.schemas.retrieval import RetrievalRequest
from app.services.retrieval.filters import RetrievalFilters
from app.services.retrieval.graph_enhanced_service import (
    GraphEnhancedRetrievalService,
)
from tests.evals.retrieval.models import (
    RetrievalEvalCase,
    RetrievalEvalResult,
)
from tests.evals.retrieval.paths import normalize_path


class GraphEnhancedRetrievalEvalRunner:
    """Evaluate retrieval enhanced with graph-based candidates."""

    def __init__(
        self,
        db: Session,
        *,
        baseline_reserve: int = -1,
        seed_strategy: Literal[
            "post_rerank",
            "pre_rerank",
            "dual_source",
            "independent",
            "combined",
        ] = "pre_rerank",
        seed_budget: int = 5,
        graph_only: bool = False,
        graph_candidate_multiplier: int = 2,
        max_hops: int = 1,
        graph_weight: float = 0.05,
    ) -> None:
        self._db = db
        self._service = GraphEnhancedRetrievalService(
            db,
            baseline_reserve=baseline_reserve,
            seed_strategy=seed_strategy,
            seed_budget=seed_budget,
            graph_only=graph_only,
            graph_candidate_multiplier=graph_candidate_multiplier,
            max_hops=max_hops,
            graph_weight=graph_weight,
        )

    def run_case(
        self,
        case: RetrievalEvalCase,
        k: int = 5,
        filters: RetrievalFilters | None = None,
    ) -> RetrievalEvalResult:
        request = RetrievalRequest(
            repository_id=case.repository_id,
            query=case.query,
            top_k=k,
            filters=filters,
        )

        response = self._service.retrieve(request)

        retrieved_paths = tuple(
            normalize_path(result.file_path)
            for result in response.results
        )

        expected_paths = tuple(
            normalize_path(path)
            for path in case.expected_file_paths
        )
        independent_seed_ids = self._service.last_independent_seed_ids
        independent_seed_paths = (
            tuple(
                normalize_path(path)
                for path in self._db.scalars(
                    select(RepositoryFile.relative_path)
                    .join(Chunk, Chunk.file_id == RepositoryFile.id)
                    .where(
                        Chunk.repository_id == case.repository_id,
                        Chunk.id.in_(independent_seed_ids),
                        RepositoryFile.repository_id == case.repository_id,
                    )
                    .distinct()
                    .order_by(RepositoryFile.relative_path)
                ).all()
            )
            if independent_seed_ids
            else ()
        )

        first_relevant_rank = next(
            (
                rank
                for rank, path in enumerate(retrieved_paths, start=1)
                if path in expected_paths
            ),
            None,
        )

        relevant_results = sum(
            path in expected_paths for path in retrieved_paths
        )

        return RetrievalEvalResult(
            case_id=case.id,
            category=case.category,
            query=case.query,
            expected_file_paths=expected_paths,
            retrieved_file_paths=retrieved_paths,
            first_relevant_rank=first_relevant_rank,
            relevant_results=relevant_results,
            latency_ms=response.latency_ms,
            graph_candidate_count=int(
                (response.latency_breakdown_ms or {}).get(
                    "graph_candidates",
                    0,
                )
            ),
            latency_breakdown_ms=response.latency_breakdown_ms,
            independent_seed_count=len(independent_seed_ids),
            independent_seed_candidate_count=(
                self._service._graph_seeder.last_candidate_count
                if self._service._seed_strategy in ("independent", "combined")
                else 0
            ),
            independent_seed_file_paths=independent_seed_paths,
        )

    def run(
        self,
        cases: list[RetrievalEvalCase],
        k: int = 5,
        filters: RetrievalFilters | None = None,
    ) -> list[RetrievalEvalResult]:
        return [
            self.run_case(case, k=k, filters=filters)
            for case in cases
        ]
