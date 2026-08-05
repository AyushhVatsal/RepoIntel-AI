from __future__ import annotations

from app.services.parsers.models.file_content import FileContent
from app.services.parsers.models.parsed_document import ParsedDocument


class GenericParser:
    """
    Generic parser for Tier 0 languages.

    Produces a ParsedDocument without performing AST analysis.
    """

    @classmethod
    def parse(
        cls,
        file: FileContent,
    ) -> ParsedDocument:
        source_code = file.content.decode(
            "utf-8",
            errors="replace",
        )

        return ParsedDocument(
            repository_file=file.repository_file,
            source_code=source_code,
        )