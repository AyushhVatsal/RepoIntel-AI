from collections.abc import Sequence

from .models import RetrievalEvalResult
from math import log2

def hit_rate_at_k(
    results: Sequence[RetrievalEvalResult],
    k: int,
) -> float:
    """Calculate file-level Hit Rate@K."""

    if not results:
        return 0.0

    hits = sum(
        1
        for result in results
        if any(
            path in result.expected_file_paths
            for path in result.retrieved_file_paths[:k]
        )
    )

    return hits / len(results)


def recall_at_k(
    results: Sequence[RetrievalEvalResult],
    k: int,
) -> float:
    """Calculate average file-level Recall@K."""

    if not results:
        return 0.0

    recalls: list[float] = []

    for result in results:
        expected = set(result.expected_file_paths)

        if not expected:
            continue

        retrieved = set(
            result.retrieved_file_paths[:k]
        )

        relevant = expected.intersection(retrieved)

        recalls.append(
            len(relevant) / len(expected)
        )

    return (
        sum(recalls) / len(recalls)
        if recalls
        else 0.0
    )


def precision_at_k(
    results: Sequence[RetrievalEvalResult],
    k: int,
) -> float:
    """Calculate average file-level Precision@K."""

    if not results:
        return 0.0

    precisions: list[float] = []

    for result in results:
        retrieved = result.retrieved_file_paths[:k]

        if not retrieved:
            precisions.append(0.0)
            continue

        expected = set(result.expected_file_paths)

        relevant = sum(
            1
            for path in retrieved
            if path in expected
        )

        precisions.append(
            relevant / len(retrieved)
        )

    return sum(precisions) / len(precisions)


def mrr_at_k(
    results: Sequence[RetrievalEvalResult],
    k: int,
) -> float:
    """Calculate Mean Reciprocal Rank@K."""

    if not results:
        return 0.0

    reciprocal_ranks: list[float] = []

    for result in results:
        rank = result.first_relevant_rank

        if rank is None or rank > k:
            reciprocal_ranks.append(0.0)
        else:
            reciprocal_ranks.append(1.0 / rank)

    return (
        sum(reciprocal_ranks)
        / len(reciprocal_ranks)
    )

def ndcg_at_k(
    results: Sequence[RetrievalEvalResult],
    k: int,
) -> float:
    """Calculate average binary nDCG@K."""

    if not results:
        return 0.0

    scores: list[float] = []

    for result in results:
        expected = set(
            result.expected_file_paths,
        )

        if not expected:
            continue

        retrieved = (
            result.retrieved_file_paths[:k]
        )

        dcg = 0.0

        for rank, path in enumerate(
            retrieved,
            start=1,
        ):
            if path in expected:
                dcg += (
                    1.0 / log2(rank + 1)
                )

        ideal_relevant = min(
            len(expected),
            k,
        )

        idcg = sum(
            1.0 / log2(rank + 1)
            for rank in range(
                1,
                ideal_relevant + 1,
            )
        )

        scores.append(
            dcg / idcg
            if idcg > 0
            else 0.0
        )

    return (
        sum(scores) / len(scores)
        if scores
        else 0.0
    )