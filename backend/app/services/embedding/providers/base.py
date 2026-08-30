from __future__ import annotations

from typing import Protocol, Sequence


class EmbeddingProvider(Protocol):
    """Interface implemented by embedding providers."""

    @property
    def model(self) -> str:
        """Return the embedding model identifier."""
        ...

    @property
    def dimensions(self) -> int:
        """Return the embedding vector dimensions."""
        ...

    def embed(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        """Generate embeddings for the supplied texts."""
        ...