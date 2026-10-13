from __future__ import annotations

from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Any

from app.db.database import SessionLocal
from app.models.repository_file import FileRole
from app.services.retrieval.filters import RetrievalFilters

from tests.evals.retrieval.aggregator import aggregate_results
from tests.evals.retrieval.loader import load_retrieval_eval_cases
from tests.evals.retrieval.v22_fusion_runner import (
    V22FusionRetrievalEvalRunner,
)


def test_v22_candidate_pool_benchmark() -> None:
    """Benchmark candidate-pool sizes and isolate Cross-Encoder latency."""
    file_path = Path(__file__).parent / "retrieval_v1.json"
    cases = load_retrieval_eval_cases(file_path)

    if not cases:
        raise AssertionError("The frozen retrieval evaluation set is empty.")

    db = SessionLocal()

    try:
        runner = V22FusionRetrievalEvalRunner(db)

        filters = RetrievalFilters(
            exclude_roles=[FileRole.TEST, FileRole.FIXTURE],
        )

        # Record only the Cross-Encoder rerank call duration.
        rerank_times_ms: list[float] = []
        original_rerank = runner._reranker.rerank

        def timed_rerank(
            *,
            query: str,
            results: list[Any],
            documents: dict[Any, str],
            top_k: int,
        ) -> Any:
            started = perf_counter()

            try:
                return original_rerank(
                    query=query,
                    results=results,
                    documents=documents,
                    top_k=top_k,
                )
            finally:
                rerank_times_ms.append(
                    (perf_counter() - started) * 1000.0
                )

        runner._reranker.rerank = timed_rerank  # type: ignore[method-assign]

        k = 5
        pool_sizes = (5, 10, 20)
        measured_runs = 3

        measurements: dict[int, list[dict[str, float]]] = {
            pool_size: [] for pool_size in pool_sizes
        }

        # Warm up each pool size. Exclude these measurements.
        for pool_size in pool_sizes:
            runner.run(
                cases=cases,
                k=k,
                candidate_pool_k=pool_size,
                filters=filters,
            )

        # Alternate the order to reduce systematic timing bias.
        for run_index in range(measured_runs):
            ordered_sizes = (
                pool_sizes
                if run_index % 2 == 0
                else tuple(reversed(pool_sizes))
            )

            for pool_size in ordered_sizes:
                rerank_times_ms.clear()

                started = perf_counter()

                results = runner.run(
                    cases=cases,
                    k=k,
                    candidate_pool_k=pool_size,
                    filters=filters,
                )

                elapsed_ms = (perf_counter() - started) * 1000.0
                summary = aggregate_results(results)

                ce_ms_per_query = (
                    sum(rerank_times_ms) / len(cases)
                    if rerank_times_ms
                    else 0.0
                )

                measurements[pool_size].append(
                    {
                        "e2e_ms_per_query": elapsed_ms / len(cases),
                        "ce_ms_per_query": ce_ms_per_query,
                        "mrr_at_5": summary.mrr_at_5,
                        "ndcg_at_5": summary.ndcg_at_5,
                        "recall_at_5": summary.recall_at_5,
                    }
                )

        print(
            "\n=== Candidate Pool Benchmark "
            "(3 measured runs) ==="
        )
        print(
            f"{'Pool':>4}  "
            f"{'E2E median ms/query':>19}  "
            f"{'CE median ms/query':>18}  "
            f"{'MRR@5':>7}  "
            f"{'nDCG@5':>7}  "
            f"{'Recall@5':>8}"
        )

        for pool_size in pool_sizes:
            rows = measurements[pool_size]

            e2e_median = median(
                row["e2e_ms_per_query"] for row in rows
            )
            ce_median = median(
                row["ce_ms_per_query"] for row in rows
            )
            mrr = median(row["mrr_at_5"] for row in rows)
            ndcg = median(row["ndcg_at_5"] for row in rows)
            recall = median(row["recall_at_5"] for row in rows)

            print(
                f"{pool_size:>4}  "
                f"{e2e_median:>19.2f}  "
                f"{ce_median:>18.2f}  "
                f"{mrr:>7.4f}  "
                f"{ndcg:>7.4f}  "
                f"{recall:>8.4f}"
            )

            assert len(rows) == measured_runs

    finally:
        db.close()