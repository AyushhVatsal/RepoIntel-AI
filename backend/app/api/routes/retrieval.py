from time import perf_counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.db import get_db
from app.schemas.retrieval import (
    RetrievalRequest,
    RetrievalResponse,
)
from app.services.retrieval.retrieval_service import RetrievalService

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
    retrieval_service = RetrievalService(db)
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
