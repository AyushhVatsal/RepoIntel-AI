from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.graph_edge import GraphEdge, GraphEdgeType
from app.models.graph_node import GraphNode, GraphNodeType

TraversalDirection = Literal["outgoing", "incoming", "both"]

# *seed chunk is the initial code chunk that has already been retrieved from (hybrid reranker) v2.2 and has already identified as relevant to the user's query
MAX_GRAPH_HOPS = 3
MAX_SEED_CHUNKS = 100
MAX_GRAPH_CANDIDATES = 200

@dataclass(frozen=True, slots=True)
class GraphRetrievalResult:
    """A chunk discovered through bounded graph expansion."""

    chunk_id: int
    file_id: int
    hop_count: int
    score: float
    query_score: float | None = None


class GraphRetriever:
    """Retrieve additional code chunks through repository graph relationships.

    Graph Retrieval V1:
    - Expands from seed chunks supplied by another retriever.
    - Includes sibling chunks from seed files.
    - Traverses IMPORTS relationships up to a bounded depth.
    - Enforces repository isolation in every database query.
    - Excludes seed chunks and deduplicates returned candidates.
    - Does not modify or rerank the original retrieval results.

    IMPORTS direction:
    - outgoing: follow files imported by the current file.
    - incoming: follow files that import the current file.
    - both: follow both directions.

    Scores are deterministic distance-based priors, not calibrated
    relevance probabilities.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def retrieve(
        self,
        *,
        repository_id: int,
        seed_chunk_ids: Sequence[int],
        max_hops: int = 1,
        top_k: int = 50,
        direction: TraversalDirection = "both",
    ) -> list[GraphRetrievalResult]:
        """Return graph-connected chunk candidates, excluding the seeds."""

        self._validate_parameters(
            repository_id=repository_id,
            max_hops=max_hops,
            top_k=top_k,
            direction=direction,
        )

        if top_k == 0:
            return []

        raw_seed_ids = list(seed_chunk_ids)

        if len(raw_seed_ids) > MAX_SEED_CHUNKS:
            raise ValueError(
                f"At most {MAX_SEED_CHUNKS} seed chunks are allowed"
            )

        if any(
            type(chunk_id) is not int or chunk_id <= 0
            for chunk_id in raw_seed_ids
        ):
            raise ValueError("Seed chunk IDs must be positive integers")

        # Keep the requested IDs for exclusion, even if some seeds are
        # missing from the current graph.
        seed_ids = set(raw_seed_ids)

        if not seed_ids:
            return []

        # 1. Resolve seed chunks strictly within the requested repository.
        seed_nodes = list(
            self._db.scalars(
                select(GraphNode).where(
                    GraphNode.repository_id == repository_id,
                    GraphNode.node_type == GraphNodeType.CHUNK.value,
                    GraphNode.chunk_id.in_(seed_ids),
                )
            ).all()
        )

        if not seed_nodes:
            return []

        seed_file_ids = {
            node.file_id
            for node in seed_nodes
            if node.file_id is not None
        }

        if not seed_file_ids:
            return []

        # 2. Load only file nodes containing seed chunks. Do not load the
        # entire repository graph into memory.
        seed_file_nodes = list(
            self._db.scalars(
                select(GraphNode).where(
                    GraphNode.repository_id == repository_id,
                    GraphNode.node_type == GraphNodeType.FILE.value,
                    GraphNode.file_id.in_(seed_file_ids),
                )
            ).all()
        )

        file_id_by_node_id: dict[int, int] = {
            node.id: node.file_id
            for node in seed_file_nodes
            if node.file_id is not None
        }

        if not file_id_by_node_id:
            return []

        # Multi-source BFS starts at every file represented by a seed chunk.
        distance_by_node_id: dict[int, int] = {
            node_id: 0 for node_id in file_id_by_node_id
        }
        frontier = set(distance_by_node_id)

        # 3. Traverse one frontier at a time. Each query is restricted to
        # the repository, IMPORTS edges, and the current frontier.
        for hop_count in range(1, max_hops + 1):
            if not frontier:
                break

            edge_conditions = []

            if direction in ("outgoing", "both"):
                edge_conditions.append(
                    GraphEdge.source_node_id.in_(frontier)
                )

            if direction in ("incoming", "both"):
                edge_conditions.append(
                    GraphEdge.target_node_id.in_(frontier)
                )

            edges = list(
                self._db.scalars(
                    select(GraphEdge).where(
                        GraphEdge.repository_id == repository_id,
                        GraphEdge.edge_type == GraphEdgeType.IMPORTS.value,
                        or_(*edge_conditions),
                    )
                ).all()
            )

            neighbor_ids: set[int] = set()

            for edge in edges:
                # Defense in depth: do not rely solely on SQL filtering.
                if edge.repository_id != repository_id:
                    continue

                if edge.edge_type != GraphEdgeType.IMPORTS.value:
                    continue

                if (
                    direction in ("outgoing", "both")
                    and edge.source_node_id in frontier
                ):
                    neighbor_ids.add(edge.target_node_id)

                if (
                    direction in ("incoming", "both")
                    and edge.target_node_id in frontier
                ):
                    neighbor_ids.add(edge.source_node_id)

            # A visited node already has a shortest distance.
            neighbor_ids.difference_update(distance_by_node_id)

            if not neighbor_ids:
                break

            # Only FILE nodes are valid traversal destinations. This guards
            # against malformed relationships pointing to other node types.
            neighbor_nodes = list(
                self._db.scalars(
                    select(GraphNode).where(
                        GraphNode.repository_id == repository_id,
                        GraphNode.node_type == GraphNodeType.FILE.value,
                        GraphNode.id.in_(neighbor_ids),
                    )
                ).all()
            )

            next_frontier: set[int] = set()

            for node in neighbor_nodes:
                if node.repository_id != repository_id:
                    continue

                if node.node_type != GraphNodeType.FILE.value:
                    continue

                if node.file_id is None:
                    continue

                file_id_by_node_id[node.id] = node.file_id
                distance_by_node_id[node.id] = hop_count
                next_frontier.add(node.id)

            frontier = next_frontier

        # 4. Group reachable source files by their shortest graph distance.
        file_ids_by_distance: dict[int, set[int]] = defaultdict(set)

        for node_id, distance in distance_by_node_id.items():
            file_id = file_id_by_node_id.get(node_id)

            if file_id is not None:
                file_ids_by_distance[distance].add(file_id)

        # 5. Fetch candidates in distance order. SQL limits each query to
        # the remaining result budget, avoiding unbounded chunk materialization.
        results_by_chunk_id: dict[int, GraphRetrievalResult] = {}

        for distance in sorted(file_ids_by_distance):
            remaining = top_k - len(results_by_chunk_id)

            if remaining <= 0:
                break

            file_ids = file_ids_by_distance[distance]

            if not file_ids:
                continue

            candidate_query = (
                select(GraphNode)
                .where(
                    GraphNode.repository_id == repository_id,
                    GraphNode.node_type == GraphNodeType.CHUNK.value,
                    GraphNode.file_id.in_(file_ids),
                    GraphNode.chunk_id.is_not(None),
                    GraphNode.chunk_id.not_in(seed_ids),
                )
                .order_by(GraphNode.file_id, GraphNode.chunk_id)
                .limit(remaining)
            )

            candidate_nodes = list(
                self._db.scalars(candidate_query).all()
            )

            for node in candidate_nodes:
                if node.repository_id != repository_id:
                    continue

                if node.node_type != GraphNodeType.CHUNK.value:
                    continue

                if node.chunk_id is None or node.file_id is None:
                    continue

                if node.chunk_id in seed_ids:
                    continue

                # Shortest distance is the primary graph relevance signal.
                result = GraphRetrievalResult(
                    chunk_id=node.chunk_id,
                    file_id=node.file_id,
                    hop_count=distance,
                    score=1.0 / (distance + 1),
                )

                previous = results_by_chunk_id.get(node.chunk_id)

                if (
                    previous is None
                    or result.hop_count < previous.hop_count
                ):
                    results_by_chunk_id[node.chunk_id] = result

        return sorted(
            results_by_chunk_id.values(),
            key=lambda result: (
                result.hop_count,
                result.file_id,
                result.chunk_id,
            ),
        )[:top_k]

    @staticmethod
    def _validate_parameters(
        *,
        repository_id: int,
        max_hops: int,
        top_k: int,
        direction: str,
    ) -> None:
        """Reject invalid or unbounded retrieval parameters."""

        if type(repository_id) is not int or repository_id <= 0:
            raise ValueError("repository_id must be a positive integer")

        if type(max_hops) is not int:
            raise ValueError("max_hops must be an integer")

        if not 0 <= max_hops <= MAX_GRAPH_HOPS:
            raise ValueError(
                f"max_hops must be between 0 and {MAX_GRAPH_HOPS}"
            )

        if type(top_k) is not int:
            raise ValueError("top_k must be an integer")

        if top_k < 0:
            raise ValueError("top_k must be non-negative")

        if top_k > MAX_GRAPH_CANDIDATES:
            raise ValueError(
                f"top_k cannot exceed {MAX_GRAPH_CANDIDATES}"
            )

        if direction not in ("outgoing", "incoming", "both"):
            raise ValueError(
                "direction must be 'outgoing', 'incoming', or 'both'"
            )
