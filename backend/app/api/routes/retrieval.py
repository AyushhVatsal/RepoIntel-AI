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
    db: Session = Depends(get_db),
) -> RetrievalResponse:
    """Retrieve relevant chunks from an indexed repository."""

    retrieval_service = RetrievalService(db)

    return retrieval_service.retrieve(request)