from app.schemas.chunk import ChunkCreate
from app.services.embedding.models.embedding_config import EmbeddingConfig
from app.services.embedding.providers.local import LocalEmbeddingProvider
from app.services.embedding.service import EmbeddingService


MODEL_NAME = "BAAI/bge-small-en-v1.5"


def make_chunk(
    chunk_index: int,
    content: str,
) -> ChunkCreate:
    return ChunkCreate(
        repository_id=1,
        file_id=10,
        chunk_index=chunk_index,
        chunk_type="function",
        content=content,
        start_line=1,
        end_line=10,
        token_count=10,
        symbol_name="authenticate_user",
        qualified_name="AuthService.authenticate_user",
        parent_symbol="AuthService",
        metadata={},
    )


def test_chunk_create_to_embedding() -> None:
    provider = LocalEmbeddingProvider(MODEL_NAME)

    config = EmbeddingConfig(
        provider="sentence_transformers",
        model=MODEL_NAME,
        dimensions=384,
        batch_size=64,
    )

    service = EmbeddingService(
        provider=provider,
        config=config,
    )

    chunks = [
        make_chunk(
            0,
            """
            def authenticate_user(username, password):
                user = get_user(username)
                return verify_password(
                    password,
                    user.password_hash,
                )
            """,
        ),
        make_chunk(
            1,
            """
            def create_access_token(user_id):
                return generate_jwt_token(user_id)
            """,
        ),
    ]

    results = service.embed(chunks)

    assert len(results) == 2

    for result in results:
        assert result.repository_id == 1
        assert result.file_id == 10
        assert result.dimensions == 384
        assert len(result.vector) == 384
        assert result.model == MODEL_NAME
        assert result.cached is False