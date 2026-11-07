import pytest
from sqlalchemy import select

from app.models.graph_node import GraphNode
from app.services.knowledge_graph import knowledge_graph_builder
from app.services.retrieval.filters import RetrievalFilters
from app.services.retrieval.graph_seeder import GraphSeedRetriever
from app.services.retrieval.lexical.manager import BM25IndexManager
from app.services.retrieval.lexical.retriever import LexicalRetriever


def test_independent_seeder_prioritizes_exact_symbol_and_respects_roles(
    db,
    retrieval_dataset,
):
    repository_id = retrieval_dataset["repository_id"]
    knowledge_graph_builder.build(db, repository_id)
    seeder = GraphSeedRetriever(db, LexicalRetriever(db, BM25IndexManager()))

    seed_ids = seeder.retrieve(
        repository_id=repository_id,
        query="Where is authenticateUser defined?",
        top_k=2,
        candidate_pool_k=20,
        filters=RetrievalFilters(exclude_roles=["test", "fixture"]),
    )

    assert seed_ids[0] == retrieval_dataset["chunks"][2].id
    assert all(
        db.scalar(
            select(GraphNode.id).where(
                GraphNode.repository_id == repository_id,
                GraphNode.chunk_id == chunk_id,
            )
        )
        is not None
        for chunk_id in seed_ids
    )
    assert seeder.last_candidate_count > 0


def test_independent_seeder_limits_duplicate_files(
    db,
    retrieval_dataset,
):
    repository_id = retrieval_dataset["repository_id"]
    knowledge_graph_builder.build(db, repository_id)
    seeder = GraphSeedRetriever(db, LexicalRetriever(db, BM25IndexManager()))

    seed_ids = seeder.retrieve(
        repository_id=repository_id,
        query="authenticate user",
        top_k=4,
        candidate_pool_k=20,
        filters=RetrievalFilters(exclude_roles=["test", "fixture"]),
        max_per_file=1,
    )

    file_ids = [
        db.scalar(
            select(GraphNode.file_id).where(
                GraphNode.repository_id == repository_id,
                GraphNode.chunk_id == chunk_id,
            )
        )
        for chunk_id in seed_ids
    ]
    assert len(file_ids) == len(set(file_ids))
    assert len(seed_ids) <= 4


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"repository_id": 0}, "repository_id"),
        ({"candidate_pool_k": 1}, "candidate_pool_k"),
        ({"max_per_file": 0}, "max_per_file"),
    ],
)
def test_independent_seeder_validates_budgets(kwargs, message):
    from unittest.mock import Mock

    seeder = GraphSeedRetriever(Mock(), Mock())
    parameters = {
        "repository_id": 1,
        "query": "token validation",
        "top_k": 2,
    }
    parameters.update(kwargs)

    with pytest.raises(ValueError, match=message):
        seeder.retrieve(**parameters)
