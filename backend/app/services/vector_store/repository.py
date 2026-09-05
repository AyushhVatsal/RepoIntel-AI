from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.embedding import Embedding
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
    ) -> list[VectorSearchResult]:
        distance = Embedding.embedding.cosine_distance(query_vector)
        similarity = 1.0 - distance

        stmt = (
            select(Chunk, similarity.label("score"))
            .join(Embedding, Embedding.chunk_id == Chunk.id)
            .where(
                Chunk.repository_id == repository_id,
                Embedding.model == model,
            )
            .order_by(distance)
            .limit(top_k)
        )

        if score_threshold is not None:
            stmt = stmt.where(similarity >= score_threshold)

        rows = self.db.execute(stmt).all()

        return [
            VectorSearchResult(
                chunk=chunk,
                score=float(score),
            )
            for chunk, score in rows
        ]