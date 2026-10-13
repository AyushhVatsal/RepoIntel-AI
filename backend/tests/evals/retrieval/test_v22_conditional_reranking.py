from pathlib import Path

from app.db.database import SessionLocal
from app.models.repository_file import FileRole
from app.services.retrieval.filters import RetrievalFilters
from tests.evals.retrieval.aggregator import aggregate_results
from tests.evals.retrieval.loader import load_retrieval_eval_cases
from tests.evals.retrieval.v22_fusion_runner import (
    V22FusionRetrievalEvalRunner,
)


def test_v22_conditional_reranking() -> None:
    file_path = Path(__file__).parent / "retrieval_v1.json"
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

        from statistics import median
        from time import perf_counter

        # Warm the embedding, database, and model paths before timing.
        runner.run(
            cases,
            k=5,
            rrf_weight=0.90,
            filters=filters,
            conditional_threshold=None,
        )

        original_rerank = runner._reranker.rerank
        rerank_calls = [0]

        def counted_rerank(*, query, results, documents, top_k):
            rerank_calls[0] += 1
            return original_rerank(
                query=query,
                results=results,
                documents=documents,
                top_k=top_k,
            )

        runner._reranker.rerank = counted_rerank

        # Three configurations, measured three times each.
        thresholds = [0.0, 0.001, None]
        measurements = {threshold: [] for threshold in thresholds}

        # Rotate the order each round to reduce ordering bias.
        for round_index in range(3):
            round_thresholds = thresholds[round_index:] + thresholds[:round_index]

            for threshold in round_thresholds:
                rerank_calls[0] = 0

                start = perf_counter()
                results = runner.run(
                    cases,
                    k=5,
                    rrf_weight=0.90,
                    filters=filters,
                    conditional_threshold=threshold,
                )
                elapsed_ms = (perf_counter() - start) * 1000

                summary = aggregate_results(results)

                measurements[threshold].append(
                    {
                        "latency_ms": elapsed_ms / len(cases),
                        "rerank_rate": rerank_calls[0] / len(cases) * 100,
                        "mrr": summary.mrr_at_5,
                        "ndcg": summary.ndcg_at_5,
                        "recall": summary.recall_at_5,
                    }
                )

        print("\n=== Conditional Reranking: 3 Repeated Runs ===")
        print(
            f"{'Strategy':>12} {'Median ms':>10} "
            f"{'Reranked':>10} {'MRR@5':>8} "
            f"{'nDCG@5':>8} {'Recall@5':>9}"
        )

        for threshold in thresholds:
            runs = measurements[threshold]
            label = "always" if threshold is None else f"{threshold:.3f}"

            print(
                f"{label:>12} "
                f"{median(r['latency_ms'] for r in runs):10.2f} "
                f"{median(r['rerank_rate'] for r in runs):9.1f}% "
                f"{median(r['mrr'] for r in runs):8.4f} "
                f"{median(r['ndcg'] for r in runs):8.4f} "
                f"{median(r['recall'] for r in runs):9.4f}"
            )

        assert len(cases) > 0

    finally:
        db.close()
