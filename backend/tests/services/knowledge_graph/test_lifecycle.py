from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.api.routes import repository as repository_route
from app.models.repository import (
    GraphBuildStatus,
    Repository,
    RepositoryStatus,
)
from app.models.user import User
from app.services.knowledge_graph import lifecycle
from app.services.knowledge_graph import worker as graph_worker
from app.services.knowledge_graph.worker import run_repository_graph_build


@pytest.fixture
def indexed_repository(db):
    suffix = uuid.uuid4().hex
    user = User(
        username=f"graph_lifecycle_{suffix}",
        email=f"graph_lifecycle_{suffix}@example.com",
        hashed_password="test-only-password",
        is_active=True,
    )
    db.add(user)
    db.flush()
    repository = Repository(
        owner_id=user.id,
        name="graph-lifecycle-test",
        github_url=f"https://github.com/graph-lifecycle/{suffix}",
        clone_path=f"/tmp/graph-lifecycle-{suffix}",
        status=RepositoryStatus.INDEXED,
        total_files=0,
        supported_files=0,
        skipped_files=0,
        repository_size=0,
        graph_status=GraphBuildStatus.NOT_BUILT.value,
    )
    db.add(repository)
    db.commit()
    yield repository
    db.delete(repository)
    db.delete(user)
    db.commit()


def test_graph_build_records_status_and_skips_duplicate_ready_build(
    db,
    indexed_repository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    builder = Mock(return_value={"nodes": 3, "edges": 2})
    monkeypatch.setattr(lifecycle.knowledge_graph_builder, "build", builder)

    result = lifecycle.build_repository_graph(db, indexed_repository.id)

    db.refresh(indexed_repository)
    assert result == {"nodes": 3, "edges": 2}
    assert indexed_repository.status == RepositoryStatus.INDEXED
    assert indexed_repository.graph_status == GraphBuildStatus.READY.value
    assert indexed_repository.graph_built_at is not None
    assert indexed_repository.graph_build_duration_ms is not None
    assert indexed_repository.graph_error is None

    assert lifecycle.build_repository_graph(db, indexed_repository.id) is None
    builder.assert_called_once_with(db, indexed_repository.id)


def test_graph_failure_keeps_vector_indexing_success_and_can_retry(
    db,
    indexed_repository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    builder = Mock(
        side_effect=[RuntimeError("graph build broke"), {"nodes": 1, "edges": 0}]
    )
    monkeypatch.setattr(lifecycle.knowledge_graph_builder, "build", builder)

    assert lifecycle.build_repository_graph(db, indexed_repository.id) is None
    db.refresh(indexed_repository)
    assert indexed_repository.status == RepositoryStatus.INDEXED
    assert indexed_repository.graph_status == GraphBuildStatus.FAILED.value
    assert indexed_repository.graph_error == "graph build broke"

    result = lifecycle.build_repository_graph(db, indexed_repository.id)
    db.refresh(indexed_repository)
    assert result == {"nodes": 1, "edges": 0}
    assert indexed_repository.status == RepositoryStatus.INDEXED
    assert indexed_repository.graph_status == GraphBuildStatus.READY.value
    assert indexed_repository.graph_error is None
    assert builder.call_count == 2


def test_independent_rebuild_endpoint_queues_once(
    db,
    indexed_repository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeRepositoryService:
        def get_repository(self, **_kwargs):
            return indexed_repository

    monkeypatch.setattr(
        repository_route,
        "get_repository_service",
        lambda: FakeRepositoryService(),
    )
    tasks = BackgroundTasks()

    response = repository_route.rebuild_repository_graph(
        indexed_repository.id,
        background_tasks=tasks,
        db=db,
        current_user=SimpleNamespace(id=indexed_repository.owner_id),
    )

    assert response.graph_status == GraphBuildStatus.QUEUED.value
    assert len(tasks.tasks) == 1
    assert tasks.tasks[0].func is run_repository_graph_build
    assert tasks.tasks[0].args == (indexed_repository.id,)

    with pytest.raises(HTTPException) as error:
        repository_route.rebuild_repository_graph(
            indexed_repository.id,
            background_tasks=BackgroundTasks(),
            db=db,
            current_user=SimpleNamespace(id=indexed_repository.owner_id),
        )
    assert error.value.status_code == 409


def test_independent_graph_worker_processes_queued_build(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = Mock()
    repository = SimpleNamespace(
        status=RepositoryStatus.INDEXED,
        graph_status=GraphBuildStatus.QUEUED.value,
    )
    monkeypatch.setattr(graph_worker, "SessionLocal", lambda: session)
    monkeypatch.setattr(
        graph_worker.repository_crud,
        "get",
        lambda _db, _repository_id: repository,
    )
    build = Mock(return_value={"nodes": 1, "edges": 0})
    monkeypatch.setattr(graph_worker, "build_repository_graph", build)

    run_repository_graph_build(53)

    build.assert_called_once_with(session, 53)
    session.close.assert_called_once_with()
