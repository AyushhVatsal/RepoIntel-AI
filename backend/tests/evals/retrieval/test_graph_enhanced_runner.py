import os
from pathlib import Path

from app.db.database import SessionLocal
from app.models.repository_file import FileRole
from app.services.retrieval.filters import RetrievalFilters

from tests.evals.retrieval.aggregator import aggregate_results
from tests.evals.retrieval.graph_enhanced_runner import (
    GraphEnhancedRetrievalEvalRunner,
)
from tests.evals.retrieval.loader import load_retrieval_eval_cases


def test_run_graph_enhanced_retrieval_evaluation() -> None:
    file_path = Path(__file__).parent / "retrieval_v1.json"
    cases = load_retrieval_eval_cases(file_path)

    db = SessionLocal()

    try:
        baseline_reserve = int(os.getenv("GRAPH_BASELINE_RESERVE", "0"))
        runner = GraphEnhancedRetrievalEvalRunner(
            db=db,
            baseline_reserve=baseline_reserve,
        )
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

        print("\n=== Graph-Enhanced Retrieval Evaluation ===")
        print(f"Total cases: {summary.total_cases}")
        print(f"Hit Rate@1: {summary.hit_rate_at_1:.4f}")
        print(f"Hit Rate@3: {summary.hit_rate_at_3:.4f}")
        print(f"Hit Rate@5: {summary.hit_rate_at_5:.4f}")
        print(f"Recall@5: {summary.recall_at_5:.4f}")
        print(f"Precision@5: {summary.precision_at_5:.4f}")
        print(f"MRR@5: {summary.mrr_at_5:.4f}")
        print(f"nDCG@5: {summary.ndcg_at_5:.4f}")

        for result in results:
            print(
                f"\n{result.case_id}: "
                f"first_relevant_rank={result.first_relevant_rank}"
            )
            print(f"Retrieved: {result.retrieved_file_paths}")

    finally:
        db.close()

    assert len(results) == len(cases)