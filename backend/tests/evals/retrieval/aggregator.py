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
    )