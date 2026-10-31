from unittest.mock import MagicMock

from app.models.chunk import Chunk
from app.models.repository_file import RepositoryFile
from app.services.retrieval.hydrator import RetrievalResultHydrator
from app.services.retrieval.result import RetrievalResult


def test_hydrate_preserves_order_and_scores():
    db = MagicMock()

    chunk_1 = MagicMock(spec=Chunk)
    chunk_1.id = 10
    chunk_1.file_id = 100
    chunk_1.content = "def authenticate_user():"

    chunk_2 = MagicMock(spec=Chunk)
    chunk_2.id = 20
    chunk_2.file_id = 200
    chunk_2.content = "class UserRepository:"

    file_1 = MagicMock(spec=RepositoryFile)
    file_1.relative_path = "backend/auth.py"

    file_2 = MagicMock(spec=RepositoryFile)
    file_2.relative_path = "backend/user.py"

    db.execute.return_value.all.return_value = [
        (chunk_1, file_1.relative_path),
        (chunk_2, file_2.relative_path),
    ]

    results = [
        RetrievalResult(
            chunk_id=20,
            score=0.031,
            dense_score=0.82,
            retrieval_score=0.031,
        ),
        RetrievalResult(
            chunk_id=10,
            score=0.030,
            dense_score=0.91,
            retrieval_score=0.030,
        ),
    ]

    hydrator = RetrievalResultHydrator(db)

    hydrated = hydrator.hydrate(results)

    assert len(hydrated) == 2

    # RRF ordering must be preserved.
    assert hydrated[0].chunk_id == 20
    assert hydrated[1].chunk_id == 10

    # Dense cosine similarity must remain separate.
    assert hydrated[0].similarity_score == 0.82
    assert hydrated[1].similarity_score == 0.91

    # Final retrieval score is RRF.
    assert hydrated[0].retrieval_score == 0.031
    assert hydrated[1].retrieval_score == 0.030

    assert hydrated[0].file_path == "backend/user.py"
    assert hydrated[1].file_path == "backend/auth.py"
