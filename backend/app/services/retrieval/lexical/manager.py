from functools import lru_cache

from app.services.retrieval.lexical.index import BM25Index, LexicalDocument


class BM25IndexManager:
    """Manage repository-scoped BM25 indexes."""

    def __init__(self) -> None:
        self._indexes: dict[tuple[int, tuple[object, ...] | None], BM25Index] = {}

    @staticmethod
    def _key(
        repository_id: int,
        filter_key: tuple[object, ...] | None,
    ) -> tuple[int, tuple[object, ...] | None]:
        return repository_id, filter_key

    def get(
        self,
        repository_id: int,
        filter_key: tuple[object, ...] | None = None,
    ) -> BM25Index | None:
        """Return the cached index for a repository, if available."""
        return self._indexes.get(self._key(repository_id, filter_key))

    def build(
        self,
        repository_id: int,
        documents: list[LexicalDocument],
        filter_key: tuple[object, ...] | None = None,
    ) -> BM25Index:
        """Build and cache a BM25 index for a repository."""
        index = BM25Index()
        index.build(documents)

        self._indexes[self._key(repository_id, filter_key)] = index

        return index

    def build_temporary(
        self,
        documents: list[LexicalDocument],
    ) -> BM25Index:
        """Build a BM25 index without caching it."""
        index = BM25Index()
        index.build(documents)

        return index

    def invalidate(self, repository_id: int) -> None:
        """Remove the cached index for a repository."""
        keys = [key for key in self._indexes if key[0] == repository_id]
        for key in keys:
            self._indexes.pop(key, None)

    def clear(self) -> None:
        """Remove all cached repository indexes."""
        self._indexes.clear()

@lru_cache(maxsize=1)
def get_bm25_index_manager() -> BM25IndexManager:
    """Return the shared BM25 index manager for this process."""
    return BM25IndexManager()
