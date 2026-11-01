import os
from collections.abc import Callable
from dataclasses import replace
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
from tests.evals.retrieval.loader import load_retrieval_eval_cases
from tests.evals.retrieval.metrics import (
    hit_rate_at_k,
    mrr_at_k,
    ndcg_at_k,
    recall_at_k,
)
from tests.evals.retrieval.rrf_only_runner import RRFOnlyRetrievalEvalRunner
from tests.evals.retrieval.v22_fusion_runner import (
    V22FusionRetrievalEvalRunner,
)
from tests.evals.retrieval.v22_runner import V22RetrievalEvalRunner


def test_retrieval_v2_across_all_layers() -> None:
    directory = Path(__file__).parent
    positive_cases = load_retrieval_eval_cases(directory / "retrieval_v2.json")
    no_answer_cases = load_retrieval_eval_cases(
        directory / "retrieval_v2_no_answer.json"
    )
    repository_id_override = os.getenv("RETRIEVAL_EVAL_REPOSITORY_ID")
    if repository_id_override:
        repository_id = int(repository_id_override)
        positive_cases = [
            replace(case, repository_id=repository_id) for case in positive_cases
        ]
        no_answer_cases = [
            replace(case, repository_id=repository_id) for case in no_answer_cases
        ]
    cases = positive_cases + no_answer_cases
    no_answer_ids = {case.id for case in no_answer_cases}
    filters = RetrievalFilters(exclude_roles=[FileRole.TEST, FileRole.FIXTURE])

    db = SessionLocal()
    try:
        layers: list[tuple[str, Callable]] = [
            ("Dense only", DenseEvalRunner),
            ("BM25 only", BM25EvalRunner),
            ("Hybrid RRF only", RRFOnlyRetrievalEvalRunner),
            ("Cross-encoder only", V22FusionRetrievalEvalRunner),
            ("Weighted RRF + cross-encoder", V22FusionRetrievalEvalRunner),
            ("Production hybrid + conditional cross-encoder", V22RetrievalEvalRunner),
        ]
        if os.getenv("RETRIEVAL_EVAL_CANDIDATE_POOL_SWEEP") == "1":
            layers.extend(
                [
                    (
                        "Production hybrid + conditional CE, candidate pool 10",
                        lambda db: V22RetrievalEvalRunner(db, candidate_pool_k=10),
                    ),
                    (
                        "Production hybrid + conditional CE, candidate pool 20",
                        lambda db: V22RetrievalEvalRunner(db, candidate_pool_k=20),
                    ),
                ]
            )
        layers.extend(
            [
                (
                    "Production hybrid + always eligible cross-encoder",
                    lambda db: V22RetrievalEvalRunner(
                        db,
                        conditional_rerank_threshold=None,
                    ),
                ),
                ("Graph enhanced", GraphEnhancedRetrievalEvalRunner),
            ]
        )
        summaries_by_layer = {}
        latency_by_layer = {}
        rerank_count_by_layer = {}
        results_by_layer = {}

        print(
            f"\n=== Retrieval V2: {len(positive_cases)} answerable + "
            f"{len(no_answer_cases)} no-answer cases; "
            f"repository_id={positive_cases[0].repository_id} ==="
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
                        rrf_weight=(
                            0.0 if layer_name == "Cross-encoder only" else 0.90
                        ),
                        filters=filters,
                        candidate_pool_k=5,
                    )
                else:
                    result = runner.run_case(case, k=5, filters=filters)
                latencies_ms.append((perf_counter() - started) * 1000)
                results.append(result)

            assert len(results) == len(cases), layer_name
            positive_results = [
                result for result in results if result.case_id not in no_answer_ids
            ]
            summary = aggregate_results(positive_results)
            summaries_by_layer[layer_name] = summary
            results_by_layer[layer_name] = {
                result.case_id: result for result in results
            }
            no_answer_results = [
                result for result in results if result.case_id in no_answer_ids
            ]
            false_positive_at_5 = sum(
                bool(result.retrieved_file_paths) for result in no_answer_results
            ) / len(no_answer_results)
            ordered_latencies = sorted(latencies_ms)
            p95_ms = ordered_latencies[max(0, ceil(0.95 * len(ordered_latencies)) - 1)]
            latency_by_layer[layer_name] = (median(latencies_ms), p95_ms)

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
                f"unique-file@5={summary.unique_file_ratio_at_5:.3f}; "
                f"duplicate-chunk@5={summary.duplicate_chunk_rate_at_5:.3f}; "
                f"latency p50/p95={median(latencies_ms):.1f}/"
                f"{p95_ms:.1f}ms"
            )
            if layer_name.startswith("Production hybrid +"):
                reranked_count = sum(runner.reranking_decisions)
                rerank_count_by_layer[layer_name] = reranked_count
                print(
                    f"  cross-encoder applied to "
                    f"{reranked_count}/{len(runner.reranking_decisions)} "
                    f"cases ({reranked_count / len(runner.reranking_decisions):.1%})"
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
                    result for result in positive_results if result.category == category
                ]
                category_summary = aggregate_results(category_results)
                print(
                    f"  {category}: n={category_summary.total_cases}, "
                    f"Recall@5={category_summary.recall_at_5:.3f}, "
                    f"MRR@5={category_summary.mrr_at_5:.3f}, "
                    f"nDCG@5={category_summary.ndcg_at_5:.3f}"
                )

        # Measure whether relevant evidence exists before CE ranking.
        candidate_runner = RRFOnlyRetrievalEvalRunner(db)
        candidate_results = candidate_runner.run(
            positive_cases,
            k=5,
            filters=filters,
            candidate_pool_k=20,
        )
        print("\nPre-rerank RRF candidate coverage:")
        for k in (5, 10, 20):
            print(
                f"  candidate@{k}: Hit={hit_rate_at_k(candidate_results, k):.3f}; "
                f"Recall={recall_at_k(candidate_results, k):.3f}; "
                f"MRR={mrr_at_k(candidate_results, k):.3f}; "
                f"nDCG={ndcg_at_k(candidate_results, k):.3f}"
            )
        for max_per_file in (1, 2):
            diversified_results = []
            for result in candidate_results:
                counts = {}
                selected_paths = []
                for path in result.retrieved_file_paths:
                    count = counts.get(path, 0)
                    if count >= max_per_file:
                        continue
                    selected_paths.append(path)
                    counts[path] = count + 1
                    if len(selected_paths) == 5:
                        break
                expected_paths = set(result.expected_file_paths)
                first_relevant_rank = next(
                    (
                        rank
                        for rank, path in enumerate(selected_paths, start=1)
                        if path in expected_paths
                    ),
                    None,
                )
                diversified_results.append(
                    replace(
                        result,
                        retrieved_file_paths=tuple(selected_paths),
                        first_relevant_rank=first_relevant_rank,
                        relevant_results=sum(
                            path in expected_paths for path in selected_paths
                        ),
                    )
                )
            diversity_summary = aggregate_results(diversified_results)
            print(
                f"  RRF candidate file-cap@5 (max {max_per_file}/file): "
                f"Recall={diversity_summary.recall_at_5:.3f}; "
                f"MRR={diversity_summary.mrr_at_5:.3f}; "
                f"nDCG={diversity_summary.ndcg_at_5:.3f}; "
                f"unique-file={diversity_summary.unique_file_ratio_at_5:.3f}; "
                f"duplicate={diversity_summary.duplicate_chunk_rate_at_5:.3f}"
            )

        conditional_name = "Production hybrid + conditional cross-encoder"
        always_name = "Production hybrid + always eligible cross-encoder"
        conditional_summary = summaries_by_layer[conditional_name]
        always_summary = summaries_by_layer[always_name]
        assert (
            rerank_count_by_layer[conditional_name] < rerank_count_by_layer[always_name]
        ), "conditional reranking should reduce cross-encoder calls"
        for metric_name in (
            "hit_rate_at_5",
            "recall_at_5",
            "mrr_at_5",
            "ndcg_at_5",
        ):
            assert (
                getattr(conditional_summary, metric_name)
                >= getattr(always_summary, metric_name) - 0.01
            ), f"conditional reranking regressed {metric_name} by over 0.01"

        conditional_p50, conditional_p95 = latency_by_layer[conditional_name]
        always_p50, always_p95 = latency_by_layer[always_name]
        print(
            "\nConditional vs always eligible reranking: "
            f"rerank_count={rerank_count_by_layer[conditional_name]}/"
            f"{rerank_count_by_layer[always_name]}, "
            f"p50_delta={conditional_p50 - always_p50:+.1f}ms, "
            f"p95_delta={conditional_p95 - always_p95:+.1f}ms"
        )

        hybrid_results = results_by_layer["Hybrid RRF only"]
        production_results = results_by_layer[conditional_name]
        quality_regressions = []
        for case in positive_cases:
            hybrid_relevant = set(hybrid_results[case.id].retrieved_file_paths) & set(
                case.expected_file_paths
            )
            production_relevant = set(
                production_results[case.id].retrieved_file_paths
            ) & set(case.expected_file_paths)
            if not hybrid_relevant.issubset(production_relevant):
                quality_regressions.append(
                    (case, hybrid_relevant - production_relevant)
                )

        print("\nRelevant files found by Hybrid RRF but lost in production:")
        for case, lost_paths in quality_regressions:
            print(
                f"  {case.id} ({case.category}): lost={sorted(lost_paths)}; "
                f"production={production_results[case.id].retrieved_file_paths}"
            )
    finally:
        db.close()
