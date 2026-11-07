"""Compare frozen Hybrid V2 with graph-only candidates and graph augmentation.

Run from ``backend`` with ``uv run python -m
tests.evals.retrieval.benchmark_graph_v1`` after the repository graph is ready.
"""

from __future__ import annotations

import json
import os
from math import ceil
from pathlib import Path
from statistics import fmean, median

from sqlalchemy import select

from app.db.database import SessionLocal
from app.models.repository import Repository
from app.models.repository_file import FileRole
from app.services.retrieval.filters import RetrievalFilters
from app.services.retrieval.lexical.manager import get_bm25_index_manager
from tests.evals.retrieval.aggregator import aggregate_results
from tests.evals.retrieval.graph_enhanced_runner import (
    GraphEnhancedRetrievalEvalRunner,
)
from tests.evals.retrieval.loader import load_retrieval_eval_cases
from tests.evals.retrieval.v22_runner import V22RetrievalEvalRunner


def _report(name: str, results) -> dict[str, object]:
    answerable = [result for result in results if result.expected_file_paths]
    no_answer = [result for result in results if not result.expected_file_paths]
    summary = aggregate_results(answerable)
    latencies = sorted(
        result.latency_ms
        for result in results
        if result.latency_ms is not None
    )
    candidate_counts = [
        result.graph_candidate_count
        for result in results
        if result.graph_candidate_count is not None
    ]
    stage_names = sorted(
        {
            stage
            for result in results
            for stage in (result.latency_breakdown_ms or {})
            if stage.endswith("_ms")
        }
    )
    stage_latency = {}
    for stage in stage_names:
        values = sorted(
            result.latency_breakdown_ms[stage]
            for result in results
            if result.latency_breakdown_ms
            and stage in result.latency_breakdown_ms
        )
        if values:
            stage_latency[stage] = {
                "p50_ms": median(values),
                "p95_ms": values[
                    min(len(values) - 1, ceil(0.95 * len(values)) - 1)
                ],
            }
    report = {
        "name": name,
        "cases": len(results),
        "answerable_cases": summary.total_cases,
        "hit_rate_at_1": summary.hit_rate_at_1,
        "hit_rate_at_3": summary.hit_rate_at_3,
        "hit_rate_at_5": summary.hit_rate_at_5,
        "recall_at_5": summary.recall_at_5,
        "precision_at_5": summary.precision_at_5,
        "mrr_at_5": summary.mrr_at_5,
        "ndcg_at_5": summary.ndcg_at_5,
        "no_answer_false_positive_at_5": (
            sum(bool(result.retrieved_file_paths) for result in no_answer)
            / len(no_answer)
            if no_answer
            else None
        ),
        "latency_p50_ms": median(latencies) if latencies else 0.0,
        "latency_p95_ms": (
            latencies[min(len(latencies) - 1, ceil(0.95 * len(latencies)) - 1)]
            if latencies
            else 0.0
        ),
        "latency_first_case_ms": (
            results[0].latency_ms if results else None
        ),
        "latency_max_ms": max(latencies) if latencies else 0.0,
        "slowest_case_id": (
            max(
                (result for result in results if result.latency_ms is not None),
                key=lambda result: result.latency_ms,
            ).case_id
            if latencies
            else None
        ),
        "mean_graph_candidates": (
            fmean(candidate_counts) if candidate_counts else 0.0
        ),
        "stage_latency": stage_latency,
    }
    if any(result.independent_seed_candidate_count for result in results):
        seed_hits = [
            result
            for result in answerable
            if set(result.independent_seed_file_paths)
            & set(result.expected_file_paths)
        ]
        relevant_seed_paths = sum(
            len(set(result.independent_seed_file_paths)
                & set(result.expected_file_paths))
            for result in answerable
        )
        relevant_path_count = sum(
            len(set(result.expected_file_paths)) for result in answerable
        )
        report.update(
            {
                "independent_seed_hit_rate": (
                    len(seed_hits) / len(answerable) if answerable else 0.0
                ),
                "independent_seed_recall": (
                    relevant_seed_paths / relevant_path_count
                    if relevant_path_count
                    else 0.0
                ),
                "mean_independent_seeds": fmean(
                    result.independent_seed_count for result in results
                ),
                "mean_independent_seed_candidates": fmean(
                    result.independent_seed_candidate_count
                    for result in results
                ),
            }
        )
    print(json.dumps(report, sort_keys=True))
    return report


def _report_hybrid_miss_rescues(name: str, baseline, candidate) -> None:
    """Count answerable queries Hybrid V2 misses that another mode hits."""
    baseline_by_id = {result.case_id: result for result in baseline}
    candidate_by_id = {result.case_id: result for result in candidate}
    missed_ids = []
    rescued_ids = []
    for case_id, baseline_result in baseline_by_id.items():
        if not baseline_result.expected_file_paths:
            continue
        expected = set(baseline_result.expected_file_paths)
        baseline_hit = bool(expected & set(baseline_result.retrieved_file_paths))
        if baseline_hit:
            continue
        missed_ids.append(case_id)
        candidate_result = candidate_by_id.get(case_id)
        if candidate_result and expected & set(candidate_result.retrieved_file_paths):
            rescued_ids.append(case_id)
    print(
        json.dumps(
            {
                "hybrid_miss_comparison": name,
                "hybrid_missed_answerable_cases": len(missed_ids),
                "rescued_cases": len(rescued_ids),
                "rescue_rate": (
                    len(rescued_ids) / len(missed_ids) if missed_ids else None
                ),
                "rescued_case_ids": rescued_ids,
            },
            sort_keys=True,
        )
    )


def main() -> None:
    eval_path = Path(__file__).with_name("retrieval_v2.json")
    cases = load_retrieval_eval_cases(eval_path)
    no_answer_path = Path(__file__).with_name("retrieval_v2_no_answer.json")
    cases.extend(load_retrieval_eval_cases(no_answer_path))
    repository_filter = os.getenv("GRAPH_EVAL_REPOSITORY_ID")
    if repository_filter:
        repository_id = int(repository_filter)
        cases = [case for case in cases if case.repository_id == repository_id]
    if not cases:
        raise RuntimeError("The configured graph evaluation set is empty")

    filters = RetrievalFilters(
        exclude_roles=[FileRole.TEST, FileRole.FIXTURE]
    )
    candidate_multiplier = int(
        os.getenv("GRAPH_CANDIDATE_MULTIPLIER", "2")
    )
    max_hops = int(os.getenv("GRAPH_MAX_HOPS", "1"))
    graph_weight = float(os.getenv("GRAPH_FUSION_WEIGHT", "0.05"))
    combined_baseline_reserve = int(
        os.getenv("GRAPH_COMBINED_BASELINE_RESERVE", "4")
    )
    with SessionLocal() as db:
        repository_ids = sorted({case.repository_id for case in cases})
        repositories = list(
            db.scalars(
                select(Repository).where(Repository.id.in_(repository_ids))
            ).all()
        )
        print(
            json.dumps(
                {
                    "evaluation_file": eval_path.name,
                    "repository_ids": repository_ids,
                    "graph_status": {
                        str(repo.id): repo.graph_status for repo in repositories
                    },
                    "graph_build_duration_ms": {
                        str(repo.id): repo.graph_build_duration_ms
                        for repo in repositories
                    },
                    "graph_candidate_multiplier": candidate_multiplier,
                    "max_hops": max_hops,
                    "graph_weight": graph_weight,
                    "combined_baseline_reserve": combined_baseline_reserve,
                },
                sort_keys=True,
            )
        )

        # Keep the 58-case regression set untouched. This separately versioned
        # suite targets import/dependency structure and includes negative
        # expansion cases where unrelated graph context should not help.
        structural_path = Path(__file__).with_name(
            "retrieval_graph_structural_v1.json"
        )
        structural_cases = load_retrieval_eval_cases(structural_path)
        if repository_filter:
            structural_cases = [
                case
                for case in structural_cases
                if case.repository_id == int(repository_filter)
            ]
        print(
            json.dumps(
                {
                    "structural_evaluation_file": structural_path.name,
                    "structural_cases": len(structural_cases),
                    "relevance_judgments": "explicit expected file paths",
                },
                sort_keys=True,
            )
        )
        structural_baseline_results = V22RetrievalEvalRunner(db).run(
            structural_cases,
            k=5,
            filters=filters,
        )
        _report("structural_hybrid_v2", structural_baseline_results)
        structural_hybrid_seeded = GraphEnhancedRetrievalEvalRunner(
            db,
            seed_strategy="post_rerank",
            seed_budget=5,
            graph_candidate_multiplier=candidate_multiplier,
            max_hops=max_hops,
            graph_weight=graph_weight,
        ).run(structural_cases, k=5, filters=filters)
        _report("structural_hybrid_v2_plus_graph", structural_hybrid_seeded)
        _report_hybrid_miss_rescues(
            "structural_hybrid_v2_plus_graph",
            structural_baseline_results,
            structural_hybrid_seeded,
        )

        # Measure the independent path's first BM25-index build as well as
        # its query latency; later calls reuse the process cache.
        get_bm25_index_manager().clear()
        structural_independent = GraphEnhancedRetrievalEvalRunner(
            db,
            seed_strategy="independent",
            seed_budget=5,
            graph_only=True,
            graph_candidate_multiplier=candidate_multiplier,
            max_hops=max_hops,
            graph_weight=graph_weight,
        ).run(structural_cases, k=5, filters=filters)
        _report("structural_independent_graph", structural_independent)
        _report_hybrid_miss_rescues(
            "structural_independent_graph",
            structural_baseline_results,
            structural_independent,
        )
        structural_combined = GraphEnhancedRetrievalEvalRunner(
            db,
            baseline_reserve=combined_baseline_reserve,
            seed_strategy="combined",
            seed_budget=5,
            graph_candidate_multiplier=candidate_multiplier,
            max_hops=max_hops,
            graph_weight=graph_weight,
        ).run(structural_cases, k=5, filters=filters)
        _report("structural_hybrid_v2_plus_independent_graph", structural_combined)
        _report_hybrid_miss_rescues(
            "structural_hybrid_v2_plus_independent_graph",
            structural_baseline_results,
            structural_combined,
        )

        baseline_results = V22RetrievalEvalRunner(db).run(
            cases,
            k=5,
            filters=filters,
        )
        _report("hybrid_v2", baseline_results)

        hybrid_seeded_results = GraphEnhancedRetrievalEvalRunner(
            db,
            seed_strategy="post_rerank",
            seed_budget=5,
            graph_candidate_multiplier=candidate_multiplier,
            max_hops=max_hops,
            graph_weight=graph_weight,
        ).run(cases, k=5, filters=filters)
        _report("hybrid_v2_plus_graph", hybrid_seeded_results)
        _report_hybrid_miss_rescues(
            "hybrid_v2_plus_graph", baseline_results, hybrid_seeded_results
        )

        get_bm25_index_manager().clear()
        independent_results = GraphEnhancedRetrievalEvalRunner(
            db,
            seed_strategy="independent",
            seed_budget=5,
            graph_only=True,
            graph_candidate_multiplier=candidate_multiplier,
            max_hops=max_hops,
            graph_weight=graph_weight,
        ).run(cases, k=5, filters=filters)
        _report("independent_graph", independent_results)
        _report_hybrid_miss_rescues(
            "independent_graph", baseline_results, independent_results
        )

        combined_results = GraphEnhancedRetrievalEvalRunner(
            db,
            baseline_reserve=combined_baseline_reserve,
            seed_strategy="combined",
            seed_budget=5,
            graph_candidate_multiplier=candidate_multiplier,
            max_hops=max_hops,
            graph_weight=graph_weight,
        ).run(cases, k=5, filters=filters)
        _report("hybrid_v2_plus_independent_graph", combined_results)
        _report_hybrid_miss_rescues(
            "hybrid_v2_plus_independent_graph",
            baseline_results,
            combined_results,
        )


if __name__ == "__main__":
    main()
