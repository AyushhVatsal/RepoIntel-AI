from time import perf_counter
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps.db import get_db
from app.schemas.retrieval import (
    RetrievalRequest,
    RetrievalResponse,
)
from app.services.retrieval.graph_enhanced_service import (
    GraphEnhancedRetrievalService,
)
from app.services.retrieval.retrieval_service import (
    create_production_retrieval_service,
)

router = APIRouter(
    prefix="/retrieval",
    tags=["Retrieval"],
)


@router.post(
    "/search",
    response_model=RetrievalResponse,
)
def search_repository(
    request: RetrievalRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> RetrievalResponse:
    """Retrieve relevant chunks from an indexed repository."""

    started = perf_counter()
    retrieval_service = create_production_retrieval_service(db)
    response = retrieval_service.retrieve(request)
    api_latency_ms = (perf_counter() - started) * 1000
    latency_breakdown = dict(response.latency_breakdown_ms or {})
    service_latency_ms = latency_breakdown.get("service_total_ms", 0.0)
    latency_breakdown["service_initialization_ms"] = max(
        0.0,
        api_latency_ms - service_latency_ms,
    )
    latency_breakdown["api_total_ms"] = api_latency_ms
    return response.model_copy(
        update={
            "latency_ms": api_latency_ms,
            "latency_breakdown_ms": latency_breakdown,
        }
    )


@router.post(
    "/graph-search",
    response_model=RetrievalResponse,
)
def search_repository_with_graph(
    request: RetrievalRequest,
    seed_strategy: Literal[
        "post_rerank",
        "pre_rerank",
        "dual_source",
        "independent",
        "combined",
    ] = "pre_rerank",
    seed_budget: int = Query(default=5, ge=1, le=100),
    max_hops: int = Query(default=1, ge=0, le=3),
    graph_candidate_multiplier: int = Query(default=2, ge=1),
    max_graph_candidates: int = Query(default=100, ge=1, le=200),
    graph_only: bool = Query(default=False),
    db: Session = Depends(get_db),  # noqa: B008
) -> RetrievalResponse:
    """Opt-in graph-augmented retrieval; `/search` remains Hybrid V2."""
    started = perf_counter()
    service = GraphEnhancedRetrievalService(
        db,
        seed_strategy=seed_strategy,
        seed_budget=seed_budget,
        max_hops=max_hops,
        graph_candidate_multiplier=graph_candidate_multiplier,
        max_graph_candidates=max_graph_candidates,
        graph_only=graph_only,
    )
    initialized_ms = (perf_counter() - started) * 1000
    response = service.retrieve(request)
    api_latency_ms = (perf_counter() - started) * 1000
    latency_breakdown = dict(response.latency_breakdown_ms or {})
    latency_breakdown["service_initialization_ms"] = initialized_ms
    latency_breakdown["api_total_ms"] = api_latency_ms
    return response.model_copy(
        update={
            "latency_ms": api_latency_ms,
            "ranking_policy": response.ranking_policy
            or "hybrid_v2_plus_graph_v1",
            "latency_breakdown_ms": latency_breakdown,
        }
    )
