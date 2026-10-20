
import pytest

from app.services.retrieval.fusion.graph_fusion import GraphFusion
from app.services.retrieval.graph_retriever import GraphRetrievalResult
from app.services.retrieval.result import RetrievalResult


def baseline(chunk_id: int, score: float) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        score=score,
        dense_score=score,
        retrieval_score=score,
    )


def graph(
    chunk_id: int,
    hop_count: int,
    file_id: int = 1,
) -> GraphRetrievalResult:
    return GraphRetrievalResult(
        chunk_id=chunk_id,
        file_id=file_id,
        hop_count=hop_count,
        score=1.0 / (hop_count + 1) if hop_count >= 0 else 0.0,
    )


def test_non_positive_top_k_returns_empty():
    fusion = GraphFusion()

    assert fusion.fuse(
        baseline_results=[baseline(1, 0.9)],
        graph_results=[],
        top_k=0,
    ) == []


def test_negative_baseline_reserve_is_rejected():
    fusion = GraphFusion()

    with pytest.raises(ValueError, match="baseline_reserve"):
        fusion.fuse(
            baseline_results=[],
            graph_results=[],
            top_k=5,
            baseline_reserve=-1,
        )


def test_negative_graph_hop_is_rejected():
    fusion = GraphFusion()

    with pytest.raises(ValueError, match="hop_count"):
        fusion.fuse(
            baseline_results=[],
            graph_results=[graph(10, -1)],
            top_k=5,
        )


def test_default_policy_keeps_fused_top_k_behavior():
    fusion = GraphFusion()

    results = fusion.fuse(
        baseline_results=[baseline(1, 1.0), baseline(2, 0.8)],
        graph_results=[graph(3, 0), graph(4, 0)],
        top_k=3,
    )

    assert [result.chunk_id for result in results] == [1, 3, 4]


@pytest.mark.parametrize("reserve", [1, 2, 3])
def test_reservation_preserves_leading_baseline_candidates(reserve):
    fusion = GraphFusion()
    baseline_results = [
        baseline(1, 1.0),
        baseline(2, 0.8),
        baseline(6, 0.6),
    ]

    results = fusion.fuse(
        baseline_results=baseline_results,
        graph_results=[graph(3, 0), graph(4, 0), graph(5, 0)],
        top_k=3,
        baseline_reserve=reserve,
    )

    returned_ids = [result.chunk_id for result in results]

    assert len(returned_ids) == 3
    assert len(set(returned_ids)) == 3
    assert set([1, 2, 6][:reserve]).issubset(returned_ids)


def test_reservation_is_capped_by_top_k_and_baseline_count():
    fusion = GraphFusion()

    results = fusion.fuse(
        baseline_results=[baseline(1, 1.0)],
        graph_results=[graph(2, 0), graph(3, 0)],
        top_k=2,
        baseline_reserve=10,
    )

    assert len(results) == 2
    assert 1 in {result.chunk_id for result in results}


def test_duplicate_graph_candidates_use_shortest_hop():
    fusion = GraphFusion()

    results = fusion.fuse(
        baseline_results=[baseline(1, 1.0)],
        graph_results=[graph(2, 2), graph(2, 0)],
        top_k=2,
    )

    by_id = {result.chunk_id: result for result in results}
    assert by_id[2].score == 0.25


def test_equal_scores_have_deterministic_tie_breaking():
    fusion = GraphFusion(baseline_weight=0.0, graph_weight=1.0)

    results = fusion.fuse(
        baseline_results=[],
        graph_results=[graph(9, 0), graph(3, 0), graph(7, 0)],
        top_k=3,
    )

    assert [result.chunk_id for result in results] == [3, 7, 9]