from collections.abc import Callable
from math import ceil
from pathlib import Path
from statistics import median
from time import perf_counter

from app.db.database import SessionLocal
from app.models.repository_file import FileRole
from app.services.retrieval.filters import RetrievalFilters
from tests.evals.retrieval.aggregator import aggregate_results
from tests.evals.retrieval.bm25_runner import BM25EvalRunner
from tests.evals.retrieval.dense_runner import DenseEvalRunner
from tests.evals.retrieval.graph_enhanced_runner import (
    GraphEnhancedRetrievalEvalRunner,
)
from tests.evals.retrieval.hybrid_only_runner import (
    HybridOnlyRetrievalEvalRunner,
)
from tests.evals.retrieval.loader import load_retrieval_eval_cases
from tests.evals.retrieval.rrf_only_runner import RRFOnlyRetrievalEvalRunner
from tests.evals.retrieval.v22_fusion_runner import (
    V22FusionRetrievalEvalRunner,
)
from tests.evals.retrieval.v22_runner import V22RetrievalEvalRunner


def test_retrieval_v2_across_all_layers() -> None:
    directory = Path(__file__).parent
    positive_cases = load_retrieval_eval_cases(
        directory / "retrieval_v2.json"
    )
    no_answer_cases = load_retrieval_eval_cases(
        directory / "retrieval_v2_no_answer.json"
    )
    cases = positive_cases + no_answer_cases
    no_answer_ids = {case.id for case in no_answer_cases}
    filters = RetrievalFilters(
        exclude_roles=[FileRole.TEST, FileRole.FIXTURE]
    )

    db = SessionLocal()
    try:
        layers: list[tuple[str, Callable]] = [
            ("Dense only", DenseEvalRunner),
            ("BM25 only", BM25EvalRunner),
            ("Hybrid RRF only", RRFOnlyRetrievalEvalRunner),
            ("Cross-encoder reranking", V22RetrievalEvalRunner),
            ("Weighted RRF + cross-encoder", V22FusionRetrievalEvalRunner),
            ("Production hybrid", HybridOnlyRetrievalEvalRunner),
            ("Graph enhanced", GraphEnhancedRetrievalEvalRunner),
        ]

        print(
            f"\n=== Retrieval V2: {len(positive_cases)} answerable + "
            f"{len(no_answer_cases)} no-answer cases ==="
        )
        for layer_name, runner_factory in layers:
            runner = runner_factory(db)
            results = []
            latencies_ms = []
            for case in cases:
                started = perf_counter()
                if isinstance(runner, V22FusionRetrievalEvalRunner):
                    result = runner.run_case(
                        case,
                        k=5,
                        rrf_weight=0.90,
                        filters=filters,
                        candidate_pool_k=5,
                    )
                else:
                    result = runner.run_case(case, k=5, filters=filters)
                latencies_ms.append((perf_counter() - started) * 1000)
                results.append(result)

            assert len(results) == len(cases), layer_name
            positive_results = [
                result
                for result in results
                if result.case_id not in no_answer_ids
            ]
            summary = aggregate_results(positive_results)
            no_answer_results = [
                result
                for result in results
                if result.case_id in no_answer_ids
            ]
            false_positive_at_5 = sum(
                bool(result.retrieved_file_paths)
                for result in no_answer_results
            ) / len(no_answer_results)
            ordered_latencies = sorted(latencies_ms)
            p95_ms = ordered_latencies[
                max(0, ceil(0.95 * len(ordered_latencies)) - 1)
            ]

            print(
                f"\n{layer_name}: Hit@1/3/5="
                f"{summary.hit_rate_at_1:.3f}/"
                f"{summary.hit_rate_at_3:.3f}/"
                f"{summary.hit_rate_at_5:.3f}; "
                f"Recall@5={summary.recall_at_5:.3f}; "
                f"Precision@5={summary.precision_at_5:.3f}; "
                f"MRR@5={summary.mrr_at_5:.3f}; "
                f"nDCG@5={summary.ndcg_at_5:.3f}; "
                f"no-answer FP@5={false_positive_at_5:.3f}; "
                f"latency p50/p95={median(latencies_ms):.1f}/"
                f"{p95_ms:.1f}ms"
            )
            if layer_name == "BM25 only":
                warm_latencies = sorted(latencies_ms[1:])
                warm_p95_ms = warm_latencies[
                    max(0, ceil(0.95 * len(warm_latencies)) - 1)
                ]
                print(
                    f"  BM25 first query (index build): "
                    f"{latencies_ms[0]:.1f}ms; warm p50/p95="
                    f"{median(latencies_ms[1:]):.1f}/"
                    f"{warm_p95_ms:.1f}ms"
                )

            for category in sorted({result.category for result in positive_results}):
                category_results = [
                    result
                    for result in positive_results
                    if result.category == category
                ]
                category_summary = aggregate_results(category_results)
                print(
                    f"  {category}: n={category_summary.total_cases}, "
                    f"Recall@5={category_summary.recall_at_5:.3f}, "
                    f"MRR@5={category_summary.mrr_at_5:.3f}, "
                    f"nDCG@5={category_summary.ndcg_at_5:.3f}"
                )
    finally:
        db.close()
