from __future__ import annotations

import importlib

from tree_sitter import Language, Parser, Tree

from app.services.parsers.exceptions import (
    TreeSitterParserError,
    UnsupportedLanguageError,
)

from .language_config import LanguageConfig


class TreeSitterService:
    """
    Service responsible for interacting with Tree-sitter.
    """

    _language_cache: dict[str, Language] = {}

    _parser_cache: dict[str, Parser] = {}

    @classmethod
    def get_language(
        cls,
        config: LanguageConfig,
    ) -> Language:

        if not config.supports_tree_sitter:
            raise UnsupportedLanguageError(
                f"{config.language} does not support Tree-sitter."
            )

        if config.tree_sitter_language in cls._language_cache:
            return cls._language_cache[
                config.tree_sitter_language
            ]

        module = importlib.import_module(
            config.grammar_module
        )

        language = Language(
            module.language()
        )

        cls._language_cache[
            config.tree_sitter_language
        ] = language

        return language

    @classmethod
    def get_parser(
        cls,
        config: LanguageConfig,
    ) -> Parser:

        if config.tree_sitter_language in cls._parser_cache:
            return cls._parser_cache[
                config.tree_sitter_language
            ]

        language = cls.get_language(config)

        parser = Parser(language)

        cls._parser_cache[
            config.tree_sitter_language
        ] = parser

        return parser

    @classmethod
    def parse(
        cls,
        source: bytes,
        config: LanguageConfig,
    ) -> Tree:

        parser = cls.get_parser(config)

        try:
            return parser.parse(source)

        except Exception as exc:
            raise TreeSitterParserError(
                f"Failed to parse {config.language}."
            ) from exc