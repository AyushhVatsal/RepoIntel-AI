from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.schemas.chunk import ChunkCreate


class ChunkCRUD:
    """CRUD operations for repository chunks."""

    @staticmethod
    def _to_model(chunk_in: ChunkCreate) -> Chunk:
        data = chunk_in.model_dump()
        data["metadata_"] = data.pop("metadata")
        return Chunk(**data)

    def create(
        self,
        db: Session,
        chunk_in: ChunkCreate,
    ) -> Chunk:
        """Create a single chunk."""
        db_chunk = self._to_model(chunk_in)

        db.add(db_chunk)
        db.commit()
        db.refresh(db_chunk)

        return db_chunk

    def create_many(
        self,
        db: Session,
        chunks: list[ChunkCreate],
    ) -> list[Chunk]:
        """Bulk insert chunks."""
        if not chunks:
            return []

        db_chunks = [
            self._to_model(chunk)
            for chunk in chunks
        ]

        db.add_all(db_chunks)
        db.commit()

        for db_chunk in db_chunks:
            db.refresh(db_chunk)

        return db_chunks

    def get(
        self,
        db: Session,
        chunk_id: int,
    ) -> Chunk | None:
        """Get a chunk by ID."""
        return db.get(Chunk, chunk_id)

    def get_by_repository(
        self,
        db: Session,
        repository_id: int,
    ) -> list[Chunk]:
        """Get all chunks for a repository."""
        stmt = (
            select(Chunk)
            .where(Chunk.repository_id == repository_id)
            .order_by(
                Chunk.file_id,
                Chunk.chunk_index,
            )
        )
        return list(db.scalars(stmt).all())

    def get_by_file(
        self,
        db: Session,
        file_id: int,
    ) -> list[Chunk]:
        """Get all chunks for a specific file."""
        stmt = (
            select(Chunk)
            .where(Chunk.file_id == file_id)
            .order_by(Chunk.chunk_index)
        )
        return list(db.scalars(stmt).all())

    def delete(
        self,
        db: Session,
        chunk_id: int,
    ) -> None:
        """Delete a chunk by ID."""
        chunk = self.get(db, chunk_id)

        if chunk:
            db.delete(chunk)
            db.commit()

    def delete_by_repository(
        self,
        db: Session,
        repository_id: int,
    ) -> None:
        """Delete all chunks for a repository."""
        stmt = (
            delete(Chunk)
            .where(Chunk.repository_id == repository_id)
        )

        db.execute(stmt)
        db.commit()

    def delete_by_file(
        self,
        db: Session,
        file_id: int,
    ) -> None:
        """Delete all chunks for a file."""
        stmt = (
            delete(Chunk)
            .where(Chunk.file_id == file_id)
        )

        db.execute(stmt)
        db.commit()


chunk_crud = ChunkCRUD()