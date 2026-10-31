from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.repository_file import RepositoryFile
from app.schemas.retrieval import RetrievedChunk
from app.services.retrieval.result import RetrievalResult


class RetrievalResultHydrator:
    def __init__(self, db: Session) -> None:
        self.db = db

    def hydrate(
        self,
        results: list[RetrievalResult],
    ) -> list[RetrievedChunk]:
        if not results:
            return []

        chunk_ids = [result.chunk_id for result in results]

        chunks_by_id = {
            chunk.id: (chunk, file_path)
            for chunk, file_path in self.db.execute(
                select(Chunk, RepositoryFile.relative_path)
                .join(RepositoryFile, RepositoryFile.id == Chunk.file_id)
                .where(Chunk.id.in_(chunk_ids))
            ).all()
        }

        hydrated: list[RetrievedChunk] = []

        for result in results:
            hydrated_row = chunks_by_id.get(result.chunk_id)

            if hydrated_row is None:
                continue
            chunk, file_path = hydrated_row

            hydrated.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    content=chunk.content,
                    file_path=file_path or "unknown",
                    similarity_score=result.dense_score,
                    hybrid_score=result.hybrid_score,
                    cross_encoder_score=result.cross_encoder_score,
                    retrieval_score=(
                        result.retrieval_score
                        if result.retrieval_score is not None
                        else result.score
                    ),
                )
            )

        return hydrated
