from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache

from sentence_transformers import SentenceTransformer


class LocalEmbeddingProvider:
    """Embedding provider backed by a local Sentence Transformers model."""

    def __init__(
        self,
        model_name: str,
    ) -> None:
        self._model_name = model_name
        self._model = SentenceTransformer(model_name)

    @property
    def model(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._model.get_embedding_dimension()
    def embed(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        if not texts:
            return []

        embeddings = self._model.encode(
            list(texts),
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        return embeddings.tolist()

@lru_cache(maxsize=4)
def get_local_embedding_provider(model_name: str) -> LocalEmbeddingProvider:
    """Reuse a loaded embedding provider across requests."""
    return LocalEmbeddingProvider(model_name)