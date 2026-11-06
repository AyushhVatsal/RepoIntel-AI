from __future__ import annotations

from collections.abc import Sequence
from threading import Lock
from time import perf_counter

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
        self._profile_lock = Lock()
        self._profile = {
            "chunks": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "provider_batches": 0,
            "cache_lookup_ms": 0.0,
            "provider_wall_ms": 0.0,
            "service_overhead_ms": 0.0,
        }

        if provider.dimensions != config.dimensions:
            raise ValueError(
                "Embedding provider dimensions do not match "
                "the configured dimensions."
            )

    @property
    def model_name(self) -> str:
        """Return the embedding model used by this service."""
        return self._provider.model

    @property
    def batch_size(self) -> int:
        """Maximum number of texts passed to the provider per batch."""
        return self._batcher.batch_size

    def profile_snapshot(self) -> dict[str, object]:
        """Return cache, provider, and model-stage profiling counters."""
        with self._profile_lock:
            snapshot = dict(self._profile)
        provider_profile = getattr(self._provider, "profile_snapshot", None)
        snapshot["provider"] = provider_profile() if provider_profile else {}
        return snapshot

    def reset_profile(self) -> None:
        """Reset counters so the next repository job is measured alone."""
        with self._profile_lock:
            self._profile = {
                key: 0.0 if key.endswith("_ms") else 0
                for key in self._profile
            }
        provider_reset = getattr(self._provider, "reset_profile", None)
        if provider_reset:
            provider_reset()

    def embed_query(
        self,
        query: str,
    ) -> list[float]:
        """Generate an embedding for a retrieval query."""

        if not query.strip():
            raise ValueError("Query cannot be empty.")

        embeddings = self._provider.embed([query])

        if len(embeddings) != 1:
            raise ValueError(
                "Embedding provider returned an unexpected "
                "number of query embeddings."
            )

        embedding = embeddings[0]

        if len(embedding) != self._config.dimensions:
            raise ValueError(
                f"Query embedding has {len(embedding)} dimensions; "
                f"expected {self._config.dimensions}."
            )

        return list(embedding)

    def embed(
        self,
        chunks: Sequence[ChunkCreate],
    ) -> list[EmbeddingResult]:
        """Generate embeddings for chunks."""

        if not chunks:
            return []

        results: list[EmbeddingResult] = []
        pending: list[ChunkCreate] = []
        started = perf_counter()
        cache_started = perf_counter()
        cache_hits = 0

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
                cache_hits += 1
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

        cache_lookup_ms = (perf_counter() - cache_started) * 1000
        provider_wall_ms = 0.0
        provider_batches = 0

        for batch in self._batcher.batch(pending):
            texts = [chunk.content for chunk in batch]

            provider_started = perf_counter()
            embeddings = self._provider.embed(texts)
            provider_wall_ms += (perf_counter() - provider_started) * 1000
            provider_batches += 1

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

        total_ms = (perf_counter() - started) * 1000
        with self._profile_lock:
            self._profile["chunks"] += len(chunks)
            self._profile["cache_hits"] += cache_hits
            self._profile["cache_misses"] += len(pending)
            self._profile["provider_batches"] += provider_batches
            self._profile["cache_lookup_ms"] += cache_lookup_ms
            self._profile["provider_wall_ms"] += provider_wall_ms
            self._profile["service_overhead_ms"] += max(
                total_ms - cache_lookup_ms - provider_wall_ms,
                0.0,
            )
        return results
