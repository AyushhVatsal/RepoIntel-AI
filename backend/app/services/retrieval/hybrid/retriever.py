from app.models.repository_file import FileRole
from app.services.retrieval.candidate_filter import RetrievalCandidateFilter
from app.services.retrieval.filters import RetrievalFilters
from app.services.retrieval.fusion.rrf import RRFFusion
from app.services.retrieval.lexical.retriever import LexicalRetriever
from app.services.retrieval.result import RetrievalResult
from app.services.retrieval.vector_retriever import VectorRetriever


class HybridRetriever:
    """Coordinate dense and lexical retrieval with RRF fusion."""

    def __init__(
        self,
        vector_retriever: VectorRetriever,
        lexical_retriever: LexicalRetriever,
        fusion: RRFFusion,
        candidate_filter: RetrievalCandidateFilter,
    ) -> None:
        self.vector_retriever = vector_retriever
        self.lexical_retriever = lexical_retriever
        self.fusion = fusion
        self.candidate_filter = candidate_filter

    def search(
        self,
        *,
        query_vector: list[float],
        repository_id: int,
        model: str,
        query: str,
        top_k: int,
        filters: RetrievalFilters | None = None,
    ) -> list[RetrievalResult]:
        """Run dense and lexical retrieval, filter candidates, then fuse."""

        if top_k <= 0:
            return []

        dense_candidate_k = max(top_k * 4, 20)

        dense_chunks = self.vector_retriever.search(
            query_vector=query_vector,
            repository_id=repository_id,
            model=model,
            top_k=dense_candidate_k,
            filters=filters,
        )

        dense_results = [
            RetrievalResult(
                chunk_id=chunk.chunk_id,
                score=chunk.similarity_score,
                dense_score=chunk.similarity_score,
            )
            for chunk in dense_chunks
        ]

        dense_results = self.candidate_filter.exclude_roles(
            dense_results,
            roles=[
                FileRole.TEST,
                FileRole.FIXTURE,
            ],
        )

        dense_results = dense_results[:top_k]

        lexical_filters = filters or RetrievalFilters()

        if FileRole.TEST not in (lexical_filters.exclude_roles or []):
            lexical_filters = lexical_filters.model_copy(
                update={
                    "exclude_roles": [
                        *(lexical_filters.exclude_roles or []),
                        FileRole.TEST,
                        FileRole.FIXTURE,
                    ]
                }
            )

        lexical_results = self.lexical_retriever.search(
            repository_id=repository_id,
            query=query,
            top_k=top_k,
            filters=lexical_filters,
        )

        return self.fusion.fuse(
            [dense_results, lexical_results],
            top_k=top_k,
        )