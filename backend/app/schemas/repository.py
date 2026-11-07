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

    indexing_progress: int

    indexing_stage: str

    indexing_processed_files: int

    indexing_total_files: int

    indexing_error: str | None = None

    graph_status: str = "not_built"

    graph_built_at: datetime | None = None

    graph_build_duration_ms: float | None = None

    graph_error: str | None = None

    primary_language: str | None = None

    primary_framework: str | None = None

    total_files: int

    supported_files: int

    skipped_files: int

    repository_size: int

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
