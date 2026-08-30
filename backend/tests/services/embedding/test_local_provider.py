from app.services.embedding.providers.local import LocalEmbeddingProvider


MODEL_NAME = "BAAI/bge-small-en-v1.5"


def test_local_provider_generates_embeddings() -> None:
    provider = LocalEmbeddingProvider(MODEL_NAME)

    embeddings = provider.embed(
        [
            "JWT authentication service",
            "User repository implementation",
        ]
    )

    assert len(embeddings) == 2
    assert len(embeddings[0]) == 384
    assert len(embeddings[1]) == 384


def test_local_provider_metadata() -> None:
    provider = LocalEmbeddingProvider(MODEL_NAME)

    assert provider.model == MODEL_NAME
    assert provider.dimensions == 384