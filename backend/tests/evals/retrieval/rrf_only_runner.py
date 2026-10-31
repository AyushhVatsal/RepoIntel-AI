from sqlalchemy.orm import Session

from app.services.embedding.models.embedding_config import EmbeddingConfig
from app.services.embedding.providers.local import LocalEmbeddingProvider
from app.services.embedding.service import EmbeddingService
from app.services.retrieval.candidate_filter import RetrievalCandidateFilter
from app.services.retrieval.filters import RetrievalFilters
from app.services.retrieval.fusion.rrf import RRFFusion
from app.services.retrieval.hybrid.retriever import HybridRetriever
from app.services.retrieval.hydrator import RetrievalResultHydrator
from app.services.retrieval.lexical.manager import BM25IndexManager
from app.services.retrieval.lexical.retriever import LexicalRetriever
from app.services.retrieval.vector_retriever import VectorRetriever
from tests.evals.retrieval.models import RetrievalEvalCase, RetrievalEvalResult
from tests.evals.retrieval.paths import normalize_path


class RRFOnlyRetrievalEvalRunner:
    """Evaluate dense + BM25 candidate fusion without reranking."""

    def __init__(self, db: Session) -> None:
        config = EmbeddingConfig()
        embedding_provider = LocalEmbeddingProvider(config.model)
        self._embedding_service = EmbeddingService(
            provider=embedding_provider,
            config=config,
        )
        self._hybrid = HybridRetriever(
            vector_retriever=VectorRetriever(db),
            lexical_retriever=LexicalRetriever(db, BM25IndexManager()),
            fusion=RRFFusion(),
            candidate_filter=RetrievalCandidateFilter(db),
        )
        self._hydrator = RetrievalResultHydrator(db)

    def run_case(
        self,
        case: RetrievalEvalCase,
        k: int = 5,
        filters: RetrievalFilters | None = None,
    ) -> RetrievalEvalResult:
        query_vector = self._embedding_service.embed_query(case.query)
        fused = self._hybrid.search(
            query_vector=query_vector,
            repository_id=case.repository_id,
            model=self._embedding_service.model_name,
            query=case.query,
            top_k=k,
            filters=filters,
        )
        hydrated = self._hydrator.hydrate(fused)
        retrieved = tuple(normalize_path(result.file_path) for result in hydrated)
        expected = tuple(normalize_path(path) for path in case.expected_file_paths)
        first_relevant_rank = next(
            (
                rank
                for rank, path in enumerate(retrieved, start=1)
                if path in expected
            ),
            None,
        )
        return RetrievalEvalResult(
            case_id=case.id,
            category=case.category,
            query=case.query,
            expected_file_paths=expected,
            retrieved_file_paths=retrieved,
            first_relevant_rank=first_relevant_rank,
            relevant_results=sum(path in expected for path in retrieved),
        )

    def run(
        self,
        cases: list[RetrievalEvalCase],
        k: int = 5,
        filters: RetrievalFilters | None = None,
    ) -> list[RetrievalEvalResult]:
        return [self.run_case(case, k=k, filters=filters) for case in cases]
