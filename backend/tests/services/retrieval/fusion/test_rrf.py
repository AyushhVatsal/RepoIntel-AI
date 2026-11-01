# pyrefly: ignore[missing-import]
from pytest import raises

from app.services.retrieval.fusion.rrf import RRFFusion
from app.services.retrieval.result import RetrievalResult


def test_rrf_fuses_multiple_ranked_lists():
    fusion = RRFFusion(k=60)

    dense_results = [
        RetrievalResult(chunk_id=1, score=0.95),
        RetrievalResult(chunk_id=2, score=0.90),
        RetrievalResult(chunk_id=3, score=0.85),
    ]

    lexical_results = [
        RetrievalResult(chunk_id=2, score=5.0),
        RetrievalResult(chunk_id=4, score=4.0),
        RetrievalResult(chunk_id=1, score=3.0),
    ]

    results = fusion.fuse(
        [dense_results, lexical_results],
        top_k=4,
    )

    assert [result.chunk_id for result in results] == [
        2,
        1,
        4,
        3,
    ]


def test_rrf_combines_scores_for_documents_present_in_multiple_lists():
    fusion = RRFFusion(k=60)

    results = fusion.fuse(
        [
            [
                RetrievalResult(chunk_id=1, score=0.9),
            ],
            [
                RetrievalResult(chunk_id=1, score=4.0),
            ],
        ],
        top_k=1,
    )

    assert len(results) == 1
    assert results[0].chunk_id == 1
    assert results[0].score == (1 / 61) + (1 / 61)


def test_rrf_applies_source_weights_to_rank_contributions():
    fusion = RRFFusion(k=60, source_weights=(0.8, 0.2))

    results = fusion.fuse(
        [
            [
                RetrievalResult(chunk_id=1, score=0.9),
                RetrievalResult(chunk_id=2, score=0.8),
            ],
            [
                RetrievalResult(chunk_id=2, score=4.0),
                RetrievalResult(chunk_id=3, score=3.0),
            ],
        ],
        top_k=3,
    )

    assert [result.chunk_id for result in results] == [2, 1, 3]
    assert results[0].score == (0.8 / 62) + (0.2 / 61)


def test_rrf_source_weights_must_match_result_lists():
    fusion = RRFFusion(source_weights=(0.8, 0.2))

    with raises(ValueError, match="must match"):
        fusion.fuse([[RetrievalResult(chunk_id=1, score=1.0)]], top_k=1)


def test_rrf_respects_top_k():
    fusion = RRFFusion()

    results = fusion.fuse(
        [
            [
                RetrievalResult(chunk_id=1, score=0.9),
                RetrievalResult(chunk_id=2, score=0.8),
                RetrievalResult(chunk_id=3, score=0.7),
            ],
        ],
        top_k=2,
    )

    assert len(results) == 2


def test_rrf_returns_empty_for_non_positive_top_k():
    fusion = RRFFusion()

    assert fusion.fuse([], top_k=0) == []
    assert fusion.fuse([], top_k=-1) == []


def test_rrf_rejects_invalid_k():
    with raises(ValueError, match="k must be greater than 0"):
        RRFFusion(k=0)

    with raises(ValueError, match="k must be greater than 0"):
        RRFFusion(k=-1)


def test_rrf_deduplicates_chunks_within_same_list():
    fusion = RRFFusion(k=60)

    results = fusion.fuse(
        [
            [
                RetrievalResult(chunk_id=1, score=0.9),
                RetrievalResult(chunk_id=1, score=0.8),
            ],
        ],
        top_k=1,
    )

    assert len(results) == 1
    assert results[0].chunk_id == 1
    assert results[0].score == (1 / 61)
