import uuid

import pytest

from app.models.chunk import Chunk, ChunkType
from app.models.embedding import Embedding
from app.models.repository import Repository, RepositoryStatus
from app.models.repository_file import (
    FileCategory,
    LanguageSupportTier,
    RepositoryFile,
)
from app.models.user import User

@pytest.fixture

def retrieval_dataset(db):

    unique_id = uuid.uuid4().hex

    user = User(

        username=f"filter_test_{unique_id}",

        email=f"filter_test_{unique_id}@example.com",

        hashed_password="test-password",

        is_active=True,

    )

    db.add(user)

    db.flush()

    repository = Repository(

        owner_id=user.id,

        name=f"filter-test-{unique_id}",

        github_url=f"https://github.com/test/filter-{unique_id}",

        clone_path=f"/tmp/filter-test-{unique_id}",

        default_branch="main",

        status=RepositoryStatus.INDEXED,

        primary_language="Python",

        primary_framework=None,

        total_files=4,

        supported_files=4,

        skipped_files=0,

        repository_size=400,

    )

    db.add(repository)

    db.flush()

    other_repository = Repository(

        owner_id=user.id,

        name=f"other-filter-test-{unique_id}",

        github_url=f"https://github.com/test/other-filter-{unique_id}",

        clone_path=f"/tmp/other-filter-test-{unique_id}",

        default_branch="main",

        status=RepositoryStatus.INDEXED,

        primary_language="Python",

        primary_framework=None,

        total_files=1,

        supported_files=1,

        skipped_files=0,

        repository_size=100,

    )

    db.add(other_repository)

    db.flush()

    files = [

        RepositoryFile(

            repository_id=repository.id,

            path=f"/tmp/filter-test-{unique_id}/auth.py",

            relative_path="backend/auth/auth.py",

            filename="auth.py",

            extension=".py",

            language="python",

            category=FileCategory.SOURCE,

            support_tier=LanguageSupportTier.TIER_1,

            size=100,

            sha256_hash=None,

            is_binary=False,

        ),

        RepositoryFile(

            repository_id=repository.id,

            path=f"/tmp/filter-test-{unique_id}/user.py",

            relative_path="backend/models/user.py",

            filename="user.py",

            extension=".py",

            language="python",

            category=FileCategory.SOURCE,

            support_tier=LanguageSupportTier.TIER_1,

            size=100,

            sha256_hash=None,

            is_binary=False,

        ),

        RepositoryFile(

            repository_id=repository.id,

            path=f"/tmp/filter-test-{unique_id}/server.ts",

            relative_path="frontend/server.ts",

            filename="server.ts",

            extension=".ts",

            language="typescript",

            category=FileCategory.SOURCE,

            support_tier=LanguageSupportTier.TIER_1,

            size=100,

            sha256_hash=None,

            is_binary=False,

        ),

        RepositoryFile(

            repository_id=repository.id,

            path=f"/tmp/filter-test-{unique_id}/README.md",

            relative_path="README.md",

            filename="README.md",

            extension=".md",

            language="markdown",

            category=FileCategory.DOCUMENTATION,

            support_tier=LanguageSupportTier.TIER_0,

            size=100,

            sha256_hash=None,

            is_binary=False,

        ),

    ]

    db.add_all(files)

    db.flush()

    chunks = [

        Chunk(

            repository_id=repository.id,

            file_id=files[0].id,

            chunk_index=0,

            chunk_type=ChunkType.FUNCTION,

            content="def authenticate_user(username, password):",

            start_line=1,

            end_line=2,

            token_count=10,

            symbol_name="authenticate_user",

            qualified_name="auth.authenticate_user",

            parent_symbol=None,

            metadata_={"language": "python"},

        ),

        Chunk(

            repository_id=repository.id,

            file_id=files[1].id,

            chunk_index=0,

            chunk_type=ChunkType.CLASS,

            content="class UserRepository:",

            start_line=1,

            end_line=5,

            token_count=10,

            symbol_name="UserRepository",

            qualified_name="user.UserRepository",

            parent_symbol=None,

            metadata_={"language": "python"},

        ),

        Chunk(

            repository_id=repository.id,

            file_id=files[2].id,

            chunk_index=0,

            chunk_type=ChunkType.FUNCTION,

            content="function authenticateUser(username) {}",

            start_line=1,

            end_line=3,

            token_count=10,

            symbol_name="authenticateUser",

            qualified_name="server.authenticateUser",

            parent_symbol=None,

            metadata_={"language": "typescript"},

        ),

    ]

    db.add_all(chunks)

    db.flush()

    # Same vector is intentional: filtering behavior is the thing

    # this integration test is validating, not ranking quality.

    query_vector = [0.1] * 384

    embeddings = [

        Embedding(

            chunk_id=chunk.id,

            model="filter-test-model",

            dimensions=384,

            embedding=query_vector,

        )

        for chunk in chunks

    ]

    # Add a chunk belonging to another repository.

    other_file = RepositoryFile(

        repository_id=other_repository.id,

        path=f"/tmp/other-filter-test-{unique_id}/auth.py",

        relative_path="auth.py",

        filename="auth.py",

        extension=".py",

        language="python",

        category=FileCategory.SOURCE,

        support_tier=LanguageSupportTier.TIER_1,

        size=100,

        sha256_hash=None,

        is_binary=False,

    )

    db.add(other_file)

    db.flush()

    other_chunk = Chunk(

        repository_id=other_repository.id,

        file_id=other_file.id,

        chunk_index=0,

        chunk_type=ChunkType.FUNCTION,

        content="def authenticate_user():",

        start_line=1,

        end_line=2,

        token_count=8,

        symbol_name="authenticate_user",

        qualified_name="auth.authenticate_user",

        parent_symbol=None,

        metadata_={"language": "python"},

    )

    db.add(other_chunk)

    db.flush()

    embeddings.append(

        Embedding(

            chunk_id=other_chunk.id,

            model="filter-test-model",

            dimensions=384,

            embedding=query_vector,

        )

    )

    db.add_all(embeddings)

    db.commit()

    return {

        "repository_id": repository.id,

        "other_repository_id": other_repository.id,

        "chunks": chunks,

        "other_chunk": other_chunk,

        "query_vector": query_vector,

    }