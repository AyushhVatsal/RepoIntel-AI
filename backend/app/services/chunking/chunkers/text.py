from app.schemas.chunk import ChunkCreate, ChunkType
from app.services.chunking.chunkers.base import BaseChunker
from app.services.chunking.token_counter import TokenCounter


class TextChunker(BaseChunker):
    """Token-based chunker for Tier 0 files."""

    def __init__(
        self,
        max_tokens: int = 800,
        overlap_tokens: int = 100,
    ) -> None:
        if max_tokens <= 0:
            raise ValueError("max_tokens must be greater than 0")

        if overlap_tokens < 0:
            raise ValueError("overlap_tokens cannot be negative")

        if overlap_tokens >= max_tokens:
            raise ValueError(
                "overlap_tokens must be smaller than max_tokens"
            )

        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.token_counter = TokenCounter()

    def chunk(
        self,
        *,
        repository_id: int,
        file_id: int,
        source_code: str,
    ) -> list[ChunkCreate]:
        if not source_code.strip():
            return []

        lines = source_code.splitlines(keepends=True)

        chunks: list[ChunkCreate] = []
        current_tokens: list[int] = []
        current_start_line = 1

        line_token_ranges: list[tuple[int, int, int]] = []

        for line_number, line in enumerate(lines, start=1):
            tokens = self.token_counter.encode(line)

            start = len(current_tokens)
            current_tokens.extend(tokens)
            end = len(current_tokens)

            line_token_ranges.append(
                (line_number, start, end)
            )

            if len(current_tokens) >= self.max_tokens:
                content = self.token_counter.decode(current_tokens)

                chunks.append(
                    ChunkCreate(
                        repository_id=repository_id,
                        file_id=file_id,
                        chunk_index=len(chunks),
                        chunk_type=ChunkType.TEXT,
                        content=content,
                        start_line=current_start_line,
                        end_line=line_number,
                        token_count=len(current_tokens),
                        metadata={
                            "chunking_strategy": "text",
                        },
                    )
                )

                overlap = current_tokens[-self.overlap_tokens:]
                current_tokens = overlap
                current_start_line = line_number

        if current_tokens:
            content = self.token_counter.decode(current_tokens)

            chunks.append(
                ChunkCreate(
                    repository_id=repository_id,
                    file_id=file_id,
                    chunk_index=len(chunks),
                    chunk_type=ChunkType.TEXT,
                    content=content,
                    start_line=current_start_line,
                    end_line=len(lines),
                    token_count=len(current_tokens),
                    metadata={
                        "chunking_strategy": "text",
                    },
                )
            )

        return chunks