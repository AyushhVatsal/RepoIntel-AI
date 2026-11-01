from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.repository_file import FileRole, RepositoryFile
from app.services.repository.file_role_classifier import FileRoleClassifier
from app.services.retrieval.result import RetrievalResult


class RetrievalCandidateFilter:
    """Filter retrieval candidates using repository file roles."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._role_classifier = FileRoleClassifier()

    def exclude_roles(
        self,
        results: list[RetrievalResult],
        roles: list[FileRole],
    ) -> list[RetrievalResult]:
        if not results or not roles:
            return results

        excluded_roles = set(roles)

        chunk_ids = {result.chunk_id for result in results}
        stmt = (
            select(
                Chunk.id,
                RepositoryFile.role,
                RepositoryFile.relative_path,
                RepositoryFile.filename,
                RepositoryFile.category,
            )
            .join(
                Chunk,
                Chunk.file_id == RepositoryFile.id,
            )
            .where(Chunk.id.in_(chunk_ids))
        )
        metadata_by_chunk = {
            chunk_id: (role, relative_path, filename, category)
            for chunk_id, role, relative_path, filename, category in self._db.execute(
                stmt
            ).all()
        }

        filtered: list[RetrievalResult] = []
        for result in results:
            metadata = metadata_by_chunk.get(result.chunk_id)
            if metadata is None:
                continue

            role, relative_path, filename, category = metadata
            if role in excluded_roles:
                continue

            inferred_role = self._role_classifier.classify(
                relative_path=relative_path,
                filename=filename,
                category=category,
            )
            if inferred_role not in excluded_roles:
                filtered.append(result)

        return filtered
