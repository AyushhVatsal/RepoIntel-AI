from sqlalchemy.orm import Session

from app.crud.chunk import chunk_crud
from app.crud.repository_file import repository_file_crud
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

        chunks = chunk_crud.get_by_ids(
            self.db,
            chunk_ids,
        )

        chunks_by_id = {
            chunk.id: chunk
            for chunk in chunks
        }

        hydrated: list[RetrievedChunk] = []

        for result in results:
            chunk = chunks_by_id.get(result.chunk_id)

            if chunk is None:
                continue

            repository_file = repository_file_crud.get(
                self.db,
                chunk.file_id,
            )

            file_path = (
                repository_file.relative_path
                if repository_file is not None
                else "unknown"
            )

            hydrated.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    content=chunk.content,
                    file_path=file_path,
                    similarity_score=result.dense_score,
                    retrieval_score=(
                        result.retrieval_score
                        if result.retrieval_score is not None
                        else result.score
                    ),
                )
            )

        return hydrated