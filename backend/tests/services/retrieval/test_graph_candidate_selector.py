
import pytest

from app.services.retrieval.graph_candidate_selector import (
    select_graph_candidates,
)
from app.services.retrieval.graph_retriever import GraphRetrievalResult


def candidate(
    chunk_id: int,
    file_id: int,
    hop_count: int = 0,
    score: float = 1.0,
) -> GraphRetrievalResult:
    return GraphRetrievalResult(
        chunk_id=chunk_id,
        file_id=file_id,
        hop_count=hop_count,
        score=score,
    )


def test_limits_candidates_per_file_and_preserves_diversity() -> None:
    candidates = [
        candidate(1, 10),
        candidate(2, 10),
        candidate(3, 10),
        candidate(4, 20),
        candidate(5, 20),
        candidate(6, 30),
    ]

    selected = select_graph_candidates(
        candidates,
        top_k=5,
        max_per_file=2,
    )

    assert [item.chunk_id for item in selected] == [1, 4, 6, 2, 5]
    assert len({item.file_id for item in selected}) == 3
    assert all(
        sum(item.file_id == file_id for item in selected) <= 2
        for file_id in {item.file_id for item in selected}
    )


def test_prefers_shorter_hops() -> None:
    candidates = [
        candidate(1, 10, hop_count=1, score=0.5),
        candidate(2, 20, hop_count=0, score=1.0),
        candidate(3, 30, hop_count=2, score=1 / 3),
    ]

    selected = select_graph_candidates(candidates, top_k=3)

    assert [item.chunk_id for item in selected] == [2, 1, 3]


def test_deduplicates_chunk_ids_using_shortest_distance() -> None:
    candidates = [
        candidate(1, 10, hop_count=2, score=1 / 3),
        candidate(1, 10, hop_count=0, score=1.0),
        candidate(2, 20, hop_count=1, score=0.5),
    ]

    selected = select_graph_candidates(candidates, top_k=5)

    assert len(selected) == 2
    assert selected[0].chunk_id == 1
    assert selected[0].hop_count == 0


def test_respects_top_k() -> None:
    candidates = [
        candidate(1, 10),
        candidate(2, 20),
        candidate(3, 30),
    ]

    selected = select_graph_candidates(candidates, top_k=2)

    assert len(selected) == 2


@pytest.mark.parametrize(
    ("top_k", "max_per_file"),
    [
        (-1, 2),
        (5, 0),
        (5, -1),
    ],
)
def test_rejects_invalid_limits(
    top_k: int,
    max_per_file: int,
) -> None:
    with pytest.raises(ValueError):
        select_graph_candidates(
            [candidate(1, 10)],
            top_k=top_k,
            max_per_file=max_per_file,
        )