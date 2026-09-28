from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from app.services.retrieval.lexical.tokenizer import tokenize_code

from app.services.retrieval.result import RetrievalResult

@dataclass(frozen=True)
class LexicalDocument:
    """A document stored in the BM25 index."""

    chunk_id: int
    content: str


class BM25Index:
    """In-memory BM25 index for repository chunks."""

    def __init__(self) -> None:
        self._documents: list[LexicalDocument] = []
        self._bm25: BM25Okapi | None = None

    def build(self, documents: list[LexicalDocument]) -> None:
        """Build the BM25 index from the supplied documents."""

        self._documents = list(documents)

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

        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)

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