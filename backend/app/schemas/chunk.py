from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ChunkType(str, Enum):
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    IMPORT = "import"
    VARIABLE = "variable"
    TEXT = "text"


class ChunkBase(BaseModel):
    file_id: int

    chunk_index: int = Field(
        ge=0,
    )

    chunk_type: ChunkType

    content: str = Field(
        min_length=1,
    )

    start_line: int = Field(
        ge=1,
    )

    end_line: int = Field(
        ge=1,
    )

    token_count: int = Field(
        ge=0,
    )

    symbol_name: str | None = None

    qualified_name: str | None = None

    parent_symbol: str | None = None

    metadata: dict = Field(
        default_factory=dict,
    )


class ChunkCreate(ChunkBase):
    repository_id: int


class ChunkResponse(ChunkCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )