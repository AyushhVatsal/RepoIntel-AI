from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps.db import get_db
from app.api.routes import retrieval as retrieval_route
from app.schemas.retrieval import RetrievalResponse, RetrievedChunk


def test_graph_search_is_opt_in_and_exposes_strategy_parameters(
    monkeypatch,
) -> None:
    captured = {}

    class FakeGraphService:
        def __init__(self, _db, **kwargs):
            captured.update(kwargs)

        def retrieve(self, request):
            return RetrievalResponse(
                repository_id=request.repository_id,
                query=request.query,
                latency_ms=12.0,
                ranking_policy="graph_only_independent_seed_v1",
                latency_breakdown_ms={"service_total_ms": 12.0},
                results=[
                    RetrievedChunk(
                        chunk_id=10,
                        content="chunk",
                        file_path="src/module.py",
                        graph_hop_count=1,
                        graph_path=["src/main.py", "src/module.py"],
                        relationship_types=["IMPORTS", "HAS_CHUNK"],
                    )
                ],
            )

    monkeypatch.setattr(
        retrieval_route,
        "GraphEnhancedRetrievalService",
        FakeGraphService,
    )
    app = FastAPI()
    app.include_router(retrieval_route.router)
    app.dependency_overrides[get_db] = lambda: object()

    with TestClient(app) as client:
        response = client.post(
            "/retrieval/graph-search?seed_strategy=independent&graph_only=true"
            "&seed_budget=7&max_hops=2&graph_candidate_multiplier=4"
            "&max_graph_candidates=80",
            json={
                "repository_id": 49,
                "query": "Where is authentication handled?",
                "top_k": 5,
            },
        )

    assert response.status_code == 200
    assert captured == {
        "seed_strategy": "independent",
        "seed_budget": 7,
        "max_hops": 2,
        "graph_candidate_multiplier": 4,
        "max_graph_candidates": 80,
        "graph_only": True,
    }
    payload = response.json()
    assert payload["ranking_policy"] == "graph_only_independent_seed_v1"
    assert payload["results"][0]["graph_path"] == [
        "src/main.py",
        "src/module.py",
    ]
    assert any(
        route.path == "/retrieval/search"
        for route in retrieval_route.router.routes
    )
