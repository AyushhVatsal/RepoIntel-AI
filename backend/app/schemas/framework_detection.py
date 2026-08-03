from pydantic import BaseModel, Field


class FrameworkDetectionResult(BaseModel):
    """
    Represents the result of framework detection for a repository.
    """

    primary_framework: str | None = None
    frameworks: list[str] = Field(default_factory=list)