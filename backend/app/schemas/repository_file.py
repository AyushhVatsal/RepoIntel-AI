from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.repository_file import (
    FileCategory,
    LanguageSupportTier,
)


class RepositoryFileBase(BaseModel):
    path: str
    relative_path: str
    filename: str
    extension: str | None = None
    language: str | None = None

    category: FileCategory
    support_tier: LanguageSupportTier

    size: int
    sha256_hash: str | None = None
    is_binary: bool

    last_modified: datetime | None = None


class RepositoryFileCreate(RepositoryFileBase):
    repository_id: int


class RepositoryFileResponse(RepositoryFileBase):
    id: int
    repository_id: int

    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )