from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EmbeddingResult(BaseModel):
    """Result produced after embedding a chunk."""

    model_config = ConfigDict(frozen=True)

    repository_id: int = Field(gt=0)
    file_id: int = Field(gt=0)
    chunk_index: int = Field(ge=0)

    vector: tuple[float, ...]

    model: str = Field(min_length=1)

    dimensions: int = Field(gt=0)

    cached: bool = False