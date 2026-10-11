from app.services.retrieval.result import RetrievalResult


class WeightedFusion:
    """Fuse RRF and Cross-Encoder scores using normalized weighting."""

    def __init__(
        self,
        rrf_weight: float = 0.9,
        cross_encoder_weight: float = 0.1,
    ) -> None:
        if rrf_weight < 0 or cross_encoder_weight < 0:
            raise ValueError("weights must be non-negative")

        if not 0.0 <= rrf_weight <= 1.0:
            raise ValueError("rrf_weight must be between 0 and 1")

        if not 0.0 <= cross_encoder_weight <= 1.0:
            raise ValueError(
                "cross_encoder_weight must be between 0 and 1"
            )

        if abs(
            (rrf_weight + cross_encoder_weight) - 1.0
        ) > 1e-9:
            raise ValueError(
                "weights must sum to 1.0"
            )

        self.rrf_weight = rrf_weight
        self.cross_encoder_weight = cross_encoder_weight

    @staticmethod
    def _normalize(
        scores: dict[int, float],
    ) -> dict[int, float]:
        if not scores:
            return {}

        minimum = min(scores.values())
        maximum = max(scores.values())

        if maximum == minimum:
            return {
                chunk_id: 1.0
                for chunk_id in scores
            }

        return {
            chunk_id: (
                (score - minimum)
                / (maximum - minimum)
            )
            for chunk_id, score in scores.items()
        }

    def fuse(
        self,
        *,
        rrf_results: list[RetrievalResult],
        cross_encoder_results: list[RetrievalResult],
        top_k: int,
    ) -> list[RetrievalResult]:
        if top_k <= 0:
            return []

        rrf_scores = {
            result.chunk_id: result.score
            for result in rrf_results
        }

        cross_encoder_scores = {
            result.chunk_id: result.score
            for result in cross_encoder_results
        }

        normalized_rrf = self._normalize(
            rrf_scores
        )

        normalized_cross_encoder = self._normalize(
            cross_encoder_scores
        )

        chunk_ids = set(rrf_scores)

        fused: list[RetrievalResult] = []

        for chunk_id in chunk_ids:
            rrf_score = normalized_rrf.get(
                chunk_id,
                0.0,
            )

            cross_encoder_score = (
                normalized_cross_encoder.get(
                    chunk_id,
                    0.0,
                )
            )

            final_score = (
                self.rrf_weight * rrf_score
                + self.cross_encoder_weight
                * cross_encoder_score
            )

            original = next(
                result
                for result in rrf_results
                if result.chunk_id == chunk_id
            )

            fused.append(
                RetrievalResult(
                    chunk_id=chunk_id,
                    score=final_score,
                    dense_score=original.dense_score,
                    retrieval_score=final_score,
                )
            )

        fused.sort(
            key=lambda result: result.score,
            reverse=True,
        )

        return fused[:top_k]