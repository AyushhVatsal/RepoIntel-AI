from pathlib import Path

from app.db.database import SessionLocal
from app.models.repository_file import FileRole
from app.services.retrieval.filters import RetrievalFilters
from app.services.retrieval.hydrator import RetrievalResultHydrator
from app.services.retrieval.reranking.cross_encoder import (
    CrossEncoderReranker,
)

from tests.evals.retrieval.loader import load_retrieval_eval_cases
from tests.evals.retrieval.v22_runner import V22RetrievalEvalRunner


def main() -> None:
    file_path = (
        Path(__file__).parent
        / "retrieval_v1.json"
    )

    cases = load_retrieval_eval_cases(file_path)

    db = SessionLocal()

    try:
        runner = V22RetrievalEvalRunner(db=db)

        reranker = CrossEncoderReranker()

        # Access the components already constructed by V22 runner.
        hybrid = runner._hybrid_retriever
        embedding_service = runner._embedding_service
        hydrator = runner._hydrator

        filters = RetrievalFilters(
            exclude_roles=[
                FileRole.TEST,
                FileRole.FIXTURE,
            ],
        )

        for case in cases:
            query_vector = embedding_service.embed_query(
                case.query,
            )

            # V2.1 RRF results.
            rrf_results = hybrid.search(
                query_vector=query_vector,
                repository_id=case.repository_id,
                model=embedding_service.model_name,
                query=case.query,
                top_k=5,
                filters=filters,
            )

            hydrated = hydrator.hydrate(rrf_results)

            documents = {
                result.chunk_id: result.content
                for result in hydrated
            }

            # V2.2 Cross-Encoder results.
            reranked = reranker.rerank(
                query=case.query,
                results=rrf_results,
                documents=documents,
                top_k=5,
            )

            rrf_chunks = hydrator.hydrate(rrf_results)
            reranked_chunks = hydrator.hydrate(reranked)

            expected = set(case.expected_file_paths)

            print("\n" + "=" * 80)
            print(f"CASE: {case.id}")
            print(f"QUERY: {case.query}")
            print(f"EXPECTED: {case.expected_file_paths}")

            print("\nV2.1 RRF:")
            for rank, chunk in enumerate(
                rrf_chunks,
                start=1,
            ):
                marker = (
                    " <-- RELEVANT"
                    if chunk.file_path in expected
                    else ""
                )

                result = rrf_results[rank - 1]

                print(
                    f"{rank}. "
                    f"chunk={result.chunk_id} "
                    f"rrf={result.retrieval_score:.6f} "
                    f"path={chunk.file_path}"
                    f"{marker}"
                )

            print("\nV2.2 CROSS-ENCODER:")

            for rank, chunk in enumerate(
                reranked_chunks,
                start=1,
            ):
                marker = (
                    " <-- RELEVANT"
                    if chunk.file_path in expected
                    else ""
                )

                result = reranked[rank - 1]

                print(
                    f"{rank}. "
                    f"chunk={result.chunk_id} "
                    f"score={result.score:.6f} "
                    f"path={chunk.file_path}"
                    f"{marker}"
                )

    finally:
        db.close()


if __name__ == "__main__":
    main()