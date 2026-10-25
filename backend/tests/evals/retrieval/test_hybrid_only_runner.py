
from pathlib import Path

from app.db.database import SessionLocal
from app.models.repository_file import FileRole
from app.services.retrieval.filters import RetrievalFilters

from tests.evals.retrieval.aggregator import aggregate_results
from tests.evals.retrieval.hybrid_only_runner import (
    HybridOnlyRetrievalEvalRunner,
)
from tests.evals.retrieval.loader import load_retrieval_eval_cases


def test_run_hybrid_only_retrieval_evaluation() -> None:
    file_path = Path(__file__).parent / "retrieval_v1.json"
    cases = load_retrieval_eval_cases(file_path)

    db = SessionLocal()

    try:
        runner = HybridOnlyRetrievalEvalRunner(db)
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

        print("\n=== Hybrid-Only Retrieval Evaluation ===")
        print(f"Total cases: {summary.total_cases}")
        print(f"Hit Rate@1: {summary.hit_rate_at_1:.4f}")
        print(f"Hit Rate@3: {summary.hit_rate_at_3:.4f}")
        print(f"Hit Rate@5: {summary.hit_rate_at_5:.4f}")
        print(f"Recall@5: {summary.recall_at_5:.4f}")
        print(f"Precision@5: {summary.precision_at_5:.4f}")
        print(f"MRR@5: {summary.mrr_at_5:.4f}")
        print(f"nDCG@5: {summary.ndcg_at_5:.4f}")
        print(
            f"Unique-file ratio@5: "
            f"{summary.unique_file_ratio_at_5:.4f}"
        )
        print(
            f"Duplicate-chunk rate@5: "
            f"{summary.duplicate_chunk_rate_at_5:.4f}"
        )

        for result in results:
            print(
                f"\n{result.case_id}: "
                f"first_relevant_rank={result.first_relevant_rank}"
            )
            print(f"Retrieved: {result.retrieved_file_paths}")

    finally:
        db.close()

    assert len(results) == len(cases)
