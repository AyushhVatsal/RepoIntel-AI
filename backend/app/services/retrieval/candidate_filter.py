from sqlalchemy.orm import Session

from app.models.repository_file import FileRole
from app.services.retrieval.result import RetrievalResult


class RetrievalCandidateFilter:
    """Filter retrieval candidates using repository file roles."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def exclude_roles(
        self,
        results: list[RetrievalResult],
        roles: list[FileRole],
    ) -> list[RetrievalResult]:
        if not results or not roles:
            return results

        excluded_roles = set(roles)

        filtered: list[RetrievalResult] = []

        for result in results:
            role = self._get_role(result.chunk_id)

            if role not in excluded_roles:
                filtered.append(result)

        return filtered

    def _get_role(
        self,
        chunk_id: int,
    ) -> FileRole | None:
        from sqlalchemy import select

        from app.models.chunk import Chunk
        from app.models.repository_file import RepositoryFile

        stmt = (
            select(RepositoryFile.role)
            .join(
                Chunk,
                Chunk.file_id == RepositoryFile.id,
            )
            .where(
                Chunk.id == chunk_id,
            )
        )

        return self._db.scalar(stmt)