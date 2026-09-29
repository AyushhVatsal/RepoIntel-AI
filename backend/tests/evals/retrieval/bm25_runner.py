from sqlalchemy.orm import Session

from app.crud.chunk import chunk_crud
from app.crud.repository_file import repository_file_crud
from app.services.retrieval.filters import RetrievalFilters
from app.services.retrieval.lexical.manager import BM25IndexManager
from app.services.retrieval.lexical.retriever import LexicalRetriever

from tests.evals.retrieval.models import (
    RetrievalEvalCase,
    RetrievalEvalResult,
)


class BM25EvalRunner:
    """Run retrieval evaluation against BM25 only."""

    def __init__(self, db: Session) -> None:
        self._db = db

        index_manager = BM25IndexManager()

        self._retriever = LexicalRetriever(
            db,
            index_manager,
        )

    def run_case(
        self,
        case: RetrievalEvalCase,
        k: int = 5,
        filters: RetrievalFilters | None = None,
    ) -> RetrievalEvalResult:
        results = self._retriever.search(
            repository_id=case.repository_id,
            query=case.query,
            top_k=k,
            filters=filters,
        )

        retrieved_file_paths: list[str] = []

        for result in results:
            chunk = chunk_crud.get(
                self._db,
                result.chunk_id,
            )

            if chunk is None:
                continue

            repository_file = repository_file_crud.get(
                self._db,
                chunk.file_id,
            )

            retrieved_file_paths.append(
                repository_file.relative_path
                if repository_file is not None
                else "unknown"
            )

        retrieved_file_paths_tuple = tuple(
            retrieved_file_paths
        )

        expected_file_paths = tuple(
            case.expected_file_paths
        )

        relevant_results = sum(
            file_path in expected_file_paths
            for file_path in retrieved_file_paths_tuple
        )

        first_relevant_rank = next(
            (
                rank
                for rank, file_path in enumerate(
                    retrieved_file_paths_tuple,
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
            retrieved_file_paths=retrieved_file_paths_tuple,
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
            self.run_case(
                case=case,
                k=k,
                filters=filters,
            )
            for case in cases
        ]