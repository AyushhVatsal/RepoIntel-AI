import time
from pathlib import Path

from app.db.database import SessionLocal
from app.models.repository_file import FileRole
from app.services.retrieval.filters import RetrievalFilters
from tests.evals.retrieval.loader import load_retrieval_eval_cases
from tests.evals.retrieval.v22_fusion_runner import (
    V22FusionRetrievalEvalRunner,
)


def test_v22_candidate_pool_latency() -> None:
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

        candidate_sizes = (5, 10, 20)

        for candidate_k in candidate_sizes:
            timings: list[float] = []

            print(
                f"\n\n=== Cross-Encoder "
                f"Candidate Pool: {candidate_k} ==="
            )

            for case in cases:
                query_vector = (
                    runner._embedding_service.embed_query(
                        case.query,
                    )
                )

                rrf_results = (
                    runner._hybrid_retriever.search(
                        query_vector=query_vector,
                        repository_id=case.repository_id,
                        model=(
                            runner._embedding_service.model_name
                        ),
                        query=case.query,
                        top_k=candidate_k,
                        filters=filters,
                    )
                )

                hydrated = runner._hydrator.hydrate(
                    rrf_results,
                )

                documents = {
                    result.chunk_id: result.content
                    for result in hydrated
                }

                start = time.perf_counter()

                runner._reranker.rerank(
                    query=case.query,
                    results=rrf_results,
                    documents=documents,
                    top_k=candidate_k,
                )

                elapsed = time.perf_counter() - start
                timings.append(elapsed)

                print(
                    f"{case.id}: "
                    f"{elapsed * 1000:.2f} ms"
                )

            average = (
                sum(timings)
                / len(timings)
            )

            print(
                f"\nAverage CE latency "
                f"({candidate_k} candidates): "
                f"{average * 1000:.2f} ms"
            )

            print(
                f"Min: "
                f"{min(timings) * 1000:.2f} ms"
            )

            print(
                f"Max: "
                f"{max(timings) * 1000:.2f} ms"
            )

    finally:
        db.close()