from sqlalchemy.orm import Session

from app.schemas.retrieval import RetrievalRequest
from app.services.retrieval.retrieval_service import RetrievalService

from tests.evals.retrieval.models import (
    RetrievalEvalCase,
    RetrievalEvalResult,
)


class RetrievalEvalRunner:
    """Run retrieval evaluation cases against Retrieval V1."""

    def __init__(
        self,
        db: Session,
    ) -> None:
        self._retrieval_service = RetrievalService(db)

    def run_case(
        self,
        case: RetrievalEvalCase,
        k: int = 5,
    ) -> RetrievalEvalResult:
        """Run a single retrieval evaluation case."""

        request = RetrievalRequest(
            repository_id=case.repository_id,
            query=case.query,
            top_k=k,
        )

        response = self._retrieval_service.retrieve(
            request,
        )

        retrieved_file_paths = tuple(
            result.file_path
            for result in response.results
        )

        expected_file_paths = tuple(
            case.expected_file_paths
        )

        relevant_results = sum(
            file_path in expected_file_paths
            for file_path in retrieved_file_paths
        )

        first_relevant_rank = next(
            (
                rank
                for rank, file_path in enumerate(
                    retrieved_file_paths,
                    start=1,
                )
                if file_path in expected_file_paths
            ),
            None,
        )

        return RetrievalEvalResult(
            case_id=case.id,
            category=case.category,
            query=case.query,
            expected_file_paths=expected_file_paths,
            retrieved_file_paths=retrieved_file_paths,
            first_relevant_rank=first_relevant_rank,
            relevant_results=relevant_results,
        )

    def run(
        self,
        cases: list[RetrievalEvalCase],
        k: int = 5,
    ) -> list[RetrievalEvalResult]:
        """Run all retrieval evaluation cases."""

        return [
            self.run_case(
                case=case,
                k=k,
            )
            for case in cases
        ]