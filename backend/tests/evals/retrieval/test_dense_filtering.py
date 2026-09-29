from pathlib import Path

from app.db.database import SessionLocal

from tests.evals.retrieval.aggregator import aggregate_results
from tests.evals.retrieval.dense_runner import DenseEvalRunner
from tests.evals.retrieval.loader import load_retrieval_eval_cases
from app.models.repository_file import FileRole
from app.services.retrieval.filters import RetrievalFilters


def test_dense_unfiltered() -> None:
    file_path = (
        Path(__file__).parent
        / "retrieval_v1.json"
    )

    cases = load_retrieval_eval_cases(file_path)

    db = SessionLocal()

    try:
        runner = DenseEvalRunner(db)

        results = runner.run(
            cases=cases,
            k=5,
            filters=RetrievalFilters(
                exclude_roles=[
                    FileRole.TEST,
                    FileRole.FIXTURE,
                ],
            ), 
       )

        summary = aggregate_results(results)

        print("\n=== Dense Retrieval — TEST/FIXTURE Excluded ===")
        print(f"Total cases: {len(cases)}")

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

    finally:
        db.close()