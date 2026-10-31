from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from app.services.retrieval.lexical.tokenizer import tokenize_code
from app.services.retrieval.result import RetrievalResult


@dataclass(frozen=True)
class LexicalDocument:
    """A document stored in the BM25 index."""

    chunk_id: int
    content: str
    symbol_name: str | None = None
    qualified_name: str | None = None


class BM25Index:
    """In-memory BM25 index for repository chunks."""

    def __init__(self) -> None:
        self._documents: list[LexicalDocument] = []
        self._bm25: BM25Okapi | None = None
        self._symbol_lookup: dict[str, list[int]] = {}

    def build(self, documents: list[LexicalDocument]) -> None:
        """Build the BM25 index from the supplied documents."""

        self._documents = list(documents)
        self._symbol_lookup = {}
        for index, document in enumerate(self._documents):
            for name in (document.symbol_name, document.qualified_name):
                if not name:
                    continue
                normalized_name = name.casefold().strip()
                self._symbol_lookup.setdefault(normalized_name, []).append(
                    index
                )

        tokenized_documents = [
            tokenize_code(document.content)
            for document in self._documents
        ]

        if not tokenized_documents:
            self._bm25 = None
            return

        self._bm25 = BM25Okapi(tokenized_documents)

    def search(
        self,
        query: str,
        top_k: int,
    ) -> list[RetrievalResult]:
        """
        Search the index and return:

            (chunk_id, bm25_score)

        ordered from highest to lowest score.
        """

        if top_k <= 0:
            return []

        if self._bm25 is None or not self._documents:
            return []

        query_tokens = tokenize_code(query)

        # Natural language questions often describe a configuration field
        # without using the word "config". Add a small, intent-specific
        # vocabulary so BM25 can surface configuration modules alongside
        # chunks that merely mention the setting at runtime.
        normalized_query = query.casefold()
        if any(
            term in normalized_query
            for term in (
                "embedding model",
                "batch size",
                "number of dimensions",
                "vector dimension",
                "embedding provider",
            )
        ):
            query_tokens.extend(("config", "configuration", "setting"))

        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)

        # A code query that exactly names a symbol should find its declaration
        # even if the name is absent from the stored chunk body. Keep this as
        # a narrow exact-match signal instead of injecting metadata tokens
        # into every document's BM25 statistics.
        exact_symbol_query = query.strip().casefold()
        exact_symbol_matches = self._symbol_lookup.get(exact_symbol_query, [])
        if exact_symbol_matches:
            exact_match_score = max(scores, default=0.0) + 1.0
            for index in exact_symbol_matches:
                scores[index] = exact_match_score

        ranked_indices = sorted(
            range(len(scores)),
            key=lambda index: scores[index],
            reverse=True,
        )[:top_k]

        return [
            RetrievalResult(
                chunk_id=self._documents[index].chunk_id,
                score=float(scores[index]),
            )
            for index in ranked_indices
        ]

    @property
    def size(self) -> int:
        """Return the number of indexed documents."""

        return len(self._documents)
