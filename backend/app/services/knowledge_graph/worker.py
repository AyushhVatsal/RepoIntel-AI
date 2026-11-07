"""Background entry point for independently rebuilding repository graphs."""

import logging

from app.crud.repository import repository_crud
from app.db.database import SessionLocal
from app.models.repository import GraphBuildStatus, RepositoryStatus
from app.services.knowledge_graph.lifecycle import build_repository_graph

logger = logging.getLogger(__name__)


def run_repository_graph_build(repository_id: int) -> None:
    """Build a queued graph with a private session and isolated failure state."""
    db = SessionLocal()
    try:
        repository = repository_crud.get(db, repository_id)
        if (
            repository is None
            or repository.status != RepositoryStatus.INDEXED
            or repository.graph_status != GraphBuildStatus.QUEUED.value
        ):
            return
        build_repository_graph(db, repository_id)
    except Exception:
        logger.exception(
            "Background graph build failed: repository_id=%s",
            repository_id,
        )
    finally:
        db.close()
