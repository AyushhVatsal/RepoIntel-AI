from pydantic import BaseModel, Field

from app.models.repository_file import FileRole


class RetrievalFilters(BaseModel):
    language: str | None = Field(default=None, min_length=1)
    file_path: str | None = Field(default=None, min_length=1)
    chunk_type: str | None = Field(default=None, min_length=1)
    symbol_name: str | None = Field(default=None, min_length=1)
    role: FileRole | None = None
    exclude_roles: list[FileRole] | None = None