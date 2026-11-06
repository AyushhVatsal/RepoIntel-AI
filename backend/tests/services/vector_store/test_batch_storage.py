from types import SimpleNamespace

import pytest

from app.services.vector_store import service as vector_store_service_module
from app.services.vector_store.service import VectorStoreService


def test_batch_embedding_storage_validates_and_calls_bulk_upsert(monkeypatch):
    db = object()
    service = object.__new__(VectorStoreService)
    service.repository = SimpleNamespace(db=db)
    saved = []
    monkeypatch.setattr(
        vector_store_service_module,
        "upsert_many",
        lambda actual_db, rows: saved.append((actual_db, rows)),
    )

    service.store_embeddings([
        (1, "model", 3, [0.1, 0.2, 0.3]),
        (2, "model", 3, [0.4, 0.5, 0.6]),
    ])

    assert saved == [(
        db,
        [
            {
                "chunk_id": 1,
                "model": "model",
                "dimensions": 3,
                "embedding": [0.1, 0.2, 0.3],
            },
            {
                "chunk_id": 2,
                "model": "model",
                "dimensions": 3,
                "embedding": [0.4, 0.5, 0.6],
            },
        ],
    )]


def test_batch_embedding_storage_rejects_invalid_dimensions():
    service = object.__new__(VectorStoreService)
    service.repository = SimpleNamespace(db=object())

    with pytest.raises(ValueError, match="dimension mismatch"):
        service.store_embeddings([(1, "model", 2, [0.1])])
