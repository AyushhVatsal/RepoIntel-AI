"""Repository-scoped lifecycle for building and rebuilding knowledge graphs."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from threading import BoundedSemaphore
from time import perf_counter

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.repository import GraphBuildStatus, Repository, RepositoryStatus
from app.services.knowledge_graph.builder import knowledge_graph_builder

logger = logging.getLogger(__name__)
_GRAPH_BUILD_SLOT = BoundedSemaphore(value=1)


def build_repository_graph(
    db: Session,
    repository_id: int,
    *,
    force: bool = False,
) -> dict[str, int] | None:
    """Build one indexed repository graph without changing indexing status.

    Builder errors are persisted as graph failures and deliberately swallowed;
    a graph failure must not invalidate successful vector indexing.
    """
    with _GRAPH_BUILD_SLOT:
        repository = db.get(Repository, repository_id)
        if repository is None:
            raise ValueError(f"Repository {repository_id} does not exist")
        if repository.status != RepositoryStatus.INDEXED:
            raise ValueError("A repository must be indexed before graph build")
        if (
            not force
            and repository.graph_status == GraphBuildStatus.READY.value
        ):
            return None

        buildable_statuses = [
            GraphBuildStatus.NOT_BUILT.value,
            GraphBuildStatus.FAILED.value,
            GraphBuildStatus.QUEUED.value,
        ]
        if force:
            buildable_statuses.append(GraphBuildStatus.READY.value)
        claimed = db.execute(
            update(Repository)
            .where(
                Repository.id == repository_id,
                Repository.status == RepositoryStatus.INDEXED,
                Repository.graph_status.in_(buildable_statuses),
            )
            .values(
                graph_status=GraphBuildStatus.BUILDING.value,
                graph_error=None,
            )
        )
        if claimed.rowcount != 1:
            db.rollback()
            return None
        db.commit()

        started = perf_counter()
        try:
            result = knowledge_graph_builder.build(db, repository_id)
        except Exception as exc:
            db.rollback()
            repository = db.get(Repository, repository_id)
            if repository is not None:
                repository.graph_status = GraphBuildStatus.FAILED.value
                repository.graph_error = str(exc)[:2000]
                repository.graph_build_duration_ms = (
                    perf_counter() - started
                ) * 1000
                db.commit()
            logger.exception(
                "Knowledge graph build failed: repository_id=%s",
                repository_id,
            )
            return None

        duration_ms = (perf_counter() - started) * 1000
        repository = db.get(Repository, repository_id)
        if repository is not None:
            repository.graph_status = GraphBuildStatus.READY.value
            repository.graph_built_at = datetime.now(UTC)
            repository.graph_build_duration_ms = duration_ms
            repository.graph_error = None
            db.commit()

        logger.info(
            "Knowledge graph build completed: repository_id=%s "
            "duration_ms=%.1f nodes=%s edges=%s files=%s chunks=%s",
            repository_id,
            duration_ms,
            result.get("nodes", 0),
            result.get("edges", 0),
            result.get("files", 0),
            result.get("chunks", 0),
        )
        return result
