from __future__ import annotations

from ..base_processor import BaseLanguageProcessor


class TypeScriptProcessor(BaseLanguageProcessor):
    """TypeScript-specific symbol enhancements."""

    @classmethod
    def process(
        cls,
        symbols: list,
        grouped: dict,
        source_code: str,
    ) -> list:
        # Inherit JS behavior + add TS-specific
        from app.services.parsers.tree_sitter.languages.javascript import JavaScriptProcessor

        # Apply JS processing first (TS is superset of JS)
        JavaScriptProcessor.process(symbols, grouped, source_code)

        # TODO: Add TS-specific extraction (interfaces, enums, type aliases)
        # For now, TS shares JS processor

        return symbols
