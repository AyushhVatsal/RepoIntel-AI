from sqlalchemy.orm import Session

from app.services.embedding.models.embedding_config import EmbeddingConfig
from app.services.embedding.providers.local import LocalEmbeddingProvider
from app.services.embedding.service import EmbeddingService
from app.services.retrieval.candidate_filter import RetrievalCandidateFilter
from app.services.retrieval.fusion.rrf import RRFFusion
from app.services.retrieval.fusion.weighted import WeightedFusion
from app.services.retrieval.hydrator import RetrievalResultHydrator
from app.services.retrieval.hybrid.retriever import HybridRetriever
from app.services.retrieval.lexical.manager import BM25IndexManager
from app.services.retrieval.lexical.retriever import LexicalRetriever
from app.services.retrieval.reranking.cross_encoder import (
    CrossEncoderReranker,
)
from app.services.retrieval.vector_retriever import VectorRetriever
from app.services.retrieval.result import RetrievalResult
from app.services.retrieval.filters import RetrievalFilters

from tests.evals.retrieval.models import (
    RetrievalEvalCase,
    RetrievalEvalResult,
)


class V22RetrievalEvalRunner:
    """Run retrieval evaluation with Cross-Encoder reranking."""

    def __init__(
        self,
        db: Session,
    ) -> None:
        config = EmbeddingConfig()

        provider = LocalEmbeddingProvider(
            config.model,
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

        fusion = RRFFusion()
        candidate_filter = RetrievalCandidateFilter(db)

        self._hybrid_retriever = HybridRetriever(
            vector_retriever=vector_retriever,
            lexical_retriever=lexical_retriever,
            fusion=fusion,
            candidate_filter=candidate_filter,
        )

        self._hydrator = RetrievalResultHydrator(db)
        self._reranker = CrossEncoderReranker()
        self._weighted_fusion = WeightedFusion(
            rrf_weight=0.90,
            cross_encoder_weight=0.10,
        )

    def run_case(
        self,
        case: RetrievalEvalCase,
        k: int = 5,
        filters: RetrievalFilters | None = None,
    ) -> RetrievalEvalResult:
        """Run one V2.2 evaluation case."""

        query_vector = self._embedding_service.embed_query(
            case.query,
        )

        retrieval_results = self._hybrid_retriever.search(
            query_vector=query_vector,
            repository_id=case.repository_id,
            model=self._embedding_service.model_name,
            query=case.query,
            top_k=max(k * 2, 10),
            filters=filters,
        )

        hydrated = self._hydrator.hydrate(
            retrieval_results,
        )

        documents = {
            result.chunk_id: result.content
            for result in hydrated
        }

        reranked = self._reranker.rerank(
            query=case.query,
            results=retrieval_results,
            documents=documents,
            top_k=len(retrieval_results),
        )

        fused = self._weighted_fusion.fuse(
            rrf_results=retrieval_results,
            cross_encoder_results=reranked,
            top_k=k,
        )

        reranked_chunks = self._hydrator.hydrate(
            fused,
        )

        retrieved_file_paths = tuple(
            result.file_path
            for result in reranked_chunks
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
        """Run all V2.2 evaluation cases."""

        return [
            self.run_case(
                case=case,
                k=k,
                filters=filters,
            )
            for case in cases
        ]
