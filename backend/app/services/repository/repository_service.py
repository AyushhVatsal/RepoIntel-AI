from __future__ import annotations

import shutil
from pathlib import Path

from sqlalchemy.orm import Session

from app.crud.repository import repository_crud
from app.crud.repository_file import repository_file_crud
from app.exceptions.repository import (
    RepositoryAlreadyExistsError,
    RepositoryNotFoundError,
)
from app.models.repository import RepositoryStatus
from app.models.repository_file import LanguageSupportTier
from app.schemas.repository import RepositoryCreate
from app.services.repository.clone_service import clone_service
from app.services.repository.framework_detector import (
    framework_detection_service
)
from app.services.repository.metadata_service import (
    metadata_service,
)
from app.services.repository.scanner_service import (
    scanner_service,
)


class RepositoryService:
    """
    Coordinate the complete repository indexing workflow.

    Responsibilities
    ----------------
    - Create repository record
    - Clone repository
    - Scan repository
    - Detect framework
    - Calculate metadata
    - Persist repository files
    - Update repository status
    """

    def index_repository(
        self,
        db: Session,
        owner_id: int,
        repository_in: RepositoryCreate,
    ):
        """
        Clone, scan and index a repository.
        """

        # ---------------------------------------------------------
        # Check for duplicate repository
        # ---------------------------------------------------------

        existing_repository = repository_crud.get_by_github_url(
            db=db,
            github_url=str(repository_in.github_url),
        )

        from sqlalchemy import text

        print(
            "Current DB:",
            db.execute(
                text("SELECT current_database()")
            ).scalar(),
        )

        print(
            "Columns:",
            db.execute(
                text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'repositories'
                ORDER BY ordinal_position
                """)
            ).fetchall(),
        )
        if existing_repository is not None:
            raise RepositoryAlreadyExistsError(
                "Repository has already been indexed."
            )

        # ---------------------------------------------------------
        # Create initial repository record
        # ---------------------------------------------------------

        repository = repository_crud.create(
            db=db,
            repository_in=repository_in,
            owner_id=owner_id,
            status=RepositoryStatus.PENDING,
            name="",
            clone_path="",
        )

        try:

            # -----------------------------------------------------
            # Clone repository
            # -----------------------------------------------------

            repository_crud.update(
                db=db,
                repository=repository,
                status=RepositoryStatus.CLONING,
            )

            clone_path = clone_service.clone(
                repository_in.github_url,
                str(repository.id),
            )

            repository_name = clone_service.get_repository_name(
                repository_in.github_url,
            )

            default_branch = clone_service.get_default_branch(
                clone_path,
            )

            repository_crud.update(
                db=db,
                repository=repository,
                name=repository_name,
                clone_path=str(clone_path),
                default_branch=default_branch,
            )

            # -----------------------------------------------------
            # Scan repository
            # -----------------------------------------------------

            repository_crud.update(
                db=db,
                repository=repository,
                status=RepositoryStatus.SCANNING,
            )

            all_repository_files = scanner_service.scan(
                repository_id=repository.id,
                repository_path=clone_path,
            )

            supported_repository_files = [
                repository_file
                for repository_file in all_repository_files
                if repository_file.support_tier != LanguageSupportTier.NONE
            ]

            # -----------------------------------------------------
            # Persist supported files
            # -----------------------------------------------------

            repository_file_crud.create_many(
                db=db,
                files=supported_repository_files,
            )

            # -----------------------------------------------------
            # Detect framework
            # -----------------------------------------------------

            framework_result = framework_detection_service.detect(
                clone_path,
            )

            # -----------------------------------------------------
            # Calculate repository metadata
            # -----------------------------------------------------

            metadata = metadata_service.calculate(
                all_repository_files,
            )

            # -----------------------------------------------------
            # Final repository update
            # -----------------------------------------------------

            repository = repository_crud.update(
                db=db,
                repository=repository,
                primary_framework=framework_result.primary_framework,
                status=RepositoryStatus.INDEXED,
                **metadata,
            )

            return repository

        except Exception:

            self._cleanup_failed_indexing(
                db=db,
                repository=repository,
            )

            raise

    def list_repositories(
        self,
        db: Session,
        owner_id: int,
    ):
        """
        Return all repositories owned by the user.
        """

        return repository_crud.get_by_owner(
            db=db,
            owner_id=owner_id,
        )

    def get_repository(
        self,
        db: Session,
        repository_id: int,
        owner_id: int,
    ):
        """
        Retrieve a repository owned by the user.
        """

        repository = repository_crud.get(
            db=db,
            repository_id=repository_id,
        )

        if repository is None:
            raise RepositoryNotFoundError(
                "Repository not found."
            )

        if repository.owner_id != owner_id:
            raise RepositoryNotFoundError(
                "Repository not found."
            )

        return repository

    def delete_repository(
        self,
        db: Session,
        repository_id: int,
        owner_id: int,
    ) -> None:
        """
        Delete a repository and all associated resources.
        """

        repository = self.get_repository(
            db=db,
            repository_id=repository_id,
            owner_id=owner_id,
        )

        # Delete indexed files
        repository_file_crud.delete_by_repository(
            db=db,
            repository_id=repository.id,
        )

        # Delete cloned repository
        try:
            if repository.clone_path:
                clone_path = Path(repository.clone_path)

                if clone_path.exists():
                    shutil.rmtree(
                        clone_path,
                        ignore_errors=True,
                    )
        except Exception:
            pass

        # Delete repository
        repository_crud.delete(
            db=db,
            repository=repository,
        )
    def list_repository_files(
        self,
        db: Session,
        repository_id: int,
        owner_id: int,
    ):
        """
        Return all indexed files for a repository.
        """

        repository = self.get_repository(
            db=db,
            repository_id=repository_id,
            owner_id=owner_id,
        )

        return repository_file_crud.get_by_repository(
            db=db,
            repository_id=repository.id,
        )

    def _cleanup_failed_indexing(
        self,
        db: Session,
        repository,
    ) -> None:
        """
        Clean up all resources created during a failed indexing operation.
        """

        # Delete indexed files
        repository_file_crud.delete_by_repository(
            db=db,
            repository_id=repository.id,
        )

        # Delete cloned repository
        try:
            if repository.clone_path:
                clone_path = Path(repository.clone_path)

                if clone_path.exists():
                    shutil.rmtree(
                        clone_path,
                        ignore_errors=True,
                    )
        except Exception:
            pass

        # Delete repository record
        repository_crud.delete(
            db=db,
            repository=repository,
        )


repository_service = RepositoryService()