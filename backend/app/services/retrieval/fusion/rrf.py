from app.services.retrieval.result import RetrievalResult


class RRFFusion:
    """Fuse ranked retrieval results using Reciprocal Rank Fusion."""

    def __init__(self, k: int = 60) -> None:
        if k <= 0:
            raise ValueError("k must be greater than 0")

        self.k = k

    def fuse(
        self,
        result_lists: list[list[RetrievalResult]],
        top_k: int,
    ) -> list[RetrievalResult]:
        """Fuse multiple ranked result lists using RRF."""

        if top_k <= 0:
            return []

        scores: dict[int, float] = {}
        dense_scores: dict[int, float | None] = {}

        for results in result_lists:
            for rank, result in enumerate(results, start=1):
                scores[result.chunk_id] = (
                    scores.get(result.chunk_id, 0.0)
                    + 1.0 / (self.k + rank)
                )

                # Preserve the dense cosine similarity if this
                # result came from dense retrieval.
                if result.dense_score is not None:
                    dense_scores[result.chunk_id] = result.dense_score
                else:
                    dense_scores.setdefault(result.chunk_id, None)

        ranked_results = sorted(
            scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        return [
        RetrievalResult(
            chunk_id=chunk_id,
            score=rrf_score,
            dense_score=dense_scores[chunk_id],
            retrieval_score=rrf_score,
        )
        for chunk_id, rrf_score in ranked_results[:top_k]
    ]