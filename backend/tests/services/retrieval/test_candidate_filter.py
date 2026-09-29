from app.db.database import SessionLocal
from app.models.repository_file import FileRole
from app.services.retrieval.candidate_filter import (
    RetrievalCandidateFilter,
)
from app.services.retrieval.result import RetrievalResult


def test_exclude_roles(retrieval_dataset):
    db = SessionLocal()

    try:
        candidate_filter = RetrievalCandidateFilter(db)

        results = [
            RetrievalResult(
                chunk_id=chunk.id,
                score=1.0,
                dense_score=1.0,
            )
            for chunk in retrieval_dataset["chunks"]
        ]

        filtered = candidate_filter.exclude_roles(
            results,
            roles=[
                FileRole.TEST,
                FileRole.FIXTURE,
            ],
        )

        assert {
            result.chunk_id
            for result in filtered
        } == {
            chunk.id
            for chunk in retrieval_dataset["chunks"]
        }

    finally:
        db.close()

def test_exclude_roles(db, retrieval_dataset):
    candidate_filter = RetrievalCandidateFilter(db)

    results = [
        RetrievalResult(
            chunk_id=chunk.id,
            score=1.0,
            dense_score=1.0,
        )
        for chunk in retrieval_dataset["chunks"]
    ]

    filtered = candidate_filter.exclude_roles(
        results,
        roles=[FileRole.TEST, FileRole.FIXTURE],
    )

    filtered_ids = {
        result.chunk_id
        for result in filtered
    }

    assert retrieval_dataset["chunks"][3].id not in filtered_ids
    assert retrieval_dataset["chunks"][4].id not in filtered_ids

    assert retrieval_dataset["chunks"][0].id in filtered_ids
    assert retrieval_dataset["chunks"][1].id in filtered_ids
    assert retrieval_dataset["chunks"][2].id in filtered_ids
