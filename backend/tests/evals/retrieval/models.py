from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class QueryCategory(StrEnum):
    SEMANTIC = "semantic"
    STRUCTURAL = "structural"
    IDENTIFIER = "identifier"
    BEHAVIORAL = "behavioral"


@dataclass(frozen=True)
class RetrievalEvalCase:
    """A single retrieval evaluation case."""

    id: str
    category: QueryCategory
    query: str
    repository_id: int
    expected_file_paths: tuple[str, ...]


@dataclass(frozen=True)
class RetrievalEvalResult:
    """Evaluation result for a single query."""

    case_id: str
    category: QueryCategory
    query: str
    expected_file_paths: tuple[str, ...]
    retrieved_file_paths: tuple[str, ...]
    first_relevant_rank: int | None
    relevant_results: int


@dataclass(frozen=True)
class RetrievalEvalSummary:
    """Aggregated Retrieval V1 evaluation metrics."""

    total_cases: int

    recall_at_1: float
    recall_at_3: float
    recall_at_5: float

    mrr_at_5: float
    precision_at_5: float
    file_hit_at_5: float