import time
from pathlib import Path

from app.db.database import SessionLocal
from app.models.repository_file import FileRole
from app.services.retrieval.filters import RetrievalFilters
from tests.evals.retrieval.loader import load_retrieval_eval_cases
from tests.evals.retrieval.v22_fusion_runner import (
    V22FusionRetrievalEvalRunner,
)


def test_v22_latency() -> None:
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

        timings: list[float] = []

        for case in cases:
            start = time.perf_counter()

            runner.run_case(
                case,
                k=5,
                rrf_weight=0.90,
                filters=filters,
            )

            elapsed = time.perf_counter() - start
            timings.append(elapsed)

            print(
                f"\n{case.id}: "
                f"{elapsed * 1000:.2f} ms"
            )

        total = sum(timings)
        average = total / len(timings)

        print("\n=== V2.2 Latency ===")
        print(
            f"Total:   {total:.3f} s"
        )
        print(
            f"Average: {average * 1000:.2f} ms"
        )
        print(
            f"Min:     {min(timings) * 1000:.2f} ms"
        )
        print(
            f"Max:     {max(timings) * 1000:.2f} ms"
        )

    finally:
        db.close()