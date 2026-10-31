from pathlib import Path

from app.db.database import SessionLocal
from app.models.repository_file import FileRole
from app.services.retrieval.filters import RetrievalFilters

from tests.evals.retrieval.aggregator import aggregate_results
from tests.evals.retrieval.loader import load_retrieval_eval_cases
from tests.evals.retrieval.v22_fusion_runner import (
    V22FusionRetrievalEvalRunner,
)


def test_compare_v22_fusion_weights() -> None:
    file_path = Path(__file__).parent / "retrieval_v1.json"
    cases = load_retrieval_eval_cases(file_path)

    filters = RetrievalFilters(
        exclude_roles=[
            FileRole.TEST,
            FileRole.FIXTURE,
        ],
    )

    configurations = [
        ("A: Cross-encoder only", 0.0),
        ("B: Current PR weights", 0.2),
        ("C: RRF-heavy fusion", 0.9),
    ]

    db = SessionLocal()

    try:
        runner = V22FusionRetrievalEvalRunner(db=db)

        for name, rrf_weight in configurations:
            results = runner.run(
                cases=cases,
                k=5,
                rrf_weight=rrf_weight,
                candidate_pool_k=20,
                conditional_threshold=None,
                filters=filters,
            )

            summary = aggregate_results(results)

            print(f"\n{'=' * 60}")
            print(name)
            print(f"RRF weight: {rrf_weight:.0%}")
            print(f"Cross-encoder weight: {1 - rrf_weight:.0%}")
            print(f"Hit Rate@1: {summary.hit_rate_at_1:.4f}")
            print(f"Hit Rate@3: {summary.hit_rate_at_3:.4f}")
            print(f"Hit Rate@5: {summary.hit_rate_at_5:.4f}")
            print(f"Recall@5: {summary.recall_at_5:.4f}")
            print(f"Precision@5: {summary.precision_at_5:.4f}")
            print(f"MRR@5: {summary.mrr_at_5:.4f}")
            print(f"nDCG@5: {summary.ndcg_at_5:.4f}")
            print(
                "Unique file ratio@5: "
                f"{summary.unique_file_ratio_at_5:.4f}"
            )
            print(
                "Duplicate chunk rate@5: "
                f"{summary.duplicate_chunk_rate_at_5:.4f}"
            )

            for result in results:
                print(
                    f"{result.case_id}: "
                    f"first_relevant_rank="
                    f"{result.first_relevant_rank}"
                )
                print(f"Retrieved: {result.retrieved_file_paths}")

            assert len(results) == len(cases)

    finally:
        db.close()