from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services.retrieval.graph_retriever import GraphRetriever


def _rows(items):
    result = Mock()
    result.all.return_value = items
    return result


def _node(
    *,
    node_id: int,
    repository_id: int = 7,
    node_type: str,
    file_id: int | None = None,
    chunk_id: int | None = None,
):
    return SimpleNamespace(
        id=node_id,
        repository_id=repository_id,
        node_type=node_type,
        file_id=file_id,
        chunk_id=chunk_id,
    )


def _edge(
    source: int,
    target: int,
    *,
    repository_id: int = 7,
    edge_type: str = "IMPORTS",
):
    return SimpleNamespace(
        repository_id=repository_id,
        edge_type=edge_type,
        source_node_id=source,
        target_node_id=target,
    )


def _session_with_rows(*responses):
    db = Mock()
    db.scalars.side_effect = [_rows(items) for items in responses]
    return db


def test_returns_sibling_and_direct_import_chunks_excluding_seed():
    seed = _node(
        node_id=101,
        node_type="CHUNK",
        file_id=10,
        chunk_id=1,
    )

    seed_file = _node(
        node_id=201,
        node_type="FILE",
        file_id=10,
    )

    dependency_file = _node(
        node_id=202,
        node_type="FILE",
        file_id=20,
    )

    dependent_file = _node(
        node_id=203,
        node_type="FILE",
        file_id=30,
    )

    # File 20 imports file 10; file 10 imports file 30.
    edges = [
        _edge(202, 201),
        _edge(201, 203),
    ]

    sibling_chunk = _node(
        node_id=102,
        node_type="CHUNK",
        file_id=10,
        chunk_id=2,
    )

    dependency_chunk = _node(
        node_id=103,
        node_type="CHUNK",
        file_id=20,
        chunk_id=3,
    )

    dependent_chunk = _node(
        node_id=104,
        node_type="CHUNK",
        file_id=30,
        chunk_id=4,
    )

    db = _session_with_rows(
        [seed],                              # Seed chunks
        [seed_file],                        # Seed file nodes
        edges,                              # First-hop IMPORTS edges
        [dependency_file, dependent_file],  # Neighbor file nodes
        [sibling_chunk],                    # Distance 0 candidates
        [dependency_chunk, dependent_chunk],# Distance 1 candidates
    )

    results = GraphRetriever(db).retrieve(
        repository_id=7,
        seed_chunk_ids=[1],
        max_hops=1,
        top_k=10,
        direction="both",
    )

    assert [result.chunk_id for result in results] == [2, 3, 4]

    by_chunk = {result.chunk_id: result for result in results}

    assert by_chunk[2].hop_count == 0
    assert by_chunk[2].score == 1.0

    assert by_chunk[3].hop_count == 1
    assert by_chunk[3].score == 0.5

    assert by_chunk[4].hop_count == 1
    assert by_chunk[4].score == 0.5


def test_zero_hops_returns_only_sibling_chunks():
    seed = _node(
        node_id=101,
        node_type="CHUNK",
        file_id=10,
        chunk_id=1,
    )

    seed_file = _node(
        node_id=201,
        node_type="FILE",
        file_id=10,
    )

    sibling = _node(
        node_id=102,
        node_type="CHUNK",
        file_id=10,
        chunk_id=2,
    )

    db = _session_with_rows([seed], [seed_file], [sibling])

    results = GraphRetriever(db).retrieve(
        repository_id=7,
        seed_chunk_ids=[1],
        max_hops=0,
        top_k=10,
    )

    assert [result.chunk_id for result in results] == [2]
    assert results[0].hop_count == 0


def test_outgoing_does_not_follow_an_incoming_import_edge():
    seed = _node(
        node_id=101,
        node_type="CHUNK",
        file_id=10,
        chunk_id=1,
    )

    seed_file = _node(
        node_id=201,
        node_type="FILE",
        file_id=10,
    )

    sibling = _node(
        node_id=102,
        node_type="CHUNK",
        file_id=10,
        chunk_id=2,
    )

    # File 20 imports file 10. This is incoming relative to the seed.
    incoming_edge = _edge(202, 201)

    db = _session_with_rows(
        [seed],
        [seed_file],
        [incoming_edge],
        [sibling],
    )

    results = GraphRetriever(db).retrieve(
        repository_id=7,
        seed_chunk_ids=[1],
        max_hops=1,
        direction="outgoing",
    )

    assert [result.chunk_id for result in results] == [2]


def test_seed_chunks_are_deduplicated():
    seed = _node(
        node_id=101,
        node_type="CHUNK",
        file_id=10,
        chunk_id=1,
    )

    seed_file = _node(
        node_id=201,
        node_type="FILE",
        file_id=10,
    )

    sibling = _node(
        node_id=102,
        node_type="CHUNK",
        file_id=10,
        chunk_id=2,
    )

    db = _session_with_rows([seed], [seed_file], [sibling])

    results = GraphRetriever(db).retrieve(
        repository_id=7,
        seed_chunk_ids=[1, 1, 1],
        max_hops=0,
        top_k=10,
    )

    assert [result.chunk_id for result in results] == [2]


def test_missing_seed_graph_node_returns_empty_results():
    db = _session_with_rows([])

    results = GraphRetriever(db).retrieve(
        repository_id=7,
        seed_chunk_ids=[999],
    )

    assert results == []


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"repository_id": 0}, "repository_id"),
        ({"max_hops": -1}, "max_hops"),
        ({"max_hops": 4}, "max_hops"),
        ({"top_k": 201}, "top_k"),
        ({"direction": "unknown"}, "direction"),
    ],
)
def test_rejects_invalid_parameters(kwargs, message):
    parameters = {
        "repository_id": 7,
        "seed_chunk_ids": [1],
        "max_hops": 1,
        "top_k": 10,
        "direction": "both",
    }
    parameters.update(kwargs)

    with pytest.raises(ValueError, match=message):
        GraphRetriever(Mock()).retrieve(**parameters)


def test_rejects_invalid_seed_chunk_ids():
    with pytest.raises(ValueError, match="positive integers"):
        GraphRetriever(Mock()).retrieve(
            repository_id=7,
            seed_chunk_ids=[1, -2],
        )