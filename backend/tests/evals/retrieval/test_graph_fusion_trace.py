from pathlib import Path

from app.db.database import SessionLocal
from app.models.repository_file import FileRole
from app.schemas.retrieval import RetrievalRequest
from app.services.retrieval.graph_enhanced_service import (
    GraphEnhancedRetrievalService,
)
from app.services.retrieval.result import RetrievalResult
from app.services.retrieval.filters import RetrievalFilters

from tests.evals.retrieval.loader import load_retrieval_eval_cases


def test_trace_graph_fusion() -> None:
    cases = load_retrieval_eval_cases(
        Path(__file__).parent / "retrieval_v1.json"
    )
    target_ids = {"config_001", "config_003"}
    filters = RetrievalFilters(
        exclude_roles=[FileRole.TEST, FileRole.FIXTURE]
    )

    db = SessionLocal()
    try:
        service = GraphEnhancedRetrievalService(db)

        for case in cases:
            if case.id not in target_ids:
                continue

            request = RetrievalRequest(
                repository_id=case.repository_id,
                query=case.query,
                top_k=5,
                filters=filters,
            )

            baseline = service._baseline_service.retrieve(request)

            baseline_results = [
                RetrievalResult(
                    chunk_id=result.chunk_id,
                    score=(
                        result.retrieval_score
                        if result.retrieval_score is not None
                        else (
                            result.similarity_score
                            if result.similarity_score is not None
                            else 0.0
                        )
                    ),
                    dense_score=result.similarity_score,
                    retrieval_score=result.retrieval_score,
                )
                for result in baseline.results
            ]

            graph_results = service._graph_retriever.retrieve(
                repository_id=request.repository_id,
                seed_chunk_ids=[
                    result.chunk_id for result in baseline_results
                ],
                max_hops=service._max_hops,
                top_k=min(
                    request.top_k * service._graph_candidate_multiplier,
                    service._max_graph_candidates,
                ),
            )

            fused = service._graph_fusion.fuse(
                baseline_results=baseline_results,
                graph_results=graph_results,
                top_k=request.top_k,
            )

            hydrated = service._hydrator.hydrate(fused)

            print(f"\n=== {case.id}: {case.query} ===")
            print("\nBASELINE CHUNKS")
            for result in baseline_results:
                print(
                    f"chunk={result.chunk_id} "
                    f"score={result.score:.6f}"
                )

            print("\nGRAPH CANDIDATES")
            for result in graph_results:
                print(
                    f"chunk={result.chunk_id} "
                    f"file_id={result.file_id} "
                    f"hops={result.hop_count} "
                    f"score={result.score:.6f}"
                )

            print("\nFUSED TOP 5")
            for result, chunk in zip(fused, hydrated):
                print(
                    f"chunk={result.chunk_id} "
                    f"file={chunk.file_path} "
                    f"score={result.score:.6f}"
                )
    finally:
        db.close()