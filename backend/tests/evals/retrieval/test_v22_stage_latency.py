import time
from pathlib import Path

from app.db.database import SessionLocal
from app.models.repository_file import FileRole
from app.services.retrieval.filters import RetrievalFilters
from app.services.retrieval.fusion.weighted import WeightedFusion
from tests.evals.retrieval.loader import load_retrieval_eval_cases
from tests.evals.retrieval.v22_fusion_runner import (
    V22FusionRetrievalEvalRunner,
)


def test_v22_stage_latency() -> None:
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

        stage_totals = {
            "embedding": 0.0,
            "hybrid_retrieval": 0.0,
            "hydration": 0.0,
            "cross_encoder": 0.0,
            "weighted_fusion": 0.0,
            "final_hydration": 0.0,
        }

        for case in cases:
            print(f"\n--- {case.id} ---")

            start = time.perf_counter()

            query_vector = runner._embedding_service.embed_query(
                case.query,
            )

            elapsed = time.perf_counter() - start
            stage_totals["embedding"] += elapsed

            print(
                f"Embedding:        {elapsed * 1000:.2f} ms"
            )

            start = time.perf_counter()

            rrf_results = runner._hybrid_retriever.search(
                query_vector=query_vector,
                repository_id=case.repository_id,
                model=runner._embedding_service.model_name,
                query=case.query,
                top_k=5,
                filters=filters,
            )

            elapsed = time.perf_counter() - start
            stage_totals["hybrid_retrieval"] += elapsed

            print(
                f"Hybrid retrieval: {elapsed * 1000:.2f} ms"
            )

            start = time.perf_counter()

            hydrated = runner._hydrator.hydrate(
                rrf_results,
            )

            elapsed = time.perf_counter() - start
            stage_totals["hydration"] += elapsed

            print(
                f"Hydration:        {elapsed * 1000:.2f} ms"
            )

            documents = {
                result.chunk_id: result.content
                for result in hydrated
            }

            start = time.perf_counter()

            ce_results = runner._reranker.rerank(
                query=case.query,
                results=rrf_results,
                documents=documents,
                top_k=5,
            )

            elapsed = time.perf_counter() - start
            stage_totals["cross_encoder"] += elapsed

            print(
                f"Cross-Encoder:    {elapsed * 1000:.2f} ms"
            )

            start = time.perf_counter()

            weighted_fusion = WeightedFusion(
                rrf_weight=0.90,
                cross_encoder_weight=0.10,
            )

            fused_results = weighted_fusion.fuse(
                rrf_results=rrf_results,
                cross_encoder_results=ce_results,
                top_k=5,
            )

            elapsed = time.perf_counter() - start
            stage_totals["weighted_fusion"] += elapsed

            print(
                f"Weighted fusion:  {elapsed * 1000:.2f} ms"
            )

            start = time.perf_counter()

            runner._hydrator.hydrate(
                fused_results,
            )

            elapsed = time.perf_counter() - start
            stage_totals["final_hydration"] += elapsed

            print(
                f"Final hydration:  {elapsed * 1000:.2f} ms"
            )

        print("\n=== V2.2 Stage Latency ===")

        total = sum(stage_totals.values())

        for stage, elapsed in stage_totals.items():
            average_ms = (
                elapsed / len(cases) * 1000
            )

            percentage = (
                elapsed / total * 100
                if total > 0
                else 0.0
            )

            print(
                f"{stage:<20}"
                f"{average_ms:>9.2f} ms/query"
                f"  ({percentage:>5.1f}%)"
            )

        print("-" * 55)
        print(
            f"{'Total':<20}"
            f"{total / len(cases) * 1000:>9.2f} ms/query"
        )

    finally:
        db.close()