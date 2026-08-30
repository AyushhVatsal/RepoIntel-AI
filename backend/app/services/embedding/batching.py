from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import TypeVar


T = TypeVar("T")


class EmbeddingBatcher:
    """Splits embedding inputs into fixed-size batches."""

    def __init__(self, batch_size: int) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero.")

        self._batch_size = batch_size

    @property
    def batch_size(self) -> int:
        return self._batch_size

    def batch(self, items: Sequence[T]) -> Iterator[Sequence[T]]:
        """Yield items in batches of the configured size."""
        for start in range(0, len(items), self._batch_size):
            yield items[start : start + self._batch_size]