from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy import select

from app.models.chunk import Chunk, ChunkType
from app.models.embedding import Embedding
from app.models.graph_edge import GraphEdge, GraphEdgeType
from app.models.graph_node import GraphNode, GraphNodeType
from app.models.repository_file import FileRole, RepositoryFile
from app.services.knowledge_graph import knowledge_graph_builder
from app.services.retrieval.filters import RetrievalFilters
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
        [10],                                # Distance 0 eligible files
        [sibling_chunk],                    # Distance 0 candidates
        [20, 30],                            # Distance 1 eligible files
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

    db = _session_with_rows([seed], [seed_file], [10], [sibling])

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
        [10],
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

    db = _session_with_rows([seed], [seed_file], [10], [sibling])

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
        ({"max_per_file": 0}, "max_per_file"),
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


def test_candidates_are_filtered_before_diverse_candidate_budget(
    db,
    retrieval_dataset,
):
    repository_id = retrieval_dataset["repository_id"]
    seed_chunk = retrieval_dataset["chunks"][0]
    auth_file = db.get(RepositoryFile, seed_chunk.file_id)
    sibling_chunks = [
        Chunk(
            repository_id=repository_id,
            file_id=auth_file.id,
            chunk_index=index,
            chunk_type=ChunkType.FUNCTION,
            content=f"def auth_helper_{index}(): pass",
            start_line=index + 1,
            end_line=index + 1,
            token_count=8,
            symbol_name=f"auth_helper_{index}",
            qualified_name=f"auth.auth_helper_{index}",
            parent_symbol=None,
            metadata_={},
        )
        for index in (1, 2)
    ]
    db.add_all(sibling_chunks)
    db.commit()
    knowledge_graph_builder.build(db, repository_id)

    file_nodes = {
        node.file_id: node
        for node in db.scalars(
            select(GraphNode).where(
                GraphNode.repository_id == repository_id,
                GraphNode.node_type == GraphNodeType.FILE.value,
            )
        ).all()
    }
    files = {
        file.relative_path: file
        for file in db.scalars(
            select(RepositoryFile).where(
                RepositoryFile.repository_id == repository_id
            )
        ).all()
    }
    auth_node = file_nodes[auth_file.id]
    target_files = [
        files["backend/models/user.py"],
        files["frontend/server.ts"],
        files["tests/test_auth.py"],
        files["fixtures/auth_fixture.py"],
    ]
    db.add_all(
        [
            GraphEdge(
                repository_id=repository_id,
                source_node_id=auth_node.id,
                target_node_id=file_nodes[file.id].id,
                edge_type=GraphEdgeType.IMPORTS.value,
                metadata_={},
            )
            for file in target_files
        ]
    )
    db.commit()

    filters = RetrievalFilters(
        language="typescript",
        file_path="frontend/",
        chunk_type="function",
        symbol_name="authenticateUser",
        role=FileRole.SOURCE,
        exclude_roles=[FileRole.TEST, FileRole.FIXTURE],
    )
    retriever = GraphRetriever(db)
    results = retriever.retrieve(
        repository_id=repository_id,
        seed_chunk_ids=[seed_chunk.id],
        max_hops=1,
        top_k=1,
        filters=filters,
        max_per_file=1,
    )

    assert len(results) == 1
    returned_chunk = db.get(Chunk, results[0].chunk_id)
    returned_file = db.get(RepositoryFile, returned_chunk.file_id)
    assert returned_file.relative_path == "frontend/server.ts"
    assert returned_file.role == FileRole.SOURCE


def test_query_similarity_selects_relevant_later_chunk_within_file(
    db,
    retrieval_dataset,
):
    repository_id = retrieval_dataset["repository_id"]
    seed_chunk = retrieval_dataset["chunks"][0]
    later_chunks = [
        Chunk(
            repository_id=repository_id,
            file_id=seed_chunk.file_id,
            chunk_index=index,
            chunk_type=ChunkType.FUNCTION,
            content=f"def query_ranked_helper_{index}(): pass",
            start_line=index + 1,
            end_line=index + 1,
            token_count=8,
            symbol_name=f"query_ranked_helper_{index}",
            qualified_name=f"auth.query_ranked_helper_{index}",
            parent_symbol=None,
            metadata_={},
        )
        for index in (1, 2)
    ]
    db.add_all(later_chunks)
    db.flush()
    db.add_all(
        [
            Embedding(
                chunk_id=later_chunks[0].id,
                model="filter-test-model",
                dimensions=384,
                embedding=[-0.1] * 384,
            ),
            Embedding(
                chunk_id=later_chunks[1].id,
                model="filter-test-model",
                dimensions=384,
                embedding=[0.1] * 384,
            ),
        ]
    )
    db.commit()
    knowledge_graph_builder.build(db, repository_id)

    results = GraphRetriever(db).retrieve(
        repository_id=repository_id,
        seed_chunk_ids=[seed_chunk.id],
        max_hops=0,
        top_k=1,
        max_per_file=1,
        query_vector=[0.1] * 384,
        embedding_model="filter-test-model",
    )

    assert len(results) == 1
    assert results[0].chunk_id == later_chunks[1].id
    assert results[0].query_score == pytest.approx(1.0)

    independent_results = GraphRetriever(db).retrieve(
        repository_id=repository_id,
        seed_chunk_ids=[seed_chunk.id],
        max_hops=0,
        top_k=3,
        max_per_file=3,
        query_vector=[0.1] * 384,
        embedding_model="filter-test-model",
        include_seed_chunk_ids=[seed_chunk.id],
    )
    assert seed_chunk.id in {
        result.chunk_id for result in independent_results
    }


def test_multi_hop_traversal_returns_shortest_paths_and_stops_cycle():
    seed = _node(
        node_id=101,
        node_type="CHUNK",
        file_id=10,
        chunk_id=1,
    )
    file_1 = _node(node_id=201, node_type="FILE", file_id=10)
    file_2 = _node(node_id=202, node_type="FILE", file_id=20)
    file_3 = _node(node_id=203, node_type="FILE", file_id=30)
    chunk_2 = _node(
        node_id=102,
        node_type="CHUNK",
        file_id=20,
        chunk_id=2,
    )
    chunk_3 = _node(
        node_id=103,
        node_type="CHUNK",
        file_id=30,
        chunk_id=3,
    )
    db = _session_with_rows(
        [seed],
        [file_1],
        [_edge(201, 202)],
        [file_2],
        [_edge(202, 203)],
        [file_3],
        [_edge(203, 201)],  # Cycle to the already visited seed file.
        [10],
        [],
        [20],
        [chunk_2],
        [30],
        [chunk_3],
    )

    results = GraphRetriever(db).retrieve(
        repository_id=7,
        seed_chunk_ids=[1],
        max_hops=3,
        top_k=10,
        direction="outgoing",
    )

    assert [result.chunk_id for result in results] == [2, 3]
    assert [result.hop_count for result in results] == [1, 2]
    assert results[0].graph_path == ("10", "20")
    assert results[1].graph_path == ("10", "20", "30")
    assert results[1].relationship_types == (
        GraphEdgeType.IMPORTS.value,
        GraphEdgeType.IMPORTS.value,
        GraphEdgeType.HAS_CHUNK.value,
    )


def test_equal_length_paths_preserve_highest_ranked_seed_provenance():
    low_rank_seed = _node(
        node_id=101, node_type="CHUNK", file_id=10, chunk_id=1
    )
    high_rank_seed = _node(
        node_id=102, node_type="CHUNK", file_id=20, chunk_id=2
    )
    file_10 = _node(node_id=201, node_type="FILE", file_id=10)
    file_20 = _node(node_id=202, node_type="FILE", file_id=20)
    target_file = _node(node_id=203, node_type="FILE", file_id=30)
    target_chunk = _node(
        node_id=103, node_type="CHUNK", file_id=30, chunk_id=3
    )
    db = _session_with_rows(
        [low_rank_seed, high_rank_seed],
        [file_10, file_20],
        [_edge(201, 203), _edge(202, 203)],
        [target_file],
        [10, 20],
        [],
        [30],
        [target_chunk],
    )

    results = GraphRetriever(db).retrieve(
        repository_id=7,
        seed_chunk_ids=[2, 1],
        max_hops=1,
        top_k=2,
        direction="outgoing",
    )

    assert len(results) == 1
    assert results[0].graph_path == ("20", "30")


def test_candidate_budget_is_diverse_deterministic_and_repository_scoped(
    db,
    retrieval_dataset,
):
    repository_id = retrieval_dataset["repository_id"]
    other_repository_id = retrieval_dataset["other_repository_id"]
    seed_chunk = retrieval_dataset["chunks"][0]
    knowledge_graph_builder.build(db, repository_id)
    knowledge_graph_builder.build(db, other_repository_id)

    file_nodes = {
        node.file_id: node
        for node in db.scalars(
            select(GraphNode).where(
                GraphNode.repository_id == repository_id,
                GraphNode.node_type == GraphNodeType.FILE.value,
            )
        ).all()
    }
    seed_file_node = file_nodes[seed_chunk.file_id]
    target_chunks = retrieval_dataset["chunks"][1:3]
    target_file_ids = {chunk.file_id for chunk in target_chunks}
    db.add_all(
        [
            GraphEdge(
                repository_id=repository_id,
                source_node_id=seed_file_node.id,
                target_node_id=file_nodes[file_id].id,
                edge_type=GraphEdgeType.IMPORTS.value,
                metadata_={},
            )
            for file_id in target_file_ids
        ]
    )
    db.commit()

    retriever = GraphRetriever(db)
    kwargs = {
        "repository_id": repository_id,
        "seed_chunk_ids": [seed_chunk.id],
        "max_hops": 1,
        "top_k": 2,
        "max_per_file": 1,
        "filters": RetrievalFilters(
            exclude_roles=[FileRole.TEST, FileRole.FIXTURE]
        ),
    }
    first = retriever.retrieve(**kwargs)
    second = retriever.retrieve(**kwargs)

    assert len(first) <= 2
    assert len({result.chunk_id for result in first}) == len(first)
    assert len({result.file_id for result in first}) == len(first)
    assert [result.chunk_id for result in first] == [
        result.chunk_id for result in second
    ]
    assert all(
        result.hop_count <= 1
        and GraphEdgeType.HAS_CHUNK.value in result.relationship_types
        for result in first
    )
    assert all(
        result.graph_path
        and result.graph_path[-1]
        for result in first
    )

    assert retriever.retrieve(
        repository_id=repository_id,
        seed_chunk_ids=[retrieval_dataset["other_chunk"].id],
        max_hops=1,
        top_k=2,
    ) == []


def test_database_multi_hop_traversal_stops_cycles_and_reports_paths(
    db,
    retrieval_dataset,
):
    repository_id = retrieval_dataset["repository_id"]
    seed_chunk = retrieval_dataset["chunks"][0]
    knowledge_graph_builder.build(db, repository_id)
    file_nodes = {
        node.file_id: node
        for node in db.scalars(
            select(GraphNode).where(
                GraphNode.repository_id == repository_id,
                GraphNode.node_type == GraphNodeType.FILE.value,
            )
        ).all()
    }
    target_files = retrieval_dataset["chunks"][1:3]
    file_ids = [seed_chunk.file_id, *(chunk.file_id for chunk in target_files)]
    db.add_all(
        [
            GraphEdge(
                repository_id=repository_id,
                source_node_id=file_nodes[source_file_id].id,
                target_node_id=file_nodes[target_file_id].id,
                edge_type=GraphEdgeType.IMPORTS.value,
                metadata_={},
            )
            for source_file_id, target_file_id in zip(
                file_ids,
                file_ids[1:] + file_ids[:1],
                strict=True,
            )
        ]
    )
    db.commit()

    results = GraphRetriever(db).retrieve(
        repository_id=repository_id,
        seed_chunk_ids=[seed_chunk.id],
        max_hops=3,
        top_k=10,
        direction="outgoing",
        filters=RetrievalFilters(
            exclude_roles=[FileRole.TEST, FileRole.FIXTURE]
        ),
    )

    assert [result.chunk_id for result in results] == [
        target_files[0].id,
        target_files[1].id,
    ]
    assert [result.hop_count for result in results] == [1, 2]
    assert results[0].graph_path[-1] == "backend/models/user.py"
    assert results[1].graph_path[-1] == "frontend/server.ts"
    assert len(results[0].relationship_types) == 2
    assert len(results[1].relationship_types) == 3
