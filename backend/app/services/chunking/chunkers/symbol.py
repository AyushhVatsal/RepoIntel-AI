from app.schemas.chunk import ChunkCreate, ChunkType
from app.services.chunking.chunkers.base import BaseChunker
from app.services.chunking.token_counter import TokenCounter
from app.services.parsers.models.symbols import BaseSymbol


class SymbolChunker(BaseChunker):
    """Symbol-aware chunker for Tier 1 source files."""

    def __init__(self, max_tokens: int = 800) -> None:
        if max_tokens <= 0:
            raise ValueError("max_tokens must be greater than 0")

        self.max_tokens = max_tokens
        self.token_counter = TokenCounter()

    def chunk(
        self,
        *,
        repository_id: int,
        file_id: int,
        source_code: str,
        symbols: list[BaseSymbol],
    ) -> list[ChunkCreate]:
        if not source_code.strip():
            return []

        lines = source_code.splitlines()
        chunks: list[ChunkCreate] = []

        for symbol in symbols:
            start_line = symbol.location.start_line
            end_line = symbol.location.end_line

            content = "\n".join(
                lines[start_line - 1:end_line]
            ).strip()

            if not content:
                continue

            chunk_type = self._get_chunk_type(symbol)
            parts = self._split_oversized(content)

            for part_index, (part_content, token_count) in enumerate(parts):
                chunks.append(
                    ChunkCreate(
                        repository_id=repository_id,
                        file_id=file_id,
                        chunk_index=len(chunks),
                        chunk_type=chunk_type,
                        content=part_content,
                        start_line=start_line,
                        end_line=end_line,
                        token_count=token_count,
                        symbol_name=symbol.name,
                        qualified_name=symbol.qualified_name,
                        parent_symbol=symbol.parent_symbol,
                        metadata={
                            "chunking_strategy": "symbol",
                            "symbol_id": symbol.symbol_id,
                            "symbol_part": part_index,
                            "symbol_parts": len(parts),
                            "language": symbol.language,
                        },
                    )
                )

        return chunks

    def _split_oversized(
        self,
        content: str,
    ) -> list[tuple[str, int]]:
        """Split oversized symbol content into token-limited pieces."""

        tokens = self.token_counter.encode(content)

        if len(tokens) <= self.max_tokens:
            return [(content, len(tokens))]

        parts: list[tuple[str, int]] = []

        for start in range(0, len(tokens), self.max_tokens):
            token_slice = tokens[start:start + self.max_tokens]

            text = self.token_counter.decode(token_slice)

            parts.append(
                (text, len(token_slice))
            )

        return parts

    @staticmethod
    def _get_chunk_type(symbol: BaseSymbol) -> ChunkType:
        symbol_type = symbol.type.value

        if symbol_type == "class":
            return ChunkType.CLASS

        if symbol_type in {"struct", "interface", "enum"}:
            return ChunkType.CLASS

        if symbol_type == "method":
            return ChunkType.METHOD

        if symbol_type == "function":
            return ChunkType.FUNCTION

        if symbol_type == "import":
            return ChunkType.IMPORT

        if symbol_type in {"variable", "field"}:
            return ChunkType.VARIABLE

        if symbol_type == "module":
            return ChunkType.MODULE

        return ChunkType.TEXT