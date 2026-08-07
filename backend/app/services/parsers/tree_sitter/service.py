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

        if config.parser != "tree_sitter":
            raise UnsupportedLanguageError(
                f"{config.language} does not support Tree-sitter."
            )

        if config.grammar_name in cls._language_cache:
            return cls._language_cache[
                config.grammar_name
            ]

        module = importlib.import_module(
            config.grammar_module
        )

        if hasattr(module, "language"):
            language = Language(module.language())

        elif hasattr(module, f"language_{config.grammar_name}"):
            language = Language(
                getattr(
                    module,
                    f"language_{config.grammar_name}"
                )()
            )

        else:
            raise UnsupportedLanguageError(
                f"No language factory found for {config.language}."
            )

        cls._language_cache[
            config.grammar_name
        ] = language

        return language

    @classmethod
    def get_parser(
        cls,
        config: LanguageConfig,
    ) -> Parser:

        if config.grammar_name in cls._parser_cache:
            return cls._parser_cache[
                config.grammar_name
            ]

        language = cls.get_language(config)

        parser = Parser(language)

        cls._parser_cache[
            config.grammar_name
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