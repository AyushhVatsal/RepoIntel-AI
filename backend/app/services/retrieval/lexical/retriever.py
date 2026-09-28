from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.repository_file import RepositoryFile
from app.services.retrieval.filters import RetrievalFilters
from app.services.retrieval.result import RetrievalResult
from app.services.retrieval.lexical.index import (
    BM25Index,
    LexicalDocument,
)


class LexicalRetriever:
    """Repository-scoped BM25 retrieval."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def search(
        self,
        *,
        repository_id: int,
        query: str,
        top_k: int,
        filters: RetrievalFilters | None = None,
    ) -> list[RetrievalResult]:
        """
        Perform BM25 retrieval over chunks belonging to one repository.

        Returns:
            list of (chunk_id, bm25_score)
        """

        if top_k <= 0:
            return []

        stmt = (
            select(Chunk)
            .join(
                RepositoryFile,
                Chunk.file_id == RepositoryFile.id,
            )
            .where(
                Chunk.repository_id == repository_id,
            )
        )

        if filters:
            if filters.language:
                stmt = stmt.where(
                    RepositoryFile.language == filters.language,
                )

            if filters.file_path:
                stmt = stmt.where(
                    RepositoryFile.relative_path.ilike(
                        f"{filters.file_path}%"
                    )
                )

            if filters.chunk_type:
                stmt = stmt.where(
                    Chunk.chunk_type == filters.chunk_type,
                )

            if filters.symbol_name:
                stmt = stmt.where(
                    Chunk.symbol_name == filters.symbol_name,
                )

        chunks = self.db.scalars(stmt).all()

        if not chunks:
            return []

        documents = [
            LexicalDocument(
                chunk_id=chunk.id,
                content=chunk.content,
            )
            for chunk in chunks
        ]

        index = BM25Index()
        index.build(documents)

        return index.search(
            query=query,
            top_k=top_k,
        )