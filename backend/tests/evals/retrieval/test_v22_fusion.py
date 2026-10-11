from pathlib import Path

from app.db.database import SessionLocal
from app.models.repository_file import FileRole
from app.services.retrieval.filters import RetrievalFilters

from tests.evals.retrieval.aggregator import aggregate_results
from tests.evals.retrieval.loader import load_retrieval_eval_cases
from tests.evals.retrieval.v22_fusion_runner import (
    V22FusionRetrievalEvalRunner,
)


def test_v22_fusion_experiment() -> None:
    file_path = (
        Path(__file__).parent
        / "retrieval_v1.json"
    )

    cases = load_retrieval_eval_cases(file_path)

    db = SessionLocal()

    try:
        runner = V22FusionRetrievalEvalRunner(db)

        filters = RetrievalFilters(
            exclude_roles=[
                FileRole.TEST,
                FileRole.FIXTURE,
            ],
        )

        for rrf_weight in (0.90, 0.75, 0.50):
            results = runner.run(
                cases,
                k=5,
                rrf_weight=rrf_weight,
                filters=filters,
            )

            summary = aggregate_results(results)

            print(
                f"\n=== RRF/CE "
                f"{rrf_weight:.0%}/"
                f"{1 - rrf_weight:.0%} ==="
            )

            print(
                f"Hit@1: {summary.hit_rate_at_1:.4f}"
            )
            print(
                f"Hit@3: {summary.hit_rate_at_3:.4f}"
            )
            print(
                f"Hit@5: {summary.hit_rate_at_5:.4f}"
            )
            print(
                f"Recall@1: {summary.recall_at_1:.4f}"
            )
            print(
                f"Recall@3: {summary.recall_at_3:.4f}"
            )
            print(
                f"Recall@5: {summary.recall_at_5:.4f}"
            )
            print(
                f"Precision@1: {summary.precision_at_1:.4f}"
            )
            print(
                f"Precision@3: {summary.precision_at_3:.4f}"
            )
            print(
                f"Precision@5: {summary.precision_at_5:.4f}"
            )
            print(
                f"MRR@5: {summary.mrr_at_5:.4f}"
            )
            print(
                f"nDCG@5: {summary.ndcg_at_5:.4f}"
            )

    finally:
        db.close()