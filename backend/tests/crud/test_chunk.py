from unittest.mock import MagicMock

from app.crud.chunk import ChunkCRUD
from app.models.chunk import Chunk
from app.schemas.chunk import ChunkCreate, ChunkType


def make_chunk() -> ChunkCreate:
    return ChunkCreate(
        repository_id=1,
        file_id=10,
        chunk_index=0,
        chunk_type=ChunkType.FUNCTION,
        content="def hello():\n    return 'hello'",
        start_line=1,
        end_line=2,
        token_count=8,
        symbol_name="hello",
        qualified_name="module.hello",
        parent_symbol=None,
        metadata={"language": "python"},
    )


def test_create():
    db = MagicMock()
    crud = ChunkCRUD()

    chunk_in = make_chunk()

    result = crud.create(db, chunk_in)

    assert isinstance(result, Chunk)
    assert result.repository_id == 1
    assert result.file_id == 10
    assert result.chunk_index == 0
    assert result.content == "def hello():\n    return 'hello'"
    assert result.symbol_name == "hello"
    assert result.metadata_ == {"language": "python"}

    db.add.assert_called_once_with(result)
    db.commit.assert_called_once_with()
    db.refresh.assert_called_once_with(result)


def test_create_many():
    db = MagicMock()
    crud = ChunkCRUD()

    chunks = [
        make_chunk(),
        make_chunk().model_copy(
            update={
                "chunk_index": 1,
                "content": "def world():\n    return 'world'",
                "symbol_name": "world",
                "qualified_name": "module.world",
            }
        ),
    ]

    result = crud.create_many(db, chunks)

    assert len(result) == 2

    assert all(isinstance(chunk, Chunk) for chunk in result)

    assert result[0].chunk_index == 0
    assert result[1].chunk_index == 1

    db.add_all.assert_called_once()
    db.commit.assert_called_once_with()

    assert db.refresh.call_count == 2


def test_create_many_empty():
    db = MagicMock()
    crud = ChunkCRUD()

    result = crud.create_many(db, [])

    assert result == []

    db.add_all.assert_not_called()
    db.commit.assert_not_called()
    db.refresh.assert_not_called()


def test_get():
    db = MagicMock()
    crud = ChunkCRUD()

    expected = MagicMock(spec=Chunk)
    db.get.return_value = expected

    result = crud.get(db, 123)

    assert result is expected
    db.get.assert_called_once_with(Chunk, 123)


def test_get_by_repository():
    db = MagicMock()
    crud = ChunkCRUD()

    chunks = [
        MagicMock(spec=Chunk),
        MagicMock(spec=Chunk),
    ]

    db.scalars.return_value.all.return_value = chunks

    result = crud.get_by_repository(db, 1)

    assert result == chunks

    db.scalars.assert_called_once()


def test_get_by_file():
    db = MagicMock()
    crud = ChunkCRUD()

    chunks = [
        MagicMock(spec=Chunk),
        MagicMock(spec=Chunk),
    ]

    db.scalars.return_value.all.return_value = chunks

    result = crud.get_by_file(db, 10)

    assert result == chunks

    db.scalars.assert_called_once()


def test_delete():
    db = MagicMock()
    crud = ChunkCRUD()

    chunk = MagicMock(spec=Chunk)
    db.get.return_value = chunk

    crud.delete(db, 123)

    db.get.assert_called_once_with(Chunk, 123)
    db.delete.assert_called_once_with(chunk)
    db.commit.assert_called_once_with()


def test_delete_missing_chunk():
    db = MagicMock()
    crud = ChunkCRUD()

    db.get.return_value = None

    crud.delete(db, 123)

    db.get.assert_called_once_with(Chunk, 123)
    db.delete.assert_not_called()
    db.commit.assert_not_called()


def test_delete_by_repository():
    db = MagicMock()
    crud = ChunkCRUD()

    crud.delete_by_repository(db, 1)

    db.execute.assert_called_once()
    db.commit.assert_called_once_with()


def test_delete_by_file():
    db = MagicMock()
    crud = ChunkCRUD()

    crud.delete_by_file(db, 10)

    db.execute.assert_called_once()
    db.commit.assert_called_once_with()