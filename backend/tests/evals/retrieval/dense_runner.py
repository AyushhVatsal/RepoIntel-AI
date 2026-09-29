from sqlalchemy.orm import Session

from app.models.repository_file import FileRole
from app.schemas.retrieval import RetrievalRequest
from app.services.embedding.models.embedding_config import EmbeddingConfig
from app.services.embedding.providers.local import LocalEmbeddingProvider
from app.services.embedding.service import EmbeddingService
from app.services.retrieval.filters import RetrievalFilters
from app.services.retrieval.hydrator import RetrievalResultHydrator
from app.services.retrieval.result import RetrievalResult
from app.services.retrieval.vector_retriever import VectorRetriever

from tests.evals.retrieval.models import (
    RetrievalEvalCase,
    RetrievalEvalResult,
)


class DenseEvalRunner:
    """Run retrieval evaluation against Dense retrieval only."""

    def __init__(self, db: Session) -> None:
        config = EmbeddingConfig()
        provider = LocalEmbeddingProvider(config.model)

        self._embedding_service = EmbeddingService(
            provider=provider,
            config=config,
        )
        self._vector_retriever = VectorRetriever(db)
        self._hydrator = RetrievalResultHydrator(db)

    def run_case(
        self,
        case: RetrievalEvalCase,
        k: int = 5,
        filters: RetrievalFilters | None = None,
    ) -> RetrievalEvalResult:
        query_vector = self._embedding_service.embed_query(
            case.query,
        )

        dense_chunks = self._vector_retriever.search(
            query_vector=query_vector,
            repository_id=case.repository_id,
            model=self._embedding_service.model_name,
            top_k=k,
            filters=filters,
        )

        retrieval_results = [
            RetrievalResult(
                chunk_id=chunk.chunk_id,
                score=chunk.similarity_score,
                dense_score=chunk.similarity_score,
            )
            for chunk in dense_chunks
        ]

        results = self._hydrator.hydrate(
            retrieval_results,
        )

        retrieved_file_paths = tuple(
            result.file_path
            for result in results
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