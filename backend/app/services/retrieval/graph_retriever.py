from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from time import perf_counter
from typing import Literal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.embedding import Embedding
from app.models.graph_edge import GraphEdge, GraphEdgeType
from app.models.graph_node import GraphNode, GraphNodeType
from app.models.repository_file import RepositoryFile
from app.services.retrieval.filters import RetrievalFilters

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
    graph_path: tuple[str, ...] = ()
    relationship_types: tuple[str, ...] = ()


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
        self.last_latency_breakdown_ms: dict[str, float] = {}

    def retrieve(
        self,
        *,
        repository_id: int,
        seed_chunk_ids: Sequence[int],
        max_hops: int = 1,
        top_k: int = 50,
        direction: TraversalDirection = "both",
        filters: RetrievalFilters | None = None,
        max_per_file: int = 2,
        query_vector: Sequence[float] | None = None,
        embedding_model: str | None = None,
        include_seed_chunk_ids: Sequence[int] = (),
        imported_symbol: str | None = None,
    ) -> list[GraphRetrievalResult]:
        
        """Return graph-connected chunk candidates, excluding the seeds."""
        if imported_symbol is not None:
            imported_symbol = imported_symbol.strip()
            if not imported_symbol:
                raise ValueError("imported_symbol must not be empty")

        self._validate_parameters(
            repository_id=repository_id,
            max_hops=max_hops,
            top_k=top_k,
            direction=direction,
            max_per_file=max_per_file,
        )

        if top_k == 0:
            return []

        if (query_vector is None) != (embedding_model is None):
            raise ValueError(
                "query_vector and embedding_model must be provided together"
            )

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
        included_seed_ids = set(include_seed_chunk_ids)
        if not included_seed_ids.issubset(seed_ids):
            raise ValueError("included seed chunks must be part of seed_chunk_ids")

        if not seed_ids:
            return []

        # 1. Resolve seed chunks strictly within the requested repository.
        stage_started = perf_counter()
        seed_nodes = list(
            self._db.scalars(
                select(GraphNode).where(
                    GraphNode.repository_id == repository_id,
                    GraphNode.node_type == GraphNodeType.CHUNK.value,
                    GraphNode.chunk_id.in_(seed_ids),
                )
            ).all()
        )
        self.last_latency_breakdown_ms["graph_seed_lookup_ms"] = (
            perf_counter() - stage_started
        ) * 1000

        if not seed_nodes:
            return []

        seed_file_ids = {
            node.file_id
            for node in seed_nodes
            if node.file_id is not None
        }

        if not seed_file_ids:
            return []

        # The service supplies seeds in retrieval-rank order. Keep that
        # priority when several equally-short paths reach the same file.
        seed_rank_by_file_id: dict[int, int] = {}
        for seed_node in seed_nodes:
            if seed_node.file_id is None or seed_node.chunk_id is None:
                continue
            rank = raw_seed_ids.index(seed_node.chunk_id)
            seed_rank_by_file_id[seed_node.file_id] = min(
                rank,
                seed_rank_by_file_id.get(seed_node.file_id, rank),
            )

        # 2. Load only file nodes containing seed chunks. Do not load the
        # entire repository graph into memory.
        stage_started = perf_counter()
        seed_file_nodes = list(
            self._db.scalars(
                select(GraphNode).where(
                    GraphNode.repository_id == repository_id,
                    GraphNode.node_type == GraphNodeType.FILE.value,
                    GraphNode.file_id.in_(seed_file_ids),
                )
            ).all()
        )
        self.last_latency_breakdown_ms["graph_seed_file_lookup_ms"] = (
            perf_counter() - stage_started
        ) * 1000

        file_id_by_node_id: dict[int, int] = {
            node.id: node.file_id
            for node in seed_file_nodes
            if node.file_id is not None
        }

        if not file_id_by_node_id:
            return []

        file_node_id_by_file_id = {
            file_id: node_id
            for node_id, file_id in file_id_by_node_id.items()
        }
        path_by_node_id: dict[int, tuple[str, ...]] = {
            node.id: (getattr(node, "qualified_name", None) or str(node.file_id),)
            for node in seed_file_nodes
            if node.file_id is not None
        }
        relationships_by_node_id: dict[int, tuple[str, ...]] = {
            node.id: ()
            for node in seed_file_nodes
            if node.file_id is not None
        }
        origin_rank_by_node_id: dict[int, int] = {
            node_id: seed_rank_by_file_id.get(file_id, len(raw_seed_ids))
            for node_id, file_id in file_id_by_node_id.items()
        }

        # Multi-source BFS starts at every file represented by a seed chunk.
        distance_by_node_id: dict[int, int] = {
            node_id: 0 for node_id in file_id_by_node_id
        }
        frontier = set(distance_by_node_id)

        # 3. Traverse one frontier at a time. Each query is restricted to
        # the repository, IMPORTS edges, and the current frontier.
        stage_started = perf_counter()
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

            edge_query = select(GraphEdge).where(
                GraphEdge.repository_id == repository_id,
                GraphEdge.edge_type == GraphEdgeType.IMPORTS.value,
                or_(*edge_conditions),
            )

            if imported_symbol is not None:
                edge_query = edge_query.where(
                    GraphEdge.metadata_["imported_symbol"].as_string()
                    == imported_symbol
                )

            edges = list(self._db.scalars(edge_query).all())

            neighbor_ids: set[int] = set()
            parent_ids_by_neighbor: dict[int, set[int]] = defaultdict(set)

            for edge in sorted(
                edges,
                key=lambda item: (
                    item.source_node_id,
                    item.target_node_id,
                ),
            ):
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
                    parent_ids_by_neighbor[edge.target_node_id].add(
                        edge.source_node_id
                    )

                if (
                    direction in ("incoming", "both")
                    and edge.target_node_id in frontier
                ):
                    neighbor_ids.add(edge.source_node_id)
                    parent_ids_by_neighbor[edge.source_node_id].add(
                        edge.target_node_id
                    )

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
            next_paths: dict[int, tuple[str, ...]] = {}
            next_relationships: dict[int, tuple[str, ...]] = {}

            for node in neighbor_nodes:
                if node.repository_id != repository_id:
                    continue

                if node.node_type != GraphNodeType.FILE.value:
                    continue

                if node.file_id is None:
                    continue

                file_id_by_node_id[node.id] = node.file_id
                file_node_id_by_file_id[node.file_id] = node.id
                distance_by_node_id[node.id] = hop_count
                next_frontier.add(node.id)

                parent_paths = [
                    (
                        origin_rank_by_node_id.get(
                            parent_id, len(raw_seed_ids)
                        ),
                        path_by_node_id[parent_id],
                        parent_id,
                    )
                    for parent_id in parent_ids_by_neighbor[node.id]
                    if parent_id in path_by_node_id
                ]
                if parent_paths:
                    _, parent_path, parent_node_id = min(parent_paths)
                    next_paths[node.id] = parent_path + (
                        getattr(node, "qualified_name", None)
                        or str(node.file_id),
                    )
                    next_relationships[node.id] = (
                        relationships_by_node_id[parent_node_id]
                        + (GraphEdgeType.IMPORTS.value,)
                    )
                    origin_rank_by_node_id[node.id] = (
                        origin_rank_by_node_id.get(
                            parent_node_id, len(raw_seed_ids)
                        )
                    )

            for node_id, path in next_paths.items():
                path_by_node_id[node_id] = path
                relationships_by_node_id[node_id] = next_relationships[
                    node_id
                ]

            frontier = next_frontier

        self.last_latency_breakdown_ms["graph_traversal_ms"] = (
            perf_counter() - stage_started
        ) * 1000

        # 4. Group reachable source files by their shortest graph distance.
        file_ids_by_distance: dict[int, set[int]] = defaultdict(set)

        for node_id, distance in distance_by_node_id.items():
            file_id = file_id_by_node_id.get(node_id)

            if file_id is not None:
                file_ids_by_distance[distance].add(file_id)

        # 5. Filter first, cap each file independently, then spend the final
        # result budget round-robin across files. The stable hash order avoids
        # file-ID prefix bias while keeping evaluations reproducible.
        results: list[GraphRetrievalResult] = []
        stable_seed = ",".join(str(value) for value in sorted(seed_ids))

        stage_started = perf_counter()
        for distance in sorted(file_ids_by_distance):
            if len(results) >= top_k:
                break

            file_ids = file_ids_by_distance[distance]

            if not file_ids:
                continue

            effective_filters = filters or RetrievalFilters()
            candidate_query = (
                select(
                    GraphNode.id.label("node_id"),
                    GraphNode.file_id.label("file_id"),
                    GraphNode.chunk_id.label("chunk_id"),
                    Chunk.chunk_index.label("chunk_index"),
                )
                .join(
                    Chunk,
                    and_(
                        Chunk.id == GraphNode.chunk_id,
                        Chunk.file_id == GraphNode.file_id,
                        Chunk.repository_id == repository_id,
                    ),
                )
                .join(
                    RepositoryFile,
                    and_(
                        RepositoryFile.id == GraphNode.file_id,
                        RepositoryFile.repository_id == repository_id,
                    ),
                )
                .where(
                    GraphNode.repository_id == repository_id,
                    GraphNode.node_type == GraphNodeType.CHUNK.value,
                    GraphNode.file_id.in_(file_ids),
                    GraphNode.chunk_id.is_not(None),
                )
            )
            excluded_seed_ids = seed_ids - included_seed_ids
            if excluded_seed_ids:
                candidate_query = candidate_query.where(
                    GraphNode.chunk_id.not_in(excluded_seed_ids)
                )
            if query_vector is not None:
                query_distance = Embedding.embedding.cosine_distance(
                    list(query_vector)
                )
                candidate_query = candidate_query.add_columns(
                    query_distance.label("query_distance")
                ).join(
                    Embedding,
                    Embedding.chunk_id == Chunk.id,
                ).where(Embedding.model == embedding_model)
            if effective_filters.language:
                candidate_query = candidate_query.where(
                    RepositoryFile.language == effective_filters.language
                )
            if effective_filters.file_path:
                candidate_query = candidate_query.where(
                    or_(
                        RepositoryFile.relative_path
                        == effective_filters.file_path,
                        RepositoryFile.relative_path.like(
                            f"{effective_filters.file_path}%"
                        ),
                    )
                )
            if effective_filters.chunk_type:
                candidate_query = candidate_query.where(
                    Chunk.chunk_type == effective_filters.chunk_type
                )
            if effective_filters.symbol_name:
                candidate_query = candidate_query.where(
                    Chunk.symbol_name == effective_filters.symbol_name
                )
            if effective_filters.role:
                candidate_query = candidate_query.where(
                    RepositoryFile.role == effective_filters.role
                )
            if effective_filters.exclude_roles:
                candidate_query = candidate_query.where(
                    ~RepositoryFile.role.in_(
                        effective_filters.exclude_roles
                    )
                )

            eligible_subquery = candidate_query.subquery()
            remaining_budget = top_k - len(results)
            if query_vector is not None:
                best_file_distance = func.min(
                    eligible_subquery.c.query_distance
                ).label("best_distance")
                ranked_files = (
                    select(
                        eligible_subquery.c.file_id,
                        func.row_number()
                        .over(
                            order_by=(
                                best_file_distance,
                                eligible_subquery.c.file_id,
                            )
                        )
                        .label("file_order"),
                    )
                    .group_by(eligible_subquery.c.file_id)
                    .subquery()
                )
                ranked_candidates = (
                    select(
                        eligible_subquery.c.node_id,
                        eligible_subquery.c.file_id,
                        eligible_subquery.c.chunk_id,
                        func.row_number()
                        .over(
                            partition_by=eligible_subquery.c.file_id,
                            order_by=(
                                eligible_subquery.c.query_distance,
                                eligible_subquery.c.chunk_id,
                            ),
                        )
                        .label("file_rank"),
                        (1.0 - eligible_subquery.c.query_distance).label(
                            "query_score"
                        ),
                        ranked_files.c.file_order,
                    )
                    .join(
                        ranked_files,
                        ranked_files.c.file_id == eligible_subquery.c.file_id,
                    )
                    .where(ranked_files.c.file_order <= remaining_budget)
                    .subquery()
                )
                candidate_rows = self._db.execute(
                    select(
                        GraphNode,
                        ranked_candidates.c.query_score,
                        ranked_candidates.c.file_order,
                    )
                    .join(
                        ranked_candidates,
                        ranked_candidates.c.node_id == GraphNode.id,
                    )
                    .where(
                        ranked_candidates.c.file_rank <= max_per_file
                    )
                    .order_by(
                        ranked_candidates.c.file_order,
                        ranked_candidates.c.file_rank,
                    )
                ).all()
                selected_file_ids = list(
                    dict.fromkeys(row[0].file_id for row in candidate_rows)
                )
                candidate_nodes_with_scores = [
                    (row[0], float(row[1])) for row in candidate_rows
                ]
            else:
                eligible_file_ids = self._db.scalars(
                    select(eligible_subquery.c.file_id).distinct()
                ).all()
                selected_file_ids = sorted(
                    eligible_file_ids,
                    key=lambda file_id: hashlib.sha256(
                        f"{repository_id}:{stable_seed}:{distance}:{file_id}".encode()
                    ).digest(),
                )[:remaining_budget]
                if not selected_file_ids:
                    continue

                ranked_subquery = (
                    select(
                        eligible_subquery.c.node_id,
                        eligible_subquery.c.file_id,
                        eligible_subquery.c.chunk_id,
                        func.row_number()
                        .over(
                            partition_by=eligible_subquery.c.file_id,
                            order_by=(
                                eligible_subquery.c.chunk_index,
                                eligible_subquery.c.chunk_id,
                            ),
                        )
                        .label("file_rank"),
                    )
                    .where(eligible_subquery.c.file_id.in_(selected_file_ids))
                    .subquery()
                )
                candidate_statement = (
                    select(GraphNode)
                    .join(
                        ranked_subquery,
                        ranked_subquery.c.node_id == GraphNode.id,
                    )
                    .where(ranked_subquery.c.file_rank <= max_per_file)
                    .order_by(
                        ranked_subquery.c.file_id,
                        ranked_subquery.c.file_rank,
                    )
                )
                candidate_nodes_with_scores = [
                    (node, None)
                    for node in self._db.scalars(candidate_statement).all()
                ]

            candidates_by_file: dict[int, list[GraphRetrievalResult]] = (
                defaultdict(list)
            )

            for node, query_score in candidate_nodes_with_scores:
                if node.repository_id != repository_id:
                    continue

                if node.node_type != GraphNodeType.CHUNK.value:
                    continue

                if node.chunk_id is None or node.file_id is None:
                    continue

                if node.chunk_id in seed_ids and node.chunk_id not in included_seed_ids:
                    continue

                # Shortest distance is the primary graph relevance signal.
                source_node_id = file_node_id_by_file_id.get(node.file_id)
                graph_path = (
                    path_by_node_id.get(source_node_id, ())
                    if source_node_id is not None
                    else ()
                )
                relationship_types = (
                    relationships_by_node_id.get(source_node_id, ())
                    if source_node_id is not None
                    else ()
                )
                result = GraphRetrievalResult(
                    chunk_id=node.chunk_id,
                    file_id=node.file_id,
                    hop_count=distance,
                    score=1.0 / (distance + 1),
                    query_score=query_score,
                    graph_path=graph_path,
                    relationship_types=(
                        relationship_types + (GraphEdgeType.HAS_CHUNK.value,)
                    ),
                )
                candidates_by_file[node.file_id].append(result)

            file_order = selected_file_ids
            for rank_in_file in range(max_per_file):
                for file_id in file_order:
                    file_candidates = candidates_by_file[file_id]
                    file_candidates.sort(key=lambda item: item.chunk_id)
                    if len(file_candidates) <= rank_in_file:
                        continue
                    results.append(file_candidates[rank_in_file])
                    if len(results) >= top_k:
                        break
                if len(results) >= top_k:
                    break

        self.last_latency_breakdown_ms["graph_candidate_query_ms"] = (
            perf_counter() - stage_started
        ) * 1000
        return results[:top_k]

    @staticmethod
    def _validate_parameters(
        *,
        repository_id: int,
        max_hops: int,
        top_k: int,
        direction: str,
        max_per_file: int,
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

        if type(max_per_file) is not int or max_per_file < 1:
            raise ValueError("max_per_file must be a positive integer")
