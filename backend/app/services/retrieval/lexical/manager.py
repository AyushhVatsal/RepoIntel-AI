from app.services.retrieval.lexical.index import BM25Index, LexicalDocument


class BM25IndexManager:
    """Manage repository-scoped BM25 indexes."""

    def __init__(self) -> None:
        self._indexes: dict[int, BM25Index] = {}

    def get(self, repository_id: int) -> BM25Index | None:
        """Return the cached index for a repository, if available."""
        return self._indexes.get(repository_id)

    def build(
        self,
        repository_id: int,
        documents: list[LexicalDocument],
    ) -> BM25Index:
        """Build and cache a BM25 index for a repository."""
        index = BM25Index()
        index.build(documents)

        self._indexes[repository_id] = index

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
        self._indexes.pop(repository_id, None)

    def clear(self) -> None:
        """Remove all cached repository indexes."""
        self._indexes.clear()