import tiktoken


class TokenCounter:
    """Counts tokens using a tiktoken encoding."""

    def __init__(self, encoding_name: str = "cl100k_base") -> None:
        self._encoding = tiktoken.get_encoding(encoding_name)

    def count(self, text: str) -> int:
        """Return the number of tokens in text."""
        if not text:
            return 0

        return len(self._encoding.encode(text))

    def encode(self, text: str) -> list[int]:
        """Encode text into token IDs."""
        return self._encoding.encode(text)

    def decode(self, tokens: list[int]) -> str:
        """Decode token IDs back into text."""
        return self._encoding.decode(tokens)