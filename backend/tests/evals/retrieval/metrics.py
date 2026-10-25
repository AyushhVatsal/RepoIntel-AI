from collections.abc import Sequence
from math import log2
from .models import RetrievalEvalResult
from .paths import normalize_path


def _expected_paths(result: RetrievalEvalResult) -> set[str]:
    """Return unique normalized expected file paths."""
    return {
        normalize_path(path)
        for path in result.expected_file_paths
    }


def _retrieved_paths(
    result: RetrievalEvalResult,
    k: int,
) -> tuple[str, ...]:
    """Normalize retrieved paths while preserving rank and duplicates."""
    return tuple(
        normalize_path(path)
        for path in result.retrieved_file_paths[:k]
    )


def hit_rate_at_k(
    results: Sequence[RetrievalEvalResult],
    k: int,
    ) -> float:
    """Calculate the fraction of cases with a relevant file in top-k."""
    if k <= 0:
        raise ValueError("k must be greater than zero")

    if not results:
        return 0.0

    hits = 0

    for result in results:
        expected = _expected_paths(result)
        retrieved = _retrieved_paths(result, k)

        if expected.intersection(retrieved):
            hits += 1

    return hits / len(results)


def recall_at_k(
    results: Sequence[RetrievalEvalResult],
    k: int,
) -> float:
    """Calculate mean file-level Recall@K."""
    if not results:
        return 0.0

    recalls: list[float] = []

    for result in results:
        expected = _expected_paths(result)

        if not expected:
            continue

        retrieved = set(_retrieved_paths(result, k))
        recalls.append(len(expected.intersection(retrieved)) / len(expected))

    return sum(recalls) / len(recalls) if recalls else 0.0


def precision_at_k(
    results: Sequence[RetrievalEvalResult],
    k: int,
) -> float:
    """Calculate mean file-level Precision@K using a fixed K denominator.

    Duplicate chunks occupy ranking positions but a file contributes
    at most one relevant result.
    """
    if not results:
        return 0.0
    if k <= 0:
        raise ValueError("k must be greater than zero")

    precisions: list[float] = []

    for result in results:
        expected = _expected_paths(result)
        retrieved = set(_retrieved_paths(result, k))

        relevant_files = expected.intersection(retrieved)
        precisions.append(len(relevant_files) / k)

    return sum(precisions) / len(precisions)


def mrr_at_k(
    results: Sequence[RetrievalEvalResult],
    k: int,
) -> float:
    """Calculate Mean Reciprocal Rank@K from original chunk positions."""
    if not results:
        return 0.0
    if k <= 0:
        raise ValueError("k must be greater than zero")

    reciprocal_ranks: list[float] = []

    for result in results:
        expected = _expected_paths(result)
        retrieved = _retrieved_paths(result, k)

        first_relevant_rank = next(
            (
                rank
                for rank, path in enumerate(retrieved, start=1)
                if path in expected
            ),
            None,
        )

        reciprocal_ranks.append(
            1.0 / first_relevant_rank
            if first_relevant_rank is not None
            else 0.0
        )

    return sum(reciprocal_ranks) / len(reciprocal_ranks)


def ndcg_at_k(
    results: Sequence[RetrievalEvalResult],
    k: int,
) -> float:
    """Calculate mean binary file-level nDCG@K.

    Each relevant file contributes gain only at its first occurrence.
    Its rank remains the original retrieved-chunk position.
    """
    if not results:
        return 0.0
    if k <= 0:
        raise ValueError("k must be greater than zero")

    scores: list[float] = []

    for result in results:
        expected = _expected_paths(result)

        if not expected:
            continue

        retrieved = _retrieved_paths(result, k)
        seen_paths: set[str] = set()
        dcg = 0.0

        for rank, path in enumerate(retrieved, start=1):
            if path in expected and path not in seen_paths:
                dcg += 1.0 / log2(rank + 1)

            seen_paths.add(path)

        ideal_relevant = min(len(expected), k)
        idcg = sum(
            1.0 / log2(rank + 1)
            for rank in range(1, ideal_relevant + 1)
        )

        scores.append(dcg / idcg if idcg else 0.0)

    return sum(scores) / len(scores) if scores else 0.0
