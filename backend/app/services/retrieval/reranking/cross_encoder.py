from sentence_transformers import CrossEncoder

from app.services.retrieval.result import RetrievalResult


class CrossEncoderReranker:
    """Rerank retrieval candidates using a cross-encoder model."""

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    ) -> None:
        self._model = CrossEncoder(model_name)

    def warmup(self) -> None:
        """Initialize tokenizer and inference kernels before live requests."""
        query = "How does repository indexing batch and embed code chunks?"
        document = (
            "repository indexing chunks embeddings retrieval candidates ranking "
            * 80
        )
        self._model.predict(
            [(query, document) for _ in range(5)],
            batch_size=16,
            show_progress_bar=False,
            processing_kwargs={
                "text": {
                    "max_length": 256,
                    "truncation": True,
                }
            },
        )

    def rerank(
        self,
        *,
        query: str,
        results: list[RetrievalResult],
        documents: dict[int, str],
        top_k: int,
    ) -> list[RetrievalResult]:
        if top_k <= 0 or not results:
            return []

        candidates = [result for result in results if result.chunk_id in documents]

        if not candidates:
            return []

        pairs = [(query, documents[result.chunk_id]) for result in candidates]

        scores = self._model.predict(
            pairs,
            batch_size=16,
            show_progress_bar=False,
            processing_kwargs={
                "text": {
                    "max_length": 256,
                    "truncation": True,
                }
            },
        )

        reranked = [
            RetrievalResult(
                chunk_id=result.chunk_id,
                score=float(score),
                dense_score=result.dense_score,
                retrieval_score=float(score),
                cross_encoder_score=float(score),
                hybrid_score=result.hybrid_score or result.score,
            )
            for result, score in zip(
                candidates,
                scores,
                strict=True,
            )
        ]

        reranked.sort(
            key=lambda result: result.score,
            reverse=True,
        )

        return reranked[:top_k]
