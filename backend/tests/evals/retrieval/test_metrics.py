import pytest

from .metrics import (
    hit_rate_at_k,
    mrr_at_k,
    precision_at_k,
    recall_at_k,
    ndcg_at_k,
)
from .models import (
    QueryCategory,
    RetrievalEvalResult,
)


def make_result(
    *,
    expected: tuple[str, ...],
    retrieved: tuple[str, ...],
    first_relevant_rank: int | None,
) -> RetrievalEvalResult:
    return RetrievalEvalResult(
        case_id="test_case",
        category=QueryCategory.SEMANTIC,
        query="test query",
        expected_file_paths=expected,
        retrieved_file_paths=retrieved,
        first_relevant_rank=first_relevant_rank,
        relevant_results=sum(
            1
            for path in retrieved
            if path in expected
        ),
    )


def test_hit_rate_at_k() -> None:
    results = [
        make_result(
            expected=("a.py",),
            retrieved=("a.py", "b.py", "c.py"),
            first_relevant_rank=1,
        ),
        make_result(
            expected=("a.py",),
            retrieved=("b.py", "a.py", "c.py"),
            first_relevant_rank=2,
        ),
        make_result(
            expected=("a.py",),
            retrieved=("b.py", "c.py", "d.py"),
            first_relevant_rank=None,
        ),
    ]

    assert hit_rate_at_k(results, 1) == pytest.approx(
        1 / 3,
    )

    assert hit_rate_at_k(results, 3) == pytest.approx(
        2 / 3,
    )


def test_recall_at_k() -> None:
    results = [
        make_result(
            expected=("a.py", "b.py"),
            retrieved=("a.py", "x.py", "b.py"),
            first_relevant_rank=1,
        ),
        make_result(
            expected=("a.py", "b.py"),
            retrieved=("a.py", "x.py", "y.py"),
            first_relevant_rank=1,
        ),
    ]

    assert recall_at_k(
        results,
        3,
    ) == pytest.approx(0.75)


def test_precision_at_k() -> None:
    results = [
        make_result(
            expected=("a.py",),
            retrieved=("a.py", "b.py", "c.py"),
            first_relevant_rank=1,
        ),
        make_result(
            expected=("a.py",),
            retrieved=("b.py", "a.py", "c.py"),
            first_relevant_rank=2,
        ),
    ]

    assert precision_at_k(
        results,
        3,
    ) == pytest.approx(1 / 3)


def test_mrr_at_k() -> None:
    results = [
        make_result(
            expected=("a.py",),
            retrieved=("a.py", "b.py", "c.py"),
            first_relevant_rank=1,
        ),
        make_result(
            expected=("a.py",),
            retrieved=("b.py", "a.py", "c.py"),
            first_relevant_rank=2,
        ),
        make_result(
            expected=("a.py",),
            retrieved=("b.py", "c.py", "d.py"),
            first_relevant_rank=None,
        ),
    ]

    expected_mrr = (
        1.0
        + 0.5
        + 0.0
    ) / 3

    assert mrr_at_k(
        results,
        3,
    ) == pytest.approx(expected_mrr)

def test_ndcg_at_k() -> None:
    results = [
        make_result(
            expected=("a.py",),
            retrieved=(
                "a.py",
                "b.py",
                "c.py",
            ),
            first_relevant_rank=1,
        ),
        make_result(
            expected=("a.py",),
            retrieved=(
                "b.py",
                "a.py",
                "c.py",
            ),
            first_relevant_rank=2,
        ),
        make_result(
            expected=("a.py",),
            retrieved=(
                "b.py",
                "c.py",
                "d.py",
            ),
            first_relevant_rank=None,
        ),
    ]

    value = ndcg_at_k(
        results=results,
        k=3,
    )

    assert 0.0 <= value <= 1.0