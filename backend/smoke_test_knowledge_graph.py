
from __future__ import annotations

import sys

# pyrefly: ignore[missing-import]
from sqlalchemy import func, select

from app.db.database import SessionLocal
from app.models.graph_edge import GraphEdge
from app.models.graph_node import GraphNode
from app.models.repository import Repository
from app.services.knowledge_graph import knowledge_graph_builder


def main() -> int:
    repository_id = int(sys.argv[1]) if len(sys.argv) > 1 else 49

    db = SessionLocal()

    try:
        repository = db.get(Repository, repository_id)

        if repository is None:
            print(f"ERROR: Repository {repository_id} was not found.")
            print("Check the repository ID and try again.")
            return 1

        print("=" * 60)
        print("KNOWLEDGE GRAPH V1 - REAL REPOSITORY SMOKE TEST")
        print("=" * 60)
        print(f"Repository ID: {repository.id}")
        print(f"Repository name: {repository.name}")
        print(f"Repository status: {repository.status}")
        print("\nBuilding graph...")

        result = knowledge_graph_builder.build(db, repository_id)

        print("\nBuild result:")
        for key, value in result.items():
            print(f"  {key}: {value}")

        node_counts = db.execute(
            select(
                GraphNode.node_type,
                func.count(GraphNode.id),
            )
            .where(GraphNode.repository_id == repository_id)
            .group_by(GraphNode.node_type)
            .order_by(GraphNode.node_type)
        ).all()

        edge_counts = db.execute(
            select(
                GraphEdge.edge_type,
                func.count(GraphEdge.id),
            )
            .where(GraphEdge.repository_id == repository_id)
            .group_by(GraphEdge.edge_type)
            .order_by(GraphEdge.edge_type)
        ).all()

        print("\nNodes by type:")
        if node_counts:
            for node_type, count in node_counts:
                print(f"  {node_type}: {count}")
        else:
            print("  No nodes found.")

        print("\nEdges by type:")
        if edge_counts:
            for edge_type, count in edge_counts:
                print(f"  {edge_type}: {count}")
        else:
            print("  No edges found.")

        actual_nodes = sum(count for _, count in node_counts)
        actual_edges = sum(count for _, count in edge_counts)

        print("\nConsistency checks:")
        print(
            f"  Returned node count matches DB: "
            f"{actual_nodes == result['nodes']}"
        )
        print(
            f"  Returned edge count matches DB: "
            f"{actual_edges == result['edges']}"
        )
        print(f"  At least one node exists: {actual_nodes > 0}")
        print(f"  At least one edge exists: {actual_edges > 0}")

        if (
            actual_nodes != result["nodes"]
            or actual_edges != result["edges"]
            or actual_nodes == 0
            or actual_edges == 0
        ):
            print("\nRESULT: FAILED")
            return 1

        print("\nRESULT: SMOKE TEST PASSED")
        return 0

    except Exception as exc:
        db.rollback()
        print(f"\nRESULT: ERROR - {type(exc).__name__}: {exc}")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
