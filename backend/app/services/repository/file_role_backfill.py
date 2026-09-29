from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.repository_file import RepositoryFile
from app.services.repository.file_role_classifier import FileRoleClassifier


class FileRoleBackfillService:
    """Backfill retrieval roles for existing repository files."""

    def __init__(
        self,
        db: Session,
        classifier: FileRoleClassifier | None = None,
    ) -> None:
        self._db = db
        self._classifier = classifier or FileRoleClassifier()

    def backfill_repository(self, repository_id: int) -> int:
        stmt = select(RepositoryFile).where(
            RepositoryFile.repository_id == repository_id,
        )

        files = list(self._db.scalars(stmt).all())

        updated = 0

        for repository_file in files:
            role = self._classifier.classify(
                relative_path=repository_file.relative_path,
                filename=repository_file.filename,
                category=repository_file.category,
            )

            if repository_file.role != role:
                repository_file.role = role
                updated += 1

        self._db.commit()

        return updated