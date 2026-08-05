from __future__ import annotations

from app.models.repository_file import LanguageSupportTier

from app.services.parsers.generic.parser import GenericParser
from app.services.parsers.models.file_content import FileContent
from app.services.parsers.models.parsed_document import ParsedDocument
from app.services.parsers.tree_sitter.parser import TreeSitterParser


class ParserService:
    """
    Public entry point for the parser module.

    Responsible for selecting the appropriate parser
    implementation based on the file's support tier.
    """

    @classmethod
    def parse(
        cls,
        file: FileContent,
    ) -> ParsedDocument:

        support_tier = (
            file.repository_file.support_tier
        )

        if support_tier == LanguageSupportTier.TIER_1:
            return TreeSitterParser.parse(file)

        return GenericParser.parse(file)