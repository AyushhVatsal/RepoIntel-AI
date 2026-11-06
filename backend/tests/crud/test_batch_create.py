from app.crud.chunk import chunk_crud
from app.crud.repository_file import repository_file_crud
from app.models.repository_file import (
    FileCategory,
    FileRole,
    LanguageSupportTier,
)
from app.schemas.chunk import ChunkCreate, ChunkType
from app.schemas.repository_file import RepositoryFileCreate


class FakeSession:
    def __init__(self):
        self.added = []
        self.committed = False
        self.flushed = False

    def add_all(self, rows):
        self.added.extend(rows)

    def commit(self):
        self.committed = True

    def flush(self):
        self.flushed = True

    def refresh(self, _row):
        raise AssertionError("bulk indexing should not refresh rows")


def test_repository_file_bulk_create_flushes_once_without_refreshes():
    db = FakeSession()
    file_in = RepositoryFileCreate(
        repository_id=1,
        path="/repo/main.py",
        relative_path="main.py",
        filename="main.py",
        extension=".py",
        language="python",
        category=FileCategory.SOURCE,
        role=FileRole.SOURCE,
        support_tier=LanguageSupportTier.TIER_1,
        size=12,
        sha256_hash="hash",
        is_binary=False,
    )

    rows = repository_file_crud.create_many(db, [file_in], commit=False)

    assert len(rows) == 1
    assert db.flushed
    assert not db.committed


def test_chunk_bulk_create_defers_flush_to_outer_batch():
    db = FakeSession()
    chunk_in = ChunkCreate(
        repository_id=1,
        file_id=2,
        chunk_index=0,
        chunk_type=ChunkType.FUNCTION,
        content="def f(): pass",
        start_line=1,
        end_line=1,
        token_count=4,
    )

    rows = chunk_crud.create_many(db, [chunk_in], commit=False)

    assert len(rows) == 1
    assert not db.flushed
    assert not db.committed
