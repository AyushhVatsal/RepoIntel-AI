from __future__ import annotations

import hashlib


class EmbeddingCache:
    """In-memory cache for generated embeddings."""

    def __init__(self) -> None:
        self._cache: dict[str, list[float]] = {}

    @staticmethod
    def build_key(
        text: str,
        model: str,
    ) -> str:
        """Create a deterministic cache key for text and model."""
        content_hash = hashlib.sha256(
            text.encode("utf-8")
        ).hexdigest()

        return f"{model}:{content_hash}"

    def get(
        self,
        text: str,
        model: str,
    ) -> list[float] | None:
        """Return a cached embedding if available."""
        key = self.build_key(text, model)
        return self._cache.get(key)

    def set(
        self,
        text: str,
        model: str,
        embedding: list[float],
    ) -> None:
        """Store an embedding in the cache."""
        key = self.build_key(text, model)
        self._cache[key] = embedding

    def clear(self) -> None:
        """Clear all cached embeddings."""
        self._cache.clear()

    @property
    def size(self) -> int:
        """Return the number of cached embeddings."""
        return len(self._cache)