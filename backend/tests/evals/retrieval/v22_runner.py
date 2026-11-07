from sqlalchemy.orm import Session

from app.schemas.retrieval import RetrievalRequest
from app.services.retrieval.filters import RetrievalFilters
from app.services.retrieval.retrieval_service import RetrievalService
from tests.evals.retrieval.models import (
    RetrievalEvalCase,
    RetrievalEvalResult,
)
from tests.evals.retrieval.paths import normalize_path


class V22RetrievalEvalRunner:
    """Evaluate the production hybrid and conditional-reranking pipeline."""

    def __init__(
        self,
        db: Session,
        *,
        conditional_rerank_threshold: float | None = 0.0005,
        candidate_pool_k: int = 10,
    ) -> None:
        self._service = RetrievalService(
            db,
            conditional_rerank_threshold=conditional_rerank_threshold,
            candidate_pool_k=candidate_pool_k,
        )
        self.reranking_decisions: list[bool] = []

    def run_case(
        self,
        case: RetrievalEvalCase,
        k: int = 5,
        filters: RetrievalFilters | None = None,
    ) -> RetrievalEvalResult:
        response = self._service.retrieve(
            RetrievalRequest(
                repository_id=case.repository_id,
                query=case.query,
                top_k=k,
                filters=filters,
            )
        )
        self.reranking_decisions.append(bool(response.reranking_applied))

        retrieved_paths = tuple(
            normalize_path(result.file_path)
            for result in response.results
        )
        expected_paths = tuple(
            normalize_path(path)
            for path in case.expected_file_paths
        )

        first_relevant_rank = next(
            (
                rank
                for rank, path in enumerate(retrieved_paths, start=1)
                if path in expected_paths
            ),
            None,
        )

        return RetrievalEvalResult(
            case_id=case.id,
            category=case.category,
            query=case.query,
            expected_file_paths=expected_paths,
            retrieved_file_paths=retrieved_paths,
            first_relevant_rank=first_relevant_rank,
            relevant_results=sum(
                path in expected_paths for path in retrieved_paths
            ),
            latency_ms=response.latency_ms,
            latency_breakdown_ms=response.latency_breakdown_ms,
        )

    def run(
        self,
        cases: list[RetrievalEvalCase],
        k: int = 5,
        filters: RetrievalFilters | None = None,
    ) -> list[RetrievalEvalResult]:
        self.reranking_decisions.clear()
        return [
            self.run_case(case, k=k, filters=filters)
            for case in cases
        ]
