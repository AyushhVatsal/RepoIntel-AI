from collections.abc import Sequence
from dataclasses import dataclass

from .metrics import (
    hit_rate_at_k,
    mrr_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)
from .models import RetrievalEvalResult
from .paths import normalize_path


@dataclass(frozen=True)
class RetrievalEvalSummary:
    """Aggregated retrieval evaluation metrics."""

    total_cases: int

    hit_rate_at_1: float
    hit_rate_at_3: float
    hit_rate_at_5: float

    recall_at_1: float
    recall_at_3: float
    recall_at_5: float

    precision_at_1: float
    precision_at_3: float
    precision_at_5: float

    mrr_at_5: float
    ndcg_at_5: float
    unique_file_ratio_at_5: float
    duplicate_chunk_rate_at_5: float


def aggregate_results(
    results: Sequence[RetrievalEvalResult],
) -> RetrievalEvalSummary:
    """Aggregate retrieval evaluation results."""

    return RetrievalEvalSummary(
        total_cases=len(results),
        hit_rate_at_1=hit_rate_at_k(
            results,
            k=1,
        ),
        hit_rate_at_3=hit_rate_at_k(
            results,
            k=3,
        ),
        hit_rate_at_5=hit_rate_at_k(
            results,
            k=5,
        ),
        recall_at_1=recall_at_k(
            results,
            k=1,
        ),
        recall_at_3=recall_at_k(
            results,
            k=3,
        ),
        recall_at_5=recall_at_k(
            results,
            k=5,
        ),
        precision_at_1=precision_at_k(
            results,
            k=1,
        ),
        precision_at_3=precision_at_k(
            results,
            k=3,
        ),
        precision_at_5=precision_at_k(
            results,
            k=5,
        ),
        mrr_at_5=mrr_at_k(
            results,
            k=5,
        ),
        ndcg_at_5=ndcg_at_k(
            results,
            k=5,
        ),
        unique_file_ratio_at_5=unique_file_ratio_at_k(
            results,
            k=5,
        ),
        duplicate_chunk_rate_at_5=duplicate_chunk_rate_at_k(
            results,
            k=5,
        ),
    )


def unique_file_ratio_at_k(
    results: Sequence[RetrievalEvalResult],
    k: int,
) -> float:
    """Average unique-file ratio among the top K retrieved chunks."""
    if k <= 0:
        raise ValueError("k must be greater than 0")

    if not results:
        return 0.0

    ratios = []
    for result in results:
        retrieved = result.retrieved_file_paths[:k]

        if not retrieved:
            ratios.append(0.0)
            continue

        unique_paths = {normalize_path(path) for path in retrieved}
        ratios.append(len(unique_paths) / k)

    return sum(ratios) / len(ratios)


def duplicate_chunk_rate_at_k(
    results: Sequence[RetrievalEvalResult],
    k: int,
) -> float:
    """Average fraction of retrieved chunks duplicating a file."""
    if k <= 0:
        raise ValueError("k must be greater than 0")

    if not results:
        return 0.0

    rates = []
    for result in results:
        retrieved = result.retrieved_file_paths[:k]

        if not retrieved:
            rates.append(0.0)
            continue

        unique_paths = {normalize_path(path) for path in retrieved}
        rates.append(1.0 - len(unique_paths) / len(retrieved))

    return sum(rates) / len(rates)
