from pydantic import BaseModel, Field


class EmbeddingConfig(BaseModel):
    """Configuration for the embedding pipeline."""

    provider: str = Field(
        default="sentence_transformers",
        min_length=1,
    )

    model: str = Field(
        default="BAAI/bge-small-en-v1.5",
        min_length=1,
    )

    dimensions: int = Field(
        default=384,
        gt=0,
    )

    batch_size: int = Field(
        default=64,
        gt=0,
    )

    max_retries: int = Field(
        default=3,
        ge=0,
    )

    max_concurrency: int = Field(
        default=1,
        gt=0,
    )