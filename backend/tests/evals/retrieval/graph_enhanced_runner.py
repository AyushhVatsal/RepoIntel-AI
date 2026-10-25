from tests.evals.retrieval.paths import normalize_path
from sqlalchemy.orm import Session

from app.schemas.retrieval import RetrievalRequest
from app.services.retrieval.filters import RetrievalFilters
from app.services.retrieval.graph_enhanced_service import (
    GraphEnhancedRetrievalService,
)

from tests.evals.retrieval.models import (
    RetrievalEvalCase,
    RetrievalEvalResult,
)


class GraphEnhancedRetrievalEvalRunner:
    """Evaluate retrieval enhanced with graph-based candidates."""

    def __init__(
        self,
        db: Session,
        *,
        baseline_reserve: int = 0,
    ) -> None:
        self._service = GraphEnhancedRetrievalService(
            db,
            baseline_reserve=baseline_reserve,
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