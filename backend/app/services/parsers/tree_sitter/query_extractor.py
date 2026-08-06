from __future__ import annotations

from pathlib import Path

from tree_sitter import Query, QueryCursor, Tree

from app.services.parsers.exceptions import QueryExecutionError

from .language_config import LanguageConfig
from .service import TreeSitterService


class QueryExtractor:
    """
    Executes Tree-sitter queries against syntax trees.

    Responsible only for:
    - Loading .scm query files
    - Compiling queries
    - Caching queries
    - Executing queries
    """

    _query_cache: dict[str, Query] = {}

    @classmethod
    def _load_query(
        cls,
        config: LanguageConfig,
    ) -> Query:

        if config.grammar_name is None:
            raise QueryExecutionError(
                f"{config.language} does not support Tree-sitter queries."
            )

        cache_key = config.grammar_name

        if cache_key in cls._query_cache:
            return cls._query_cache[cache_key]

        if config.query_file is None:
            raise QueryExecutionError(
                f"No query file configured for {config.language}."
            )

        if not config.query_file.exists():
            raise QueryExecutionError(
                f"Query file not found: {config.query_file}"
            )

        language = TreeSitterService.get_language(config)

        source = config.query_file.read_text(
            encoding="utf-8"
        )

        query = Query(language, source)

        cls._query_cache[cache_key] = query

        return query

    @classmethod
    def execute(
        cls,
        tree: Tree,
        config: LanguageConfig,
    ):
        """
        Execute the configured query against a syntax tree.

        Returns
        -------
        list[tuple[Node, str]]
        """

        query = cls._load_query(config)

        cursor = QueryCursor(query)

        captures = cursor.captures(tree.root_node)

        normalized: list[tuple] = []

        for capture_name, nodes in captures.items():
            for node in nodes:
                normalized.append(
                    (node, capture_name)
                )

        return normalized