from math import isfinite

from app.services.retrieval.result import RetrievalResult


class RRFFusion:
    """Fuse ranked retrieval results using Reciprocal Rank Fusion."""

    def __init__(
        self,
        k: int = 60,
        source_weights: tuple[float, ...] | None = None,
    ) -> None:
        if k <= 0:
            raise ValueError("k must be greater than 0")
        if source_weights is not None and (
            not source_weights
            or any(not isfinite(weight) or weight < 0 for weight in source_weights)
            or sum(source_weights) <= 0
        ):
            raise ValueError("source_weights must be non-negative with a positive sum")

        self.k = k
        if source_weights is None:
            self.source_weights = None
        else:
            total_weight = sum(source_weights)
            self.source_weights = tuple(
                weight / total_weight for weight in source_weights
            )

    def fuse(
        self,
        result_lists: list[list[RetrievalResult]],
        top_k: int,
    ) -> list[RetrievalResult]:
        """Fuse multiple ranked result lists using RRF."""

        if top_k <= 0:
            return []
        if self.source_weights is not None and len(self.source_weights) != len(
            result_lists
        ):
            raise ValueError("source_weights must match the number of result lists")

        scores: dict[int, float] = {}
        dense_scores: dict[int, float | None] = {}

        for source_index, results in enumerate(result_lists):
            source_weight = (
                self.source_weights[source_index]
                if self.source_weights is not None
                else 1.0
            )
            seen_in_list: set[int] = set()
            for rank, result in enumerate(results, start=1):
                if result.chunk_id in seen_in_list:
                    continue
                seen_in_list.add(result.chunk_id)

                scores[result.chunk_id] = scores.get(
                    result.chunk_id, 0.0
                ) + source_weight / (self.k + rank)

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
                hybrid_score=rrf_score,
            )
            for chunk_id, rrf_score in ranked_results[:top_k]
        ]
