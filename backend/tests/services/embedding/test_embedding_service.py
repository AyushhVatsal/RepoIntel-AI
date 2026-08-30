from unittest.mock import Mock

import pytest

from app.schemas.chunk import ChunkCreate
from app.services.embedding.cache import EmbeddingCache
from app.services.embedding.models.embedding_config import EmbeddingConfig
from app.services.embedding.service import EmbeddingService


@pytest.fixture
def config() -> EmbeddingConfig:
    return EmbeddingConfig(
        provider="test",
        model="test-model",
        dimensions=3,
        batch_size=2,
    )


@pytest.fixture
def provider() -> Mock:
    provider = Mock()
    provider.model = "test-model"
    provider.dimensions = 3
    provider.embed.side_effect = lambda texts: [
        [float(index)] * 3
        for index, _ in enumerate(texts, start=1)
    ]
    return provider


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
        symbol_name=None,
        qualified_name=None,
        parent_symbol=None,
        metadata={},
    )


def test_embed_generates_embeddings(
    config: EmbeddingConfig,
    provider: Mock,
) -> None:
    service = EmbeddingService(
        provider=provider,
        config=config,
    )

    chunks = [
        make_chunk(0, "authentication service"),
        make_chunk(1, "user repository"),
    ]

    results = service.embed(chunks)

    assert len(results) == 2

    assert results[0].repository_id == 1
    assert results[0].file_id == 10
    assert results[0].chunk_index == 0
    assert results[0].dimensions == 3
    assert results[0].cached is False

    provider.embed.assert_called_once()


def test_embed_uses_cache(
    config: EmbeddingConfig,
    provider: Mock,
) -> None:
    cache = EmbeddingCache()

    service = EmbeddingService(
        provider=provider,
        config=config,
        cache=cache,
    )

    chunks = [
        make_chunk(0, "authentication service"),
    ]

    first = service.embed(chunks)
    second = service.embed(chunks)

    assert first[0].cached is False
    assert second[0].cached is True

    assert provider.embed.call_count == 1


def test_embed_batches_chunks(
    config: EmbeddingConfig,
    provider: Mock,
) -> None:
    service = EmbeddingService(
        provider=provider,
        config=config,
    )

    chunks = [
        make_chunk(0, "chunk one"),
        make_chunk(1, "chunk two"),
        make_chunk(2, "chunk three"),
        make_chunk(3, "chunk four"),
        make_chunk(4, "chunk five"),
    ]

    service.embed(chunks)

    assert provider.embed.call_count == 3

    calls = provider.embed.call_args_list

    assert len(calls[0].args[0]) == 2
    assert len(calls[1].args[0]) == 2
    assert len(calls[2].args[0]) == 1


def test_embed_rejects_empty_chunk(
    config: EmbeddingConfig,
    provider: Mock,
) -> None:
    service = EmbeddingService(
        provider=provider,
        config=config,
    )

    with pytest.raises(ValueError, match="empty"):
        service.embed(
            [
                make_chunk(0, "   "),
            ]
        )


def test_embed_rejects_dimension_mismatch(
    provider: Mock,
) -> None:
    config = EmbeddingConfig(
        provider="test",
        model="test-model",
        dimensions=384,
    )

    provider.dimensions = 768

    with pytest.raises(ValueError, match="dimensions"):
        EmbeddingService(
            provider=provider,
            config=config,
        )