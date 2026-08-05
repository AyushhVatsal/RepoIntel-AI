from __future__ import annotations

from pathlib import Path

from app.services.parsers.models.base import ParserBaseModel


class LanguageConfig(ParserBaseModel):
    """
    Describes how a language integrates with the parser.

    The parser should depend only on this configuration,
    never on language-specific conditions.
    """

    # ==========================================================
    # Identity
    # ==========================================================

    language: str

    extensions: tuple[str, ...]

    # ==========================================================
    # Tier
    # ==========================================================

    tier: str

    # ==========================================================
    # Parser
    # ==========================================================

    parser: str

    # ==========================================================
    # Tree-sitter
    # ==========================================================

    grammar_name: str | None = None

    grammar_module: str | None = None

    query_file: Path | None = None

    # ==========================================================
    # Capabilities
    # ==========================================================

    supports_ast: bool = False

    supports_symbols: bool = False

    supports_docstrings: bool = False

    supports_return_types: bool = False

    supports_incremental_parsing: bool = False