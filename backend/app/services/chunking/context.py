from app.schemas.chunk import ChunkCreate


class ContextPreserver:
    """Adds lightweight parent/file context to chunks."""

    def enrich(
        self,
        chunk: ChunkCreate,
        *,
        file_path: str | None = None,
        module_name: str | None = None,
    ) -> ChunkCreate:
        metadata = dict(chunk.metadata)

        if file_path:
            metadata["file_path"] = file_path

        if module_name:
            metadata["module_name"] = module_name

        if chunk.parent_symbol:
            metadata["parent_symbol"] = chunk.parent_symbol

        return chunk.model_copy(
            update={"metadata": metadata}
        )