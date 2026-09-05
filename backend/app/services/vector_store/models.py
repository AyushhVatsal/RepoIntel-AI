from dataclasses import dataclass

from app.models.chunk import Chunk


@dataclass(frozen=True, slots=True)
class VectorSearchResult:
    chunk: Chunk
    score: float