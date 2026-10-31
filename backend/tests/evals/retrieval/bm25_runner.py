from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.repository_file import RepositoryFile
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

        path_rows = self._db.execute(
            select(Chunk.id, RepositoryFile.relative_path)
            .join(RepositoryFile, Chunk.file_id == RepositoryFile.id)
            .where(Chunk.id.in_([result.chunk_id for result in results]))
        ).all() if results else []
        paths_by_chunk_id = dict(path_rows)
        retrieved_file_paths = [
            paths_by_chunk_id[result.chunk_id]
            for result in results
            if result.chunk_id in paths_by_chunk_id
        ]

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
