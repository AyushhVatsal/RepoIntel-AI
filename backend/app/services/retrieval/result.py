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
    graph_hop_count: int | None = None
    graph_path: tuple[str, ...] | None = None
    relationship_types: tuple[str, ...] | None = None
