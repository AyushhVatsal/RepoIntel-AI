from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseLanguageProcessor(ABC):
    """
    Base class for all language-specific processors.

    Processors receive the parsed document produced by
    SymbolExtractor and enhance it with language-specific
    information.
    """

    @classmethod
    @abstractmethod
    def process(
        cls,
        document: Any,
        grouped: dict,
        source_code: str,
    ) -> Any:
        """
        Enhance the parsed document with language-specific
        information and return the updated document.
        """
        raise NotImplementedError