from sqlalchemy.orm import Session

from app.services.embedding.models.embedding_config import EmbeddingConfig
from app.services.embedding.providers.local import LocalEmbeddingProvider
from app.services.embedding.service import EmbeddingService
from app.services.retrieval.candidate_filter import RetrievalCandidateFilter
from app.services.retrieval.filters import RetrievalFilters
from app.services.retrieval.fusion.rrf import RRFFusion
from app.services.retrieval.fusion.weighted import WeightedFusion
from app.services.retrieval.hydrator import RetrievalResultHydrator
from app.services.retrieval.hybrid.retriever import HybridRetriever
from app.services.retrieval.lexical.manager import BM25IndexManager
from app.services.retrieval.lexical.retriever import LexicalRetriever
from app.services.retrieval.reranking.cross_encoder import CrossEncoderReranker
from app.services.retrieval.vector_retriever import VectorRetriever

from tests.evals.retrieval.models import (
    RetrievalEvalCase,
    RetrievalEvalResult,
)


class V22FusionRetrievalEvalRunner:
    """Evaluate RRF + Cross-Encoder score fusion."""

    def __init__(self, db: Session) -> None:
        config = EmbeddingConfig()

        provider = LocalEmbeddingProvider(
            config.model
        )

        self._embedding_service = EmbeddingService(
            provider=provider,
            config=config,
        )

        vector_retriever = VectorRetriever(db)

        index_manager = BM25IndexManager()

        lexical_retriever = LexicalRetriever(
            db,
            index_manager,
        )

        self._hybrid_retriever = HybridRetriever(
            vector_retriever=vector_retriever,
            lexical_retriever=lexical_retriever,
            fusion=RRFFusion(),
            candidate_filter=RetrievalCandidateFilter(db),
        )

        self._hydrator = RetrievalResultHydrator(db)

        self._reranker = CrossEncoderReranker()

    def run_case(
        self,
        case: RetrievalEvalCase,
        *,
        k: int = 5,
        rrf_weight: float = 0.90,
        filters: RetrievalFilters | None = None,
    ) -> RetrievalEvalResult:
        query_vector = self._embedding_service.embed_query(
            case.query,
        )

        # Keep the candidate pool at 5 for this controlled experiment.
        rrf_results = self._hybrid_retriever.search(
            query_vector=query_vector,
            repository_id=case.repository_id,
            model=self._embedding_service.model_name,
            query=case.query,
            top_k=k,
            filters=filters,
        )

        hydrated = self._hydrator.hydrate(
            rrf_results,
        )

        documents = {
            result.chunk_id: result.content
            for result in hydrated
        }

        ce_results = self._reranker.rerank(
            query=case.query,
            results=rrf_results,
            documents=documents,
            top_k=k,
        )

        weighted_fusion = WeightedFusion(
            rrf_weight=rrf_weight,
            cross_encoder_weight=1.0 - rrf_weight,
        )

        fused_results = weighted_fusion.fuse(
            rrf_results=rrf_results,
            cross_encoder_results=ce_results,
            top_k=k,
        )

        final_chunks = self._hydrator.hydrate(
            fused_results,
        )

        retrieved_file_paths = tuple(
            result.file_path
            for result in final_chunks
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
        *,
        k: int = 5,
        rrf_weight: float = 0.90,
        filters: RetrievalFilters | None = None,
    ) -> list[RetrievalEvalResult]:
        return [
            self.run_case(
                case,
                k=k,
                rrf_weight=rrf_weight,
                filters=filters,
            )
            for case in cases
        ]