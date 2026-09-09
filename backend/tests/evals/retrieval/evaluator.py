from app.schemas.retrieval import RetrievalRequest
from app.services.retrieval.retrieval_service import RetrievalService

from .models import (
    RetrievalEvalCase,
    RetrievalEvalResult,
)


class RetrievalEvaluator:
    """Evaluates Retrieval V1 against ground-truth cases."""

    def __init__(
        self,
        retrieval_service: RetrievalService,
    ) -> None:
        self._retrieval_service = retrieval_service

    def evaluate_case(
        self,
        case: RetrievalEvalCase,
        top_k: int = 5,
    ) -> RetrievalEvalResult:
        """Evaluate a single retrieval case."""

        request = RetrievalRequest(
            repository_id=case.repository_id,
            query=case.query,
            top_k=top_k,
        )

        response = self._retrieval_service.retrieve(request)

        retrieved_file_paths = self._deduplicate_paths(
            tuple(
                self._normalize_path(result.file_path)
                for result in response.results
            )
        )

        expected_file_paths = tuple(
            self._normalize_path(path)
            for path in case.expected_file_paths
        )

        expected_paths = set(expected_file_paths)

        relevant_ranks = [
            rank
            for rank, path in enumerate(
                retrieved_file_paths,
                start=1,
            )
            if path in expected_paths
        ]

        first_relevant_rank = (
            relevant_ranks[0]
            if relevant_ranks
            else None
        )

        return RetrievalEvalResult(
            case_id=case.id,
            category=case.category,
            query=case.query,
            expected_file_paths=expected_file_paths,
            retrieved_file_paths=retrieved_file_paths,
            first_relevant_rank=first_relevant_rank,
            relevant_results=len(relevant_ranks),
        )

    @staticmethod
    def _normalize_path(
        path: str,
    ) -> str:
        """Normalize paths for consistent comparison."""

        return path.replace("\\", "/").lower()

    @staticmethod
    def _deduplicate_paths(
        paths: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Remove duplicate paths while preserving ranking order."""

        seen: set[str] = set()
        unique_paths: list[str] = []

        for path in paths:
            if path not in seen:
                seen.add(path)
                unique_paths.append(path)

        return tuple(unique_paths)