from functools import lru_cache

import tiktoken


@lru_cache(maxsize=2)
def _get_encoding(encoding_name: str):
    """Reuse tokenizer assets and keep initialization out of file loops."""
    return tiktoken.get_encoding(encoding_name)


def warmup_tokenizer(encoding_name: str = "cl100k_base") -> None:
    """Load tokenizer assets before repository indexing requests arrive."""
    _get_encoding(encoding_name)


class TokenCounter:
    """Counts tokens using a tiktoken encoding."""

    def __init__(self, encoding_name: str = "cl100k_base") -> None:
        self._encoding = _get_encoding(encoding_name)

    def count(self, text: str) -> int:
        """Return the number of tokens in text."""
        if not text:
            return 0

        return len(self._encoding.encode(text, disallowed_special=()))

    def encode(self, text: str) -> list[int]:
        """Encode text into token IDs."""
        # Source code can contain strings resembling tokenizer control tokens;
        # preserve them as ordinary text instead of raising during indexing.
        return self._encoding.encode(text, disallowed_special=())

    def decode(self, tokens: list[int]) -> str:
        """Decode token IDs back into text."""
        return self._encoding.decode(tokens)
