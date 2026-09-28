from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.embedding import Embedding
from app.models.repository_file import RepositoryFile
from app.services.retrieval.filters import RetrievalFilters
from app.services.vector_store.models import VectorSearchResult


class VectorStoreRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def similarity_search(
        self,
        query_vector: list[float],
        repository_id: int,
        model: str,
        top_k: int,
        score_threshold: float | None = None,
        filters: RetrievalFilters | None = None,
    ) -> list[VectorSearchResult]:
        distance = Embedding.embedding.cosine_distance(
            query_vector
        )

        similarity = 1.0 - distance

        stmt = (
            select(
                Chunk,
                similarity.label("score"),
            )
            .join(
                Embedding,
                Embedding.chunk_id == Chunk.id,
            )
            .join(
                RepositoryFile,
                RepositoryFile.id == Chunk.file_id,
            )
            .where(
                Chunk.repository_id == repository_id,
                RepositoryFile.repository_id == repository_id,
                Embedding.model == model,
            )
        )

        if filters is not None:
            if filters.language is not None:
                stmt = stmt.where(
                    RepositoryFile.language
                    == filters.language
                )

            if filters.file_path is not None:
                stmt = stmt.where(
                    RepositoryFile.relative_path.ilike(
                        f"{filters.file_path}%"
                    )
                )

            if filters.chunk_type is not None:
                stmt = stmt.where(
                    Chunk.chunk_type
                    == filters.chunk_type
                )

            if filters.symbol_name is not None:
                stmt = stmt.where(
                    Chunk.symbol_name
                    == filters.symbol_name
                )

        stmt = (
            stmt
            .order_by(distance)
            .limit(top_k)
        )

        if score_threshold is not None:
            stmt = stmt.where(
                similarity >= score_threshold
            )

        rows = self.db.execute(stmt).all()

        return [
            VectorSearchResult(
                chunk=chunk,
                score=float(score),
            )
            for chunk, score in rows
        ]