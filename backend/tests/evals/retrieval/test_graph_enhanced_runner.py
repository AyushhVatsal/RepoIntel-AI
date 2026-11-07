import os
from pathlib import Path

import pytest

from app.db.database import SessionLocal
from app.models.repository import Repository
from app.models.repository_file import FileRole
from app.services.retrieval.filters import RetrievalFilters
from tests.evals.retrieval.aggregator import aggregate_results
from tests.evals.retrieval.graph_enhanced_runner import (
    GraphEnhancedRetrievalEvalRunner,
)
from tests.evals.retrieval.loader import load_retrieval_eval_cases
from tests.evals.retrieval.v22_runner import V22RetrievalEvalRunner


def test_run_graph_enhanced_retrieval_evaluation() -> None:
    file_path = Path(__file__).parent / "retrieval_v1.json"
    cases = load_retrieval_eval_cases(file_path)

    db = SessionLocal()

    try:
        if db.get(Repository, cases[0].repository_id) is None:
            pytest.skip(
                "The evaluation repository is absent; set "
                "RETRIEVAL_EVAL_REPOSITORY_ID to an indexed matching copy."
            )

        baseline_reserve = int(os.getenv("GRAPH_BASELINE_RESERVE", "-1"))
        filters = RetrievalFilters(
            exclude_roles=[FileRole.TEST, FileRole.FIXTURE]
        )
        baseline_results = V22RetrievalEvalRunner(db).run(
            cases=cases,
            k=5,
            filters=filters,
        )
        baseline_summary = aggregate_results(baseline_results)
        runner = GraphEnhancedRetrievalEvalRunner(
            db=db,
            baseline_reserve=baseline_reserve,
        )
        results = runner.run(
            cases=cases,
            k=5,
            filters=filters,
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
    # Graph augmentation must not fall below the pre-fix graph baseline.
    assert summary.hit_rate_at_5 >= 0.875
    assert summary.recall_at_5 >= 0.75
    assert summary.mrr_at_5 >= baseline_summary.mrr_at_5
    assert summary.ndcg_at_5 >= 0.681
