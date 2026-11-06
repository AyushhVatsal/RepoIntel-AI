import numpy as np

from app.services.embedding.providers import local
from app.services.embedding.providers.local import LocalEmbeddingProvider

MODEL_NAME = "BAAI/bge-small-en-v1.5"


class FakeFirstModule:
    def tokenize(self, texts):
        return {"input_ids": texts}


class FakeInputIds:
    def __init__(self, count):
        self.count = count

    def numel(self):
        return self.count


class FakeSentenceTransformer:
    def __init__(self, _model_name):
        self.first_module = FakeFirstModule()
        self.device = "cpu"
        self.encode_kwargs = None

    def _first_module(self):
        return self.first_module

    def preprocess(self, texts, **_kwargs):
        return {"input_ids": FakeInputIds(len(texts))}

    def forward(self, features):
        return features

    def get_embedding_dimension(self):
        return 3

    def encode(self, texts, **kwargs):
        self.encode_kwargs = kwargs
        batch_size = kwargs["batch_size"]
        for start in range(0, len(texts), batch_size):
            self.forward(self.preprocess(texts[start : start + batch_size]))
        return np.tile(np.array([[0.6, 0.8, 0.0]]), (len(texts), 1))


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


def test_provider_uses_bounded_batch_and_keeps_normalized_vectors(
    monkeypatch,
) -> None:
    fake_model = FakeSentenceTransformer("BAAI/bge-small-en-v1.5")
    monkeypatch.setattr(
        local,
        "SentenceTransformer",
        lambda model_name: fake_model,
    )
    provider = local.LocalEmbeddingProvider("BAAI/bge-small-en-v1.5")

    vectors = provider.embed([f"chunk {i}" for i in range(64)])

    assert fake_model.encode_kwargs == {
        "batch_size": 32,
        "show_progress_bar": False,
        "convert_to_numpy": True,
        "normalize_embeddings": True,
    }
    assert len(vectors) == 64
    assert all(len(vector) == 3 for vector in vectors)
    assert vectors[0] == [0.6, 0.8, 0.0]
    profile = provider.profile_snapshot()
    assert profile["provider_calls"] == 1
    assert profile["model_batches"] == 2
    assert profile["token_positions"] == 64

    provider.reset_profile()
    assert provider.profile_snapshot()["embeddings"] == 0


def test_cuda_provider_retries_with_smaller_batch_on_oom(monkeypatch) -> None:
    fake_model = FakeSentenceTransformer("BAAI/bge-small-en-v1.5")
    fake_model.device = "cuda:0"
    original_encode = fake_model.encode
    attempted_batch_sizes = []

    def encode_with_memory_limit(texts, **kwargs):
        batch_size = kwargs["batch_size"]
        attempted_batch_sizes.append(batch_size)
        if batch_size > 8:
            raise RuntimeError("CUDA error: out of memory")
        return original_encode(texts, **kwargs)

    monkeypatch.setattr(fake_model, "encode", encode_with_memory_limit)
    monkeypatch.setattr(local.torch.cuda, "empty_cache", lambda: None)
    monkeypatch.setattr(
        local,
        "SentenceTransformer",
        lambda _model_name: fake_model,
    )
    provider = local.LocalEmbeddingProvider("BAAI/bge-small-en-v1.5")

    vectors = provider.embed([f"chunk {i}" for i in range(64)])

    assert attempted_batch_sizes == [16, 8]
    assert len(vectors) == 64
    assert vectors[0] == [0.6, 0.8, 0.0]
