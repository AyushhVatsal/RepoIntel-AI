from app.services.chunking.chunkers.base import BaseChunker
from app.services.chunking.chunkers.symbol import SymbolChunker
from app.services.chunking.chunkers.text import TextChunker


class ChunkerFactory:
    """Creates the appropriate chunker for a support tier."""

    def __init__(self) -> None:
        self._symbol_chunker = SymbolChunker()
        self._text_chunker = TextChunker()

    def get_chunker(self, support_tier: str) -> BaseChunker:
        tier = support_tier.lower()

        if tier == "tier_1":
            return self._symbol_chunker

        if tier == "tier_0":
            return self._text_chunker

        raise ValueError(
            f"Unsupported chunking tier: {support_tier}"
        )