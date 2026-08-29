from app.schemas.chunk import ChunkCreate


class MetadataGenerator:
    """Generates common metadata for chunks."""

    def generate(
        self,
        chunk: ChunkCreate,
        *,
        language: str | None = None,
        file_path: str | None = None,
        support_tier: str | None = None,
    ) -> dict:
        metadata = dict(chunk.metadata)

        if language:
            metadata["language"] = language

        if file_path:
            metadata["file_path"] = file_path

        if support_tier:
            metadata["support_tier"] = support_tier

        metadata["start_line"] = chunk.start_line
        metadata["end_line"] = chunk.end_line
        metadata["chunk_type"] = chunk.chunk_type.value

        if chunk.symbol_name:
            metadata["symbol_name"] = chunk.symbol_name

        if chunk.qualified_name:
            metadata["qualified_name"] = chunk.qualified_name

        if chunk.parent_symbol:
            metadata["parent_symbol"] = chunk.parent_symbol

        return metadata