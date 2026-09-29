from pathlib import Path

from app.db.database import SessionLocal
from app.models.repository_file import FileRole
from app.services.embedding.models.embedding_config import EmbeddingConfig
from app.services.embedding.providers.local import LocalEmbeddingProvider
from app.services.embedding.service import EmbeddingService
from app.services.retrieval.filters import RetrievalFilters
from app.services.retrieval.fusion.rrf import RRFFusion
from app.services.retrieval.hydrator import RetrievalResultHydrator
from app.services.retrieval.lexical.manager import BM25IndexManager
from app.services.retrieval.lexical.retriever import LexicalRetriever
from app.services.retrieval.result import RetrievalResult
from app.services.retrieval.vector_retriever import VectorRetriever

from tests.evals.retrieval.aggregator import aggregate_results
from tests.evals.retrieval.loader import load_retrieval_eval_cases
from tests.evals.retrieval.models import RetrievalEvalResult


def test_production_diagnostic() -> None:
    file_path = (
        Path(__file__).parent
        / "retrieval_v1.json"
    )

    cases = load_retrieval_eval_cases(file_path)

    db = SessionLocal()

    try:
        config = EmbeddingConfig()
        provider = LocalEmbeddingProvider(config.model)
        embedding_service = EmbeddingService(
            provider=provider,
            config=config,
        )

        vector_retriever = VectorRetriever(db)

        lexical_retriever = LexicalRetriever(
            db,
            BM25IndexManager(),
        )

        fusion = RRFFusion()
        hydrator = RetrievalResultHydrator(db)

        evaluation_results: list[RetrievalEvalResult] = []

        production_filters = RetrievalFilters(
            exclude_roles=[
                FileRole.TEST,
                FileRole.FIXTURE,
            ],
        )

        for case in cases:
            query_vector = embedding_service.embed_query(
                case.query,
            )

            # Dense: retrieve a larger candidate pool first.
            dense_chunks = vector_retriever.search(
                query_vector=query_vector,
                repository_id=case.repository_id,
                model=embedding_service.model_name,
                top_k=20,
                filters=None,
            )

            # Remove TEST/FIXTURE candidates after retrieval.
            dense_results = [
                RetrievalResult(
                    chunk_id=chunk.chunk_id,
                    score=chunk.similarity_score,
                    dense_score=chunk.similarity_score,
                )
                for chunk in dense_chunks
            ]

            dense_hydrated = hydrator.hydrate(
                dense_results,
            )

            allowed_dense_ids = {
                chunk.chunk_id
                for chunk in dense_hydrated
                if chunk.file_path
                and "/tests/" not in chunk.file_path.replace(
                    "\\",
                    "/",
                ).lower()
                and "/fixtures/" not in chunk.file_path.replace(
                    "\\",
                    "/",
                ).lower()
            }

            dense_results = [
                result
                for result in dense_results
                if result.chunk_id in allowed_dense_ids
            ][:5]

            # BM25: directly search the production-only corpus.
            lexical_results = lexical_retriever.search(
                repository_id=case.repository_id,
                query=case.query,
                top_k=5,
                filters=production_filters,
            )

            fused_results = fusion.fuse(
                [
                    dense_results,
                    lexical_results,
                ],
                top_k=5,
            )

            hydrated = hydrator.hydrate(
                fused_results,
            )

            retrieved_file_paths = tuple(
                result.file_path
                for result in hydrated
            )

            expected_file_paths = tuple(
                case.expected_file_paths
            )

            relevant_results = sum(
                path in expected_file_paths
                for path in retrieved_file_paths
            )

            first_relevant_rank = next(
                (
                    rank
                    for rank, path in enumerate(
                        retrieved_file_paths,
                        start=1,
                    )
                    if path in expected_file_paths
                ),
                None,
            )

            evaluation_results.append(
                RetrievalEvalResult(
                    case_id=case.id,
                    category=case.category,
                    query=case.query,
                    expected_file_paths=expected_file_paths,
                    retrieved_file_paths=retrieved_file_paths,
                    first_relevant_rank=first_relevant_rank,
                    relevant_results=relevant_results,
                )
            )

        summary = aggregate_results(
            evaluation_results,
        )

        print("\n=== Production Diagnostic ===")
        print(f"Total cases: {len(cases)}")

        print("\nHit Rate")
        print(f"@1: {summary.hit_rate_at_1:.4f}")
        print(f"@3: {summary.hit_rate_at_3:.4f}")
        print(f"@5: {summary.hit_rate_at_5:.4f}")

        print("\nRecall")
        print(f"@1: {summary.recall_at_1:.4f}")
        print(f"@3: {summary.recall_at_3:.4f}")
        print(f"@5: {summary.recall_at_5:.4f}")

        print("\nPrecision")
        print(f"@1: {summary.precision_at_1:.4f}")
        print(f"@3: {summary.precision_at_3:.4f}")
        print(f"@5: {summary.precision_at_5:.4f}")

        print("\nMRR")
        print(f"@5: {summary.mrr_at_5:.4f}")

        print("\nnDCG")
        print(f"@5: {summary.ndcg_at_5:.4f}")

    finally:
        db.close()