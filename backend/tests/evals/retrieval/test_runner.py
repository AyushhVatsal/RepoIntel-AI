from pathlib import Path

from app.db.database import SessionLocal

from tests.evals.retrieval.loader import (
    load_retrieval_eval_cases,
)
from tests.evals.retrieval.runner import (
    RetrievalEvalRunner,
)

from .aggregator import aggregate_results


def test_run_retrieval_evaluation() -> None:
    file_path = (
        Path(__file__).parent
        / "retrieval_v1.json"
    )

    cases = load_retrieval_eval_cases(
        file_path,
    )

    db = SessionLocal()

    try:
        runner = RetrievalEvalRunner(
            db=db,
        )

        k = 5

        results = runner.run(
            cases=cases,
            k=k,
        )

        summary = aggregate_results(results)

        for result in results:
            expected = set(result.expected_file_paths)
            retrieved = set(result.retrieved_file_paths)

            missing = expected - retrieved

            if missing:
                print("\n--- Retrieval Miss ---")
                print(f"Case: {result.case_id}")
                print(f"Query: {result.query}")
                print(
                    f"Expected: "
                    f"{result.expected_file_paths}"
                )
                print(
                    f"Retrieved: "
                    f"{result.retrieved_file_paths}"
                )
                print(
                    f"First relevant rank: "
                    f"{result.first_relevant_rank}"
                )
                print(
                    f"Missing: {tuple(missing)}"
                )

        print("\n=== Retrieval Evaluation V1 ===")
        print(
            f"Total cases: {summary.total_cases}"
        )

        print("\nHit Rate")
        print(
            f"@1: {summary.hit_rate_at_1:.4f}"
        )
        print(
            f"@3: {summary.hit_rate_at_3:.4f}"
        )
        print(
            f"@5: {summary.hit_rate_at_5:.4f}"
        )

        print("\nRecall")
        print(
            f"@1: {summary.recall_at_1:.4f}"
        )
        print(
            f"@3: {summary.recall_at_3:.4f}"
        )
        print(
            f"@5: {summary.recall_at_5:.4f}"
        )

        print("\nPrecision")
        print(
            f"@1: {summary.precision_at_1:.4f}"
        )
        print(
            f"@3: {summary.precision_at_3:.4f}"
        )
        print(
            f"@5: {summary.precision_at_5:.4f}"
        )

        print("\nMRR")
        print(
            f"@5: {summary.mrr_at_5:.4f}"
        )
        
        print("\nnDCG")
        print(f"@5: {summary.ndcg_at_5:.4f}")

    finally:
        db.close()

    assert len(results) == len(cases)

    for result in results:
        assert result.case_id
        assert result.query
        assert (
            len(result.retrieved_file_paths)
            <= k
        )