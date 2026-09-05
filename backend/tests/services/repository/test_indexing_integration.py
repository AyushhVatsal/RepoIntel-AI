from pathlib import Path
from unittest.mock import patch
import pytest
from app.crud.chunk import chunk_crud
from app.crud.repository import repository_crud
from app.crud.repository_file import repository_file_crud
from app.crud.repository_symbol import repository_symbol_crud
from app.db.database import SessionLocal
from app.models.embedding import Embedding
from app.models.repository import RepositoryStatus
from app.models.user import User
from app.services.repository.repository_service import RepositoryService
from app.schemas.repository import RepositoryCreate
from sqlalchemy import delete


TEST_REPOSITORY = Path(__file__).resolve().parent / "fixture_repo"


def _create_fixture_repository() -> None:
    TEST_REPOSITORY.mkdir(parents=True, exist_ok=True)

    (TEST_REPOSITORY / "main.py").write_text(
        """
def add(a, b):
    return a + b


class Calculator:
    def multiply(self, a, b):
        return a * b
""".strip(),
        encoding="utf-8",
    )


def _remove_fixture_repository() -> None:
    if TEST_REPOSITORY.exists():
        for path in TEST_REPOSITORY.rglob("*"):
            if path.is_file():
                path.unlink()

        for path in sorted(
            TEST_REPOSITORY.rglob("*"),
            reverse=True,
        ):
            if path.is_dir():
                path.rmdir()

        TEST_REPOSITORY.rmdir()


def test_repository_indexing_end_to_end():
    db = SessionLocal()
    repository = None

    try:
        _create_fixture_repository()

        # ---------------------------------------------------------
        # Create test user
        # ---------------------------------------------------------

        db.execute(
            delete(User).where(
                User.email == "repository-e2e@test.local"
            )
        )
        db.commit()

        user = User(
            username="repository-e2e-test",
            email="repository-e2e@test.local",
            hashed_password="test-password",
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        service = RepositoryService()

        repository_create = RepositoryCreate(
            github_url="https://github.com/test/repository-e2e",
        )

        with patch(
            "app.services.repository.repository_service.clone_service.clone",
            return_value=TEST_REPOSITORY,
        ), patch(
            "app.services.repository.repository_service.clone_service.get_repository_name",
            return_value="repository-e2e",
        ), patch(
            "app.services.repository.repository_service.clone_service.get_default_branch",
            return_value="main",
        ):
            repository = service.index_repository(
                db=db,
                owner_id=user.id,
                repository_in=repository_create,
            )

        assert repository.status == RepositoryStatus.INDEXED

        persisted_files = repository_file_crud.get_by_repository(
            db=db,
            repository_id=repository.id,
        )

        assert len(persisted_files) > 0

        chunks = chunk_crud.get_by_repository(
            db=db,
            repository_id=repository.id,
        )

        assert len(chunks) > 0

        symbols = repository_symbol_crud.get_by_repository(
            db=db,
            repository_id=repository.id,
        )

        assert len(symbols) > 0

        embeddings = db.query(Embedding).join(
            Embedding.chunk
        ).filter(
            Embedding.chunk.has(
                repository_id=repository.id
            )
        ).all()

        assert len(embeddings) == len(chunks)

        for embedding in embeddings:
            assert embedding.model == "BAAI/bge-small-en-v1.5"
            assert embedding.dimensions == 384
            assert len(embedding.embedding) == 384

    finally:
        try:
            db.rollback()

            if repository is not None:
                repository_file_crud.delete_by_repository(
                    db=db,
                    repository_id=repository.id,
                )

                repository_symbol_crud.delete_by_repository(
                    db=db,
                    repository_id=repository.id,
                )

                repository_crud.delete(
                    db=db,
                    repository=repository,
                )

                db.commit()

            if user is not None and user.id is not None:
                db.delete(user)
                db.commit()

        finally:
            db.close()
            _remove_fixture_repository()

def test_repository_indexing_fails_when_vector_storage_fails():
    db = SessionLocal()
    user = None

    try:
        _create_fixture_repository()

        db.execute(
            delete(User).where(
                User.email == "repository-vector-failure@test.local"
            )
        )
        db.commit()

        user = User(
            username="repository-vector-failure",
            email="repository-vector-failure@test.local",
            hashed_password="test-password",
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        service = RepositoryService()

        repository_create = RepositoryCreate(
            github_url="https://github.com/test/repository-vector-failure",
        )

        with (
            patch(
                "app.services.repository.repository_service.clone_service.clone",
                return_value=TEST_REPOSITORY,
            ),
            patch(
                "app.services.repository.repository_service.clone_service.get_repository_name",
                return_value="repository-vector-failure",
            ),
            patch(
                "app.services.repository.repository_service.clone_service.get_default_branch",
                return_value="main",
            ),
            patch(
                "app.services.repository.repository_service.VectorStoreService.store_embedding",
                side_effect=RuntimeError("vector storage failure"),
            ),
        ):
            with pytest.raises(RuntimeError, match="vector storage failure"):
                service.index_repository(
                    db=db,
                    owner_id=user.id,
                    repository_in=repository_create,
                )

        db.rollback()

        assert (
            repository_crud.get_by_github_url(
                db=db,
                github_url=str(repository_create.github_url),
                owner_id=user.id,
            )
            is None
        )

    finally:
        db.rollback()

        if user is not None:
            db.execute(
                delete(User).where(
                    User.email == "repository-vector-failure@test.local"
                )
            )
            db.commit()

        db.close()
        _remove_fixture_repository()