from pydantic import BaseModel, Field

from app.services.retrieval.filters import RetrievalFilters


class RetrievalRequest(BaseModel):
    """Request for retrieving relevant repository chunks."""

    repository_id: int = Field(
        ...,
        description="ID of the repository to search.",
        gt=0,
    )

    query: str = Field(
        ...,
        description="Natural language query used for retrieval.",
        min_length=1,
    )

    top_k: int = Field(
        default=5,
        description="Maximum number of relevant chunks to retrieve.",
        ge=1,
        le=20,
    )

    filters: RetrievalFilters | None = Field(
        default=None,
        description="Optional metadata filters for retrieval.",
    )


class RetrievedChunk(BaseModel):
    """A chunk returned by retrieval."""

    chunk_id: int

    content: str

    file_path: str

    similarity_score: float | None = None

    hybrid_score: float | None = None

    cross_encoder_score: float | None = None

    retrieval_score: float | None = None

class RetrievalResponse(BaseModel):
    """Response returned by the retrieval module."""

    repository_id: int

    query: str

    latency_ms: float | None = None

    reranking_applied: bool | None = None

    reranking_skip_reason: str | None = None

    ranking_policy: str | None = None

    latency_breakdown_ms: dict[str, float] | None = None

    results: list[RetrievedChunk]
