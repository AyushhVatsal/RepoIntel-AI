from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.repository import RepositoryStatus


class RepositoryBase(BaseModel):
    github_url: str = Field(
        min_length=1,
        max_length=1000,
    )


class RepositoryCreate(RepositoryBase):
    pass


class RepositoryResponse(RepositoryBase):
    id: int

    owner_id: int

    name: str

    clone_path: str

    default_branch: str | None = None

    status: RepositoryStatus

    primary_language: str | None = None

    primary_framework: str | None = None

    total_files: int

    supported_files: int

    skipped_files: int

    repository_size: int

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)