from app.schemas.chunk import ChunkCreate


class ChunkValidator:
    """Validates chunks before persistence."""

    def validate(self, chunk: ChunkCreate) -> None:
        if not chunk.content.strip():
            raise ValueError("Chunk content cannot be empty")

        if chunk.start_line > chunk.end_line:
            raise ValueError(
                "Chunk start_line cannot exceed end_line"
            )

        if chunk.token_count <= 0:
            raise ValueError(
                "Chunk token_count must be greater than zero"
            )

        if chunk.chunk_index < 0:
            raise ValueError(
                "Chunk index cannot be negative"
            )

    def validate_all(
        self,
        chunks: list[ChunkCreate],
    ) -> None:
        seen_indexes: set[int] = set()

        for chunk in chunks:
            self.validate(chunk)

            if chunk.chunk_index in seen_indexes:
                raise ValueError(
                    f"Duplicate chunk index: {chunk.chunk_index}"
                )

            seen_indexes.add(chunk.chunk_index)