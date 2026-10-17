import time
from pathlib import Path

from app.db.database import SessionLocal
from app.models.repository_file import FileRole
from app.services.retrieval.filters import RetrievalFilters
from app.services.retrieval.reranking.cross_encoder import (
    CrossEncoderReranker,
)
from tests.evals.retrieval.loader import load_retrieval_eval_cases
from tests.evals.retrieval.v22_fusion_runner import (
    V22FusionRetrievalEvalRunner,
)
from sentence_transformers import CrossEncoder


MODELS = (
    "cross-encoder/ms-marco-MiniLM-L6-v2",
    "cross-encoder/ettin-reranker-32m-v1",
    "jinaai/jina-reranker-v1-tiny-en",
)


def test_v22_reranker_benchmark() -> None:
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

        for model_name in MODELS:
            print(
                f"\n\n{'=' * 70}\n"
                f"MODEL: {model_name}\n"
                f"{'=' * 70}"
            )

            print("\nLoading model...")


            reranker = CrossEncoder(
                model_name,
                model_kwargs={
                    "attn_implementation": "eager",
                },
            )

            timings: list[float] = []

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
                        top_k=5,
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

                documents_list = [
                    documents[result.chunk_id]
                    for result in rrf_results
                    if result.chunk_id in documents
                ]

                start = time.perf_counter()

                reranker.rank(
                    case.query,
                    documents_list,
                    top_k=min(5, len(documents_list)),
                )

                elapsed = time.perf_counter() - start
                timings.append(elapsed)

                print(
                    f"{case.id:<20}"
                    f"{elapsed * 1000:>10.2f} ms"
                )

            average = (
                sum(timings)
                / len(timings)
            )

            print("\n--- Summary ---")
            print(
                f"Average: "
                f"{average * 1000:.2f} ms/query"
            )
            print(
                f"Min:     "
                f"{min(timings) * 1000:.2f} ms"
            )
            print(
                f"Max:     "
                f"{max(timings) * 1000:.2f} ms"
            )

    finally:
        db.close()