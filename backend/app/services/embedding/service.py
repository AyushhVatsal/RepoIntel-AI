from __future__ import annotations

from collections.abc import Sequence

from app.schemas.chunk import ChunkCreate
from app.services.embedding.batching import EmbeddingBatcher
from app.services.embedding.cache import EmbeddingCache
from app.services.embedding.models.embedding_config import EmbeddingConfig
from app.services.embedding.models.embedding_result import EmbeddingResult
from app.services.embedding.providers.base import EmbeddingProvider


class EmbeddingService:
    """Orchestrates chunk embedding, batching, caching, and validation."""
    
    def __init__(
        self,
        provider: EmbeddingProvider,
        config: EmbeddingConfig,
        cache: EmbeddingCache | None = None,
    ) -> None:
        self._provider = provider
        self._config = config
        self._cache = cache or EmbeddingCache()
        self._batcher = EmbeddingBatcher(config.batch_size)

        if provider.dimensions != config.dimensions:
            raise ValueError(
                "Embedding provider dimensions do not match "
                "the configured dimensions."
            )

    def embed(
        self,
        chunks: Sequence[ChunkCreate],
    ) -> list[EmbeddingResult]:
        """Generate embeddings for chunks."""

        if not chunks:
            return []

        results: list[EmbeddingResult] = []
        pending: list[ChunkCreate] = []

        for chunk in chunks:
            if not chunk.content.strip():
                raise ValueError(
                    "Chunk content cannot be empty."
                )

            cached_embedding = self._cache.get(
                text=chunk.content,
                model=self._provider.model,
            )

            if cached_embedding is not None:
                results.append(
                    EmbeddingResult(
                        repository_id=chunk.repository_id,
                        file_id=chunk.file_id,
                        chunk_index=chunk.chunk_index,
                        vector=tuple(cached_embedding),
                        model=self._provider.model,
                        dimensions=len(cached_embedding),
                        cached=True,
                    )
                )
            else:
                pending.append(chunk)

        for batch in self._batcher.batch(pending):
            texts = [chunk.content for chunk in batch]

            embeddings = self._provider.embed(texts)

            if len(embeddings) != len(batch):
                raise ValueError(
                    "Embedding provider returned an unexpected "
                    "number of embeddings."
                )

            for chunk, embedding in zip(
                batch,
                embeddings,
                strict=True,
            ):
                if len(embedding) != self._config.dimensions:
                    raise ValueError(
                        f"Embedding for chunk "
                        f"{chunk.file_id}:{chunk.chunk_index} has "
                        f"{len(embedding)} dimensions; expected "
                        f"{self._config.dimensions}."
                    )

                self._cache.set(
                    text=chunk.content,
                    model=self._provider.model,
                    embedding=embedding,
                )

                results.append(
                    EmbeddingResult(
                        repository_id=chunk.repository_id,
                        file_id=chunk.file_id,
                        chunk_index=chunk.chunk_index,
                        vector=tuple(embedding),
                        model=self._provider.model,
                        dimensions=len(embedding),
                        cached=False,
                    )
                )

        return results