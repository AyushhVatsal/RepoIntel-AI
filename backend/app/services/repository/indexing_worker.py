"""In-process bounded runner for repository indexing jobs."""

import logging
from threading import BoundedSemaphore

from app.crud.repository import repository_crud
from app.db.database import SessionLocal
from app.models.repository import RepositoryStatus
from app.services.repository.repository_service import get_repository_service

logger = logging.getLogger(__name__)
_INDEXING_SLOT = BoundedSemaphore(value=1)


def run_repository_indexing(repository_id: int) -> None:
    """Run one queued job with its own session and bounded process resources."""
    with _INDEXING_SLOT:
        db = SessionLocal()
        try:
            repository = repository_crud.get(db, repository_id)
            if repository is None or repository.status != RepositoryStatus.PENDING:
                return
            get_repository_service().process_indexing_job(db, repository)
        except Exception:
            # The service persists FAILED status and error details. Keep this
            # boundary defensive so a background exception cannot affect the
            # response that has already been sent.
            logger.exception("Background indexing job failed: %s", repository_id)
        finally:
            db.close()
