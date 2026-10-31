from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalResult:
    """A normalized retrieval result."""

    chunk_id: int
    score: float
    dense_score: float | None = None
    retrieval_score: float | None = None
    cross_encoder_score: float | None = None
    hybrid_score: float | None = None
