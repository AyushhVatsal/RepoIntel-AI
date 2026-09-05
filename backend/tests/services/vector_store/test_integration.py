import uuid

import pytest

from app.db.database import SessionLocal
from app.models.chunk import Chunk, ChunkType
from app.models.embedding import Embedding
from app.models.repository import Repository, RepositoryStatus
from app.models.repository_file import (
    FileCategory,
    LanguageSupportTier,
    RepositoryFile,
)
from app.models.user import User
from app.services.vector_store.repository import VectorStoreRepository
from app.services.vector_store.service import VectorStoreService

@pytest.fixture
def db():
    session = SessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_pgvector_similarity_search(db):
    unique_id = uuid.uuid4().hex

    user = User(
        username=f"vector_test_{unique_id}",
        email=f"vector_test_{unique_id}@example.com",
        hashed_password="test-password",
        is_active=True,
    )

    db.add(user)
    db.flush()

    repository = Repository(
        owner_id=user.id,
        name=f"vector-test-{unique_id}",
        github_url=f"https://github.com/test/vector-{unique_id}",
        clone_path=f"/tmp/vector-test-{unique_id}",
        default_branch="main",
        status=RepositoryStatus.INDEXED,
        primary_language="Python",
        primary_framework=None,
        total_files=1,
        supported_files=1,
        skipped_files=0,
        repository_size=100,
    )

    db.add(repository)
    db.flush()

    repository_file = RepositoryFile(
        repository_id=repository.id,
        path=f"/tmp/vector-test-{unique_id}/example.py",
        relative_path="example.py",
        filename="example.py",
        extension=".py",
        language="python",
        category=FileCategory.SOURCE,
        support_tier=LanguageSupportTier.TIER_1,
        size=100,
        sha256_hash=None,
        is_binary=False,
    )

    db.add(repository_file)
    db.flush()

    chunk = Chunk(
        repository_id=repository.id,
        file_id=repository_file.id,
        chunk_index=0,
        chunk_type=ChunkType.FUNCTION,
        content="def hello():\n    return 'hello'",
        start_line=1,
        end_line=2,
        token_count=8,
        symbol_name="hello",
        qualified_name="example.hello",
        parent_symbol=None,
        metadata_={"language": "python"},
    )

    db.add(chunk)
    db.flush()

    query_vector = [0.1] * 384

    embedding = Embedding(
        chunk_id=chunk.id,
        model="test-model",
        dimensions=384,
        embedding=query_vector,
    )

    db.add(embedding)
    db.commit()

    repository_impl = VectorStoreRepository(db)

    results = repository_impl.similarity_search(
        query_vector=query_vector,
        repository_id=repository.id,
        model="test-model",
        top_k=10,
    )

    assert len(results) == 1

    result = results[0]

    assert result.chunk.id == chunk.id
    assert result.chunk.repository_id == repository.id
    assert result.chunk.file_id == repository_file.id
    assert result.chunk.content == "def hello():\n    return 'hello'"

    # Identical vectors should have cosine similarity approximately 1.
    assert result.score == pytest.approx(1.0, abs=1e-5)

def test_vector_store_service_persists_embedding(db):
    unique_id = uuid.uuid4().hex

    user = User(
        username=f"service_vector_test_{unique_id}",
        email=f"service_vector_test_{unique_id}@example.com",
        hashed_password="test-password",
        is_active=True,
    )

    db.add(user)
    db.flush()

    repository = Repository(
        owner_id=user.id,
        name=f"service-vector-test-{unique_id}",
        github_url=f"https://github.com/test/service-vector-{unique_id}",
        clone_path=f"/tmp/service-vector-test-{unique_id}",
        default_branch="main",
        status=RepositoryStatus.INDEXED,
        primary_language="Python",
        primary_framework=None,
        total_files=1,
        supported_files=1,
        skipped_files=0,
        repository_size=100,
    )

    db.add(repository)
    db.flush()

    repository_file = RepositoryFile(
        repository_id=repository.id,
        path=f"/tmp/service-vector-test-{unique_id}/example.py",
        relative_path="example.py",
        filename="example.py",
        extension=".py",
        language="python",
        category=FileCategory.SOURCE,
        support_tier=LanguageSupportTier.TIER_1,
        size=100,
        sha256_hash=None,
        is_binary=False,
    )

    db.add(repository_file)
    db.flush()

    chunk = Chunk(
        repository_id=repository.id,
        file_id=repository_file.id,
        chunk_index=0,
        chunk_type=ChunkType.FUNCTION,
        content="def service_test():\n    return True",
        start_line=1,
        end_line=2,
        token_count=8,
        symbol_name="service_test",
        qualified_name="example.service_test",
        parent_symbol=None,
        metadata_={"language": "python"},
    )

    db.add(chunk)
    db.flush()

    vector = [0.2] * 384

    service = VectorStoreService(db)

    result = service.store_embedding(
        chunk_id=chunk.id,
        model="test-service-model",
        dimensions=384,
        embedding=vector,
    )

    db.commit()

    assert result is not None
    assert result.chunk_id == chunk.id
    assert result.model == "test-service-model"
    assert result.dimensions == 384
    assert list(result.embedding) == pytest.approx(vector)

    stored_embedding = (
        db.query(Embedding)
        .filter(
            Embedding.chunk_id == chunk.id,
            Embedding.model == "test-service-model",
        )
        .one()
    )

    assert stored_embedding.id == result.id
    assert stored_embedding.chunk_id == chunk.id
    assert stored_embedding.dimensions == 384
    assert list(stored_embedding.embedding) == pytest.approx(vector)