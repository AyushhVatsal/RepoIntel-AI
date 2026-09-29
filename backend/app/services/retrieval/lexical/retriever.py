from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.repository_file import RepositoryFile
from app.services.retrieval.filters import RetrievalFilters
from app.services.retrieval.lexical.index import LexicalDocument
from app.services.retrieval.lexical.manager import BM25IndexManager
from app.services.retrieval.result import RetrievalResult


class LexicalRetriever:
    """Repository-scoped BM25 retrieval."""

    def __init__(
        self,
        db: Session,
        index_manager: BM25IndexManager,
    ) -> None:
        self.db = db
        self.index_manager = index_manager

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

            if filters.role:
                stmt = stmt.where(
                    RepositoryFile.role == filters.role,
                )

            if filters.exclude_roles:
                stmt = stmt.where(
                    ~RepositoryFile.role.in_(filters.exclude_roles)
                )
                
        if filters:
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

            index = self.index_manager.build_temporary(documents)

        else:
            index = self.index_manager.get(repository_id)

            if index is None:
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

                index = self.index_manager.build(
                    repository_id,
                    documents,
                )

        return index.search(
            query=query,
            top_k=top_k,
        )