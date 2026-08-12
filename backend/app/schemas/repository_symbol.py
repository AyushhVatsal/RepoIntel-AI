from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RepositorySymbolCreate(BaseModel):
    """Schema for creating a symbol."""

    repository_id: int
    file_id: int
    symbol_type: str
    name: str
    qualified_name: str
    location: dict
    symbol_metadata: dict | None = None


class RepositorySymbolResponse(RepositorySymbolCreate):
    """Schema for symbol API response."""

    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
