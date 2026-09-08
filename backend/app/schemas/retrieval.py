from pydantic import BaseModel, Field


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


class RetrievedChunk(BaseModel):
    """A chunk returned by vector retrieval."""

    chunk_id: int

    content: str

    file_path: str

    similarity_score: float


class RetrievalResponse(BaseModel):
    """Response returned by the retrieval module."""

    repository_id: int

    query: str

    results: list[RetrievedChunk]