import pytest

from app.services.retrieval.fusion.weighted import WeightedFusion
from app.services.retrieval.result import RetrievalResult


def test_weighted_fusion_uses_90_10_weighting() -> None:
    fusion = WeightedFusion(
        rrf_weight=0.9,
        cross_encoder_weight=0.1,
    )

    rrf_results = [
        RetrievalResult(
            chunk_id=1,
            score=1.0,
        ),
        RetrievalResult(
            chunk_id=2,
            score=0.5,
        ),
    ]

    cross_encoder_results = [
        RetrievalResult(
            chunk_id=1,
            score=0.0,
        ),
        RetrievalResult(
            chunk_id=2,
            score=1.0,
        ),
    ]

    results = fusion.fuse(
        rrf_results=rrf_results,
        cross_encoder_results=cross_encoder_results,
        top_k=2,
    )

    assert [result.chunk_id for result in results] == [1, 2]


def test_weighted_fusion_normalizes_scores() -> None:
    fusion = WeightedFusion(
        rrf_weight=0.5,
        cross_encoder_weight=0.5,
    )

    rrf_results = [
        RetrievalResult(chunk_id=1, score=100.0),
        RetrievalResult(chunk_id=2, score=50.0),
    ]

    cross_encoder_results = [
        RetrievalResult(chunk_id=1, score=-10.0),
        RetrievalResult(chunk_id=2, score=0.0),
    ]

    results = fusion.fuse(
        rrf_results=rrf_results,
        cross_encoder_results=cross_encoder_results,
        top_k=2,
    )

    assert results[0].chunk_id == 1
    assert results[1].chunk_id == 2


def test_weighted_fusion_sorts_results() -> None:
    fusion = WeightedFusion(
        rrf_weight=0.9,
        cross_encoder_weight=0.1,
    )

    rrf_results = [
        RetrievalResult(chunk_id=1, score=0.1),
        RetrievalResult(chunk_id=2, score=1.0),
        RetrievalResult(chunk_id=3, score=0.5),
    ]

    cross_encoder_results = [
        RetrievalResult(chunk_id=1, score=0.1),
        RetrievalResult(chunk_id=2, score=0.1),
        RetrievalResult(chunk_id=3, score=0.1),
    ]

    results = fusion.fuse(
        rrf_results=rrf_results,
        cross_encoder_results=cross_encoder_results,
        top_k=3,
    )

    assert [result.chunk_id for result in results] == [
        2,
        3,
        1,
    ]


def test_weighted_fusion_respects_top_k() -> None:
    fusion = WeightedFusion()

    rrf_results = [
        RetrievalResult(chunk_id=1, score=1.0),
        RetrievalResult(chunk_id=2, score=0.8),
        RetrievalResult(chunk_id=3, score=0.6),
    ]

    cross_encoder_results = [
        RetrievalResult(chunk_id=1, score=1.0),
        RetrievalResult(chunk_id=2, score=0.8),
        RetrievalResult(chunk_id=3, score=0.6),
    ]

    results = fusion.fuse(
        rrf_results=rrf_results,
        cross_encoder_results=cross_encoder_results,
        top_k=2,
    )

    assert len(results) == 2


def test_weighted_fusion_empty_input() -> None:
    fusion = WeightedFusion()

    assert fusion.fuse(
        rrf_results=[],
        cross_encoder_results=[],
        top_k=5,
    ) == []


def test_weighted_fusion_invalid_negative_weights() -> None:
    with pytest.raises(ValueError):
        WeightedFusion(
            rrf_weight=-0.1,
            cross_encoder_weight=1.1,
        )


def test_weighted_fusion_invalid_weight_range() -> None:
    with pytest.raises(ValueError):
        WeightedFusion(
            rrf_weight=1.2,
            cross_encoder_weight=-0.2,
        )


def test_weighted_fusion_weights_must_sum_to_one() -> None:
    with pytest.raises(ValueError):
        WeightedFusion(
            rrf_weight=0.8,
            cross_encoder_weight=0.1,
        )


def test_weighted_fusion_equal_scores_are_safe() -> None:
    fusion = WeightedFusion()

    results = fusion.fuse(
        rrf_results=[
            RetrievalResult(chunk_id=1, score=5.0),
            RetrievalResult(chunk_id=2, score=5.0),
        ],
        cross_encoder_results=[
            RetrievalResult(chunk_id=1, score=2.0),
            RetrievalResult(chunk_id=2, score=2.0),
        ],
        top_k=2,
    )

    assert len(results) == 2
    assert all(
        result.score == 1.0
        for result in results
    )