from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks

from app.api.routes import repository as repository_route
from app.exceptions.repository import RepositoryAlreadyExistsError
from app.schemas.repository import RepositoryCreate
from app.services.repository import indexing_worker
from app.services.repository.indexing_worker import run_repository_indexing
from app.services.repository.repository_service import RepositoryService


def test_create_repository_schedules_job_and_returns_queued_record(monkeypatch):
    repository = SimpleNamespace(
        id=72,
        status="pending",
        indexing_progress=0,
        indexing_stage="queued",
        indexing_processed_files=0,
        indexing_total_files=0,
        indexing_error=None,
    )

    class FakeService:
        def create_indexing_job(self, **kwargs):
            assert kwargs["owner_id"] == 9
            return repository

    monkeypatch.setattr(
        repository_route,
        "get_repository_service",
        lambda: FakeService(),
    )
    tasks = BackgroundTasks()

    response = repository_route.create_repository(
        RepositoryCreate(github_url="https://github.com/example/repo"),
        background_tasks=tasks,
        db=object(),
        current_user=SimpleNamespace(id=9),
    )

    assert response is repository
    assert len(tasks.tasks) == 1
    assert tasks.tasks[0].func is run_repository_indexing
    assert tasks.tasks[0].args == (72,)
    create_route = next(
        route
        for route in repository_route.router.routes
        if getattr(route, "endpoint", None)
        is repository_route.create_repository
    )
    assert create_route.status_code == 202


def test_worker_uses_own_session_and_processes_pending_job(monkeypatch):
    sessions = []
    repository = SimpleNamespace(status="pending")
    processed = []

    class FakeSession:
        def __init__(self):
            self.closed = False
            sessions.append(self)

        def close(self):
            self.closed = True

    class FakeService:
        def process_indexing_job(self, db, job):
            processed.append((db, job))

    monkeypatch.setattr(indexing_worker, "SessionLocal", FakeSession)
    monkeypatch.setattr(
        indexing_worker.repository_crud,
        "get",
        lambda db, repository_id: repository,
    )
    monkeypatch.setattr(
        indexing_worker,
        "get_repository_service",
        lambda: FakeService(),
    )

    run_repository_indexing(72)

    assert processed == [(sessions[0], repository)]
    assert sessions[0].closed


def test_failed_job_can_be_requeued_for_same_repository(monkeypatch):
    failed = SimpleNamespace(status="failed", github_url="https://github.com/o/r")
    calls = []

    monkeypatch.setattr(
        "app.services.repository.repository_service.repository_crud.get_by_github_url",
        lambda **_kwargs: failed,
    )
    monkeypatch.setattr(
        "app.services.repository.repository_service.repository_crud.update",
        lambda **kwargs: calls.append(kwargs) or failed,
    )

    repository = RepositoryService().create_indexing_job(
        db=object(),
        owner_id=9,
        repository_in=RepositoryCreate(github_url=failed.github_url),
    )

    assert repository is failed
    assert calls[0]["status"].value == "pending"
    assert calls[0]["indexing_progress"] == 0
    assert calls[0]["indexing_stage"] == "queued"
    assert calls[0]["indexing_error"] is None


def test_indexed_repository_still_rejects_duplicate_submission(monkeypatch):
    indexed = SimpleNamespace(status="indexed", github_url="https://github.com/o/r")
    monkeypatch.setattr(
        "app.services.repository.repository_service.repository_crud.get_by_github_url",
        lambda **_kwargs: indexed,
    )

    with pytest.raises(RepositoryAlreadyExistsError):
        RepositoryService().create_indexing_job(
            db=object(),
            owner_id=9,
            repository_in=RepositoryCreate(github_url=indexed.github_url),
        )
