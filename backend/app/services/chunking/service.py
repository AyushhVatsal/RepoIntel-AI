from app.models.repository_file import LanguageSupportTier
from app.schemas.chunk import ChunkCreate
from app.services.chunking.factory import ChunkerFactory
from app.services.chunking.metadata import MetadataGenerator
from app.services.chunking.validators import ChunkValidator
from app.services.parsers.models.parsed_document import ParsedDocument


class ChunkingService:
    """Main entry point for converting parsed documents into chunks."""

    def __init__(self) -> None:
        self.factory = ChunkerFactory()
        self.metadata_generator = MetadataGenerator()
        self.validator = ChunkValidator()

    def chunk(
        self,
        parsed_document: ParsedDocument,
        *,
        support_tier: LanguageSupportTier,
    ) -> list[ChunkCreate]:
        """Generate validated chunks from a parsed document."""

        if not parsed_document.source_code.strip():
            return []

        if support_tier == LanguageSupportTier.NONE:
            return []

        repository_file = parsed_document.repository_file

        chunker = self.factory.get_chunker(
            support_tier.value
        )

        if support_tier == LanguageSupportTier.TIER_1:
            chunks = chunker.chunk(
                repository_id=repository_file.repository_id,
                file_id=repository_file.id,
                source_code=parsed_document.source_code,
                symbols=parsed_document.symbols,
            )
        else:
            chunks = chunker.chunk(
                repository_id=repository_file.repository_id,
                file_id=repository_file.id,
                source_code=parsed_document.source_code,
            )

        enriched_chunks = []

        for chunk in chunks:
            metadata = self.metadata_generator.generate(
                chunk,
                language=repository_file.language,
                file_path=repository_file.relative_path,
                support_tier=support_tier.value,
            )

            enriched_chunks.append(
                chunk.model_copy(
                    update={"metadata": metadata}
                )
            )

        self.validator.validate_all(enriched_chunks)

        return enriched_chunks