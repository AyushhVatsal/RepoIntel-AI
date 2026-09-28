from pydantic import BaseModel, Field


class RetrievalFilters(BaseModel):
    """Optional metadata constraints for repository retrieval."""

    language: str | None = Field(
        default=None,
        min_length=1,
    )

    file_path: str | None = Field(
        default=None,
        min_length=1,
    )

    chunk_type: str | None = Field(
        default=None,
        min_length=1,
    )

    symbol_name: str | None = Field(
        default=None,
        min_length=1,
    )