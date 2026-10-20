from pathlib import Path
from collections import Counter

from app.db.database import SessionLocal
from app.models.repository_file import FileRole
from app.services.retrieval.filters import RetrievalFilters

from tests.evals.retrieval.graph_enhanced_runner import (
    GraphEnhancedRetrievalEvalRunner,
)
from tests.evals.retrieval.loader import load_retrieval_eval_cases
from tests.evals.retrieval.v22_runner import V22RetrievalEvalRunner


def unique_in_order(paths: tuple[str, ...]) -> list[str]:
    """Deduplicate file paths while preserving their first rank."""
    return list(dict.fromkeys(paths))


def test_graph_enhanced_failure_analysis() -> None:
    cases = load_retrieval_eval_cases(
        Path(__file__).parent / "retrieval_v1.json"
    )

    filters = RetrievalFilters(
        exclude_roles=[FileRole.TEST, FileRole.FIXTURE],
    )

    db = SessionLocal()

    try:
        baseline_runner = V22RetrievalEvalRunner(db=db)
        graph_runner = GraphEnhancedRetrievalEvalRunner(db=db)

        baseline_results = baseline_runner.run(
            cases=cases,
            k=5,
            filters=filters,
        )
        graph_results = graph_runner.run(
            cases=cases,
            k=5,
            filters=filters,
        )

        baseline_by_id = {
            result.case_id: result for result in baseline_results
        }
        graph_by_id = {
            result.case_id: result for result in graph_results
        }

        baseline_losses: Counter[str] = Counter()
        graph_gains: Counter[str] = Counter()

        print("\n=== Graph Retrieval Failure Analysis ===")

        for case in cases:
            baseline = baseline_by_id[case.id]
            graph = graph_by_id[case.id]

            baseline_paths = unique_in_order(
                baseline.retrieved_file_paths
            )
            graph_paths = unique_in_order(
                graph.retrieved_file_paths
            )
            expected = set(case.expected_file_paths)

            lost_paths = [
                path for path in baseline_paths
                if path in expected and path not in graph_paths
            ]
            gained_paths = [
                path for path in graph_paths
                if path in expected and path not in baseline_paths
            ]

            baseline_losses.update(lost_paths)
            graph_gains.update(gained_paths)

            print(f"\n[{case.id}] {case.query}")
            print(f"Expected: {sorted(expected)}")
            print(
                "Baseline first relevant rank: "
                f"{baseline.first_relevant_rank}"
            )
            print(
                "Graph first relevant rank: "
                f"{graph.first_relevant_rank}"
            )
            print(f"Baseline unique paths: {baseline_paths}")
            print(f"Graph unique paths:    {graph_paths}")
            print(f"Relevant files lost:   {lost_paths}")
            print(f"Relevant files gained: {gained_paths}")

            baseline_set = set(baseline_paths)
            graph_set = set(graph_paths)

            print(
                "Baseline-only paths: "
                f"{sorted(baseline_set - graph_set)}"
            )
            print(
                "Graph-only paths: "
                f"{sorted(graph_set - baseline_set)}"
            )

        print("\n=== Aggregate Relevant-File Changes ===")
        print(f"Relevant files lost: {dict(baseline_losses)}")
        print(f"Relevant files gained: {dict(graph_gains)}")

    finally:
        db.close()
