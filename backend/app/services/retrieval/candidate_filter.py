from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.repository_file import FileRole, RepositoryFile
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

        chunk_ids = {result.chunk_id for result in results}
        stmt = (
            select(Chunk.id, RepositoryFile.role)
            .join(
                Chunk,
                Chunk.file_id == RepositoryFile.id,
            )
            .where(Chunk.id.in_(chunk_ids))
        )
        roles_by_chunk = dict(self._db.execute(stmt).all())
        return [
            result
            for result in results
            if roles_by_chunk.get(result.chunk_id) not in excluded_roles
        ]
