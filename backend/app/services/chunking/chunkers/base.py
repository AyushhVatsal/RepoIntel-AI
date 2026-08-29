from abc import ABC, abstractmethod

from app.schemas.chunk import ChunkCreate


class BaseChunker(ABC):
    """Base interface for all chunking strategies."""

    @abstractmethod
    def chunk(
        self,
        *,
        repository_id: int,
        file_id: int,
        source_code: str,
    ) -> list[ChunkCreate]:
        """Split source code into retrieval-ready chunks."""
        raise NotImplementedError