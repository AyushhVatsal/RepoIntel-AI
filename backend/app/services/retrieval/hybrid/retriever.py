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
        candidate_k: int | None = None,
    ) -> list[RetrievalResult]:
        """Run dense and lexical retrieval, filter candidates, then fuse."""

        if top_k <= 0:
            return []

        retrieval_k = (
            max(candidate_k, top_k)
            if candidate_k is not None
            else top_k
        )

        # Use the caller's candidate budget to bound dense and lexical work.
        dense_candidate_k = retrieval_k

        # Apply the default exclusions before top-k selection so test and
        # fixture chunks cannot consume the dense candidate budget.
        effective_filters = filters or RetrievalFilters()
        excluded_roles = list(effective_filters.exclude_roles or [])
        for role in (FileRole.TEST, FileRole.FIXTURE):
            if role not in excluded_roles:
                excluded_roles.append(role)
        effective_filters = effective_filters.model_copy(
            update={"exclude_roles": excluded_roles}
        )

        # 1. Dense vector retrieval.
        dense_chunks = self.vector_retriever.search(
            query_vector=query_vector,
            repository_id=repository_id,
            model=model,
            top_k=dense_candidate_k,
            filters=effective_filters,
        )

        dense_results = [
            RetrievalResult(
                chunk_id=chunk.chunk_id,
                score=chunk.similarity_score,
                dense_score=chunk.similarity_score,
            )
            for chunk in dense_chunks
        ]

        # 2. BM25 lexical retrieval.
        lexical_results = self.lexical_retriever.search(
            repository_id=repository_id,
            query=query,
            top_k=dense_candidate_k,
            filters=effective_filters,
        )
        # Filter both candidate lists in one metadata lookup. The database role
        # can be stale, so the candidate filter also checks conventional paths.
        allowed_ids = {
            result.chunk_id
            for result in self.candidate_filter.exclude_roles(
                dense_results + lexical_results,
                roles=[
                    FileRole.TEST,
                    FileRole.FIXTURE,
                ],
            )
        }
        dense_results = [
            result for result in dense_results if result.chunk_id in allowed_ids
        ][:dense_candidate_k]
        lexical_results = [
            result for result in lexical_results if result.chunk_id in allowed_ids
        ]

        # 3. Fuse dense and lexical results using RRF.
        fuse_top_k = retrieval_k if candidate_k is not None else top_k
        return self.fusion.fuse(
            [dense_results, lexical_results],
            top_k=fuse_top_k,
        )
