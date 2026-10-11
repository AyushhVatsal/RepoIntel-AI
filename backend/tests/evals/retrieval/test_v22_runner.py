from pathlib import Path

from app.db.database import SessionLocal
from app.models.repository_file import FileRole
from app.services.retrieval.filters import RetrievalFilters

from tests.evals.retrieval.aggregator import aggregate_results
from tests.evals.retrieval.loader import load_retrieval_eval_cases
from tests.evals.retrieval.v22_runner import V22RetrievalEvalRunner


def test_run_v22_retrieval_evaluation() -> None:
    file_path = (
        Path(__file__).parent
        / "retrieval_v1.json"
    )

    cases = load_retrieval_eval_cases(file_path)

    db = SessionLocal()

    try:
        runner = V22RetrievalEvalRunner(db=db)

        k = 5

        results = runner.run(
            cases=cases,
            k=k,
            filters=RetrievalFilters(
                exclude_roles=[
                    FileRole.TEST,
                    FileRole.FIXTURE,
                ],
            ),
        )

        summary = aggregate_results(results)

        print("\n=== Retrieval Evaluation V2.2 ===")
        print(f"Total cases: {summary.total_cases}")

        print("\nHit Rate")
        print(f"@1: {summary.hit_rate_at_1:.4f}")
        print(f"@3: {summary.hit_rate_at_3:.4f}")
        print(f"@5: {summary.hit_rate_at_5:.4f}")

        print("\nRecall")
        print(f"@1: {summary.recall_at_1:.4f}")
        print(f"@3: {summary.recall_at_3:.4f}")
        print(f"@5: {summary.recall_at_5:.4f}")

        print("\nPrecision")
        print(f"@1: {summary.precision_at_1:.4f}")
        print(f"@3: {summary.precision_at_3:.4f}")
        print(f"@5: {summary.precision_at_5:.4f}")

        print("\nMRR")
        print(f"@5: {summary.mrr_at_5:.4f}")

        print("\nnDCG")
        print(f"@5: {summary.ndcg_at_5:.4f}")

        for result in results:
            print(
                f"\n{result.case_id}: "
                f"first_relevant_rank="
                f"{result.first_relevant_rank}"
            )
            print(
                f"Retrieved: "
                f"{result.retrieved_file_paths}"
            )

    finally:
        db.close()

    assert len(results) == len(cases)