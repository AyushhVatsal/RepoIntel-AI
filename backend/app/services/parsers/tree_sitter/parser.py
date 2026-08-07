from __future__ import annotations

from app.services.parsers.models.file_content import FileContent
from app.services.parsers.models.parsed_document import ParsedDocument

from .language_registry import LanguageRegistry
from .query_extractor import QueryExtractor
from .service import TreeSitterService
from .symbol_extractor import SymbolExtractor

from .grammar_registry import GrammarRegistry

from .languages.javascript.javascript_processor import JavaScriptProcessor

class TreeSitterParser:
    """
    Parser implementation for Tier 1 languages.

    Responsibilities
    ----------------
    - Resolve the language configuration
    - Build the Tree-sitter syntax tree
    - Execute the Tree-sitter query
    - Convert query captures into parser symbols
    - Return a ParsedDocument

    This class intentionally contains no parsing business logic.
    """

    @classmethod
    def parse(
        cls,
        file_content: FileContent,
    ) -> ParsedDocument:
        """
        Parse a Tier 1 source file into the parser's
        intermediate representation.
        """

        repository_file = file_content.repository_file

        if repository_file.language is None:
            raise ValueError(
                "Repository file language is missing."
            )

        source_code = file_content.content.decode(
            "utf-8",
            errors="replace",
        )

        language_config = LanguageRegistry.get(
            repository_file.language,
        )

        tree = TreeSitterService.parse(
            source=file_content.content,
            config=language_config,
        )

        captures = QueryExtractor.execute(
            tree=tree,
            config=language_config,
        )
        print("=" * 80)
        print("CAPTURES")
        print("=" * 80)

        for capture in captures:
            print(capture)


        grammar_config = GrammarRegistry.get(
            repository_file.language,
        )

        symbols, grouped = SymbolExtractor.extract(
            captures=captures,
            source_code=source_code,
            language_config=language_config,
            grammar_config=grammar_config,
        )

        if repository_file.language == "javascript":
            symbols = JavaScriptProcessor.process(
                symbols=symbols,
                grouped=grouped,
                source_code=source_code,
            )

        return ParsedDocument(
            repository_file=repository_file,
            source_code=source_code,
            symbols=symbols,
        )
    