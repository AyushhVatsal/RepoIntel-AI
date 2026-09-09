from .aggregator import aggregate_results
from .models import QueryCategory, RetrievalEvalResult


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
            path in expected
            for path in retrieved
        ),
    )


def test_aggregate_results() -> None:
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

    summary = aggregate_results(results)

    assert summary.total_cases == 2

    assert summary.hit_rate_at_1 == 0.5
    assert summary.hit_rate_at_3 == 1.0
    assert summary.hit_rate_at_5 == 1.0

    assert summary.recall_at_1 == 0.5
    assert summary.recall_at_3 == 1.0
    assert summary.recall_at_5 == 1.0

    assert summary.precision_at_1 == 0.5
    assert summary.precision_at_3 == 1 / 3
    assert summary.precision_at_5 == 1 / 3

    assert summary.mrr_at_5 == 0.75