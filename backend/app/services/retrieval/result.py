from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalResult:
    """A normalized retrieval result."""

    chunk_id: int
    score: float