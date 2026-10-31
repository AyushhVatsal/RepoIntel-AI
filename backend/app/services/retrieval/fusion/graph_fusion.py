
"""Experimental fusion of baseline retrieval rankings and graph candidates."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from app.services.retrieval.graph_retriever import GraphRetrievalResult
from app.services.retrieval.result import RetrievalResult

logger = logging.getLogger(__name__)


class GraphFusion:
    """Blend normalized baseline relevance and graph proximity scores.

    Baseline scores use min-max normalization.
    Graph candidates receive a distance prior of 1 / (hop_count + 1).

    baseline_reserve is an experimental selection constraint. It preserves
    leading baseline candidates in the final top-k without changing their
    fused scores. Its default of zero retains the existing selection policy.
    """

    def __init__(
        self,
        *,
        baseline_weight: float = 0.75,
        graph_weight: float = 0.25,
    ) -> None:
        if baseline_weight < 0:
            raise ValueError("baseline_weight must be non-negative")
        if graph_weight < 0:
            raise ValueError("graph_weight must be non-negative")
        if not 0.0 <= baseline_weight <= 1.0:
            raise ValueError("baseline_weight must be between 0 and 1")
        if not 0.0 <= graph_weight <= 1.0:
            raise ValueError("graph_weight must be between 0 and 1")
        if abs(baseline_weight + graph_weight - 1.0) > 1e-9:
            raise ValueError("weights must sum to 1.0")

        self._baseline_weight = baseline_weight
        self._graph_weight = graph_weight

    @staticmethod
    def _normalize(scores: dict[int, float]) -> dict[int, float]:
        """Min-max normalize scores; equal scores receive 1.0."""
        if not scores:
            return {}

        minimum = min(scores.values())
        maximum = max(scores.values())

        if maximum == minimum:
            return {chunk_id: 1.0 for chunk_id in scores}

        score_range = maximum - minimum
        return {
            chunk_id: (score - minimum) / score_range
            for chunk_id, score in scores.items()
        }

    def fuse(
        self,
        *,
        baseline_results: list[RetrievalResult],
        graph_results: Sequence[GraphRetrievalResult],
        top_k: int,
        baseline_reserve: int = 0,
    ) -> list[RetrievalResult]:
        """Fuse candidates and optionally preserve leading baseline results."""
        if top_k <= 0:
            return []
        if baseline_reserve < 0:
            raise ValueError("baseline_reserve must be non-negative")

        # Preserve the first occurrence of each baseline chunk and its rank.
        baseline_by_id: dict[int, RetrievalResult] = {}
        for result in baseline_results:
            baseline_by_id.setdefault(result.chunk_id, result)

        normalized_baseline = self._normalize(
            {
                chunk_id: result.score
                for chunk_id, result in baseline_by_id.items()
            }
        )

        # Keep the shortest graph distance for each candidate.
        graph_hops: dict[int, int] = {}
        graph_query_scores: dict[int, float] = {}
        for result in graph_results:
            if result.hop_count < 0:
                raise ValueError("graph hop_count must be non-negative")

            previous_hop = graph_hops.get(result.chunk_id)
            if previous_hop is None or result.hop_count < previous_hop:
                graph_hops[result.chunk_id] = result.hop_count
            if result.query_score is not None:
                graph_query_scores[result.chunk_id] = max(
                    graph_query_scores.get(result.chunk_id, float("-inf")),
                    result.query_score,
                )

        normalized_graph = self._normalize(graph_query_scores)

        candidate_ids = sorted(set(baseline_by_id) | set(graph_hops))
        fused_by_id: dict[int, RetrievalResult] = {}

        for chunk_id in candidate_ids:
            baseline_result = baseline_by_id.get(chunk_id)
            baseline_score = normalized_baseline.get(chunk_id, 0.0)

            if chunk_id not in graph_hops:
                graph_score = 0.0
            elif graph_query_scores:
                graph_score = normalized_graph.get(chunk_id, 0.0) / (
                    graph_hops[chunk_id] + 1
                )
            else:
                graph_score = 1.0 / (graph_hops[chunk_id] + 1)

            final_score = (
                self._baseline_weight * baseline_score
                + self._graph_weight * graph_score
            )

            fused_by_id[chunk_id] = RetrievalResult(
                chunk_id=chunk_id,
                score=final_score,
                dense_score=(
                    baseline_result.dense_score
                    if baseline_result is not None
                    else None
                ),
                retrieval_score=final_score,
            )

            logger.debug(
                "graph_fusion_candidate chunk_id=%s baseline_present=%s "
                "baseline_raw=%s baseline_normalized=%.6f graph_hop=%s "
                "graph_score=%.6f final_score=%.6f",
                chunk_id,
                baseline_result is not None,
                baseline_result.score if baseline_result is not None else None,
                baseline_score,
                graph_hops.get(chunk_id),
                graph_score,
                final_score,
            )

        ranked = sorted(
            fused_by_id.values(),
            key=lambda result: (-result.score, result.chunk_id),
        )

        reserve_count = min(
            baseline_reserve,
            top_k,
            len(baseline_by_id),
        )

        if reserve_count == 0:
            return ranked[:top_k]

        # Preserve the first N baseline candidates, then fill remaining slots
        # with the highest-scoring candidates not already reserved.
        reserved_ids = list(baseline_by_id)[:reserve_count]
        selected_ids = set(reserved_ids)

        selected = [fused_by_id[chunk_id] for chunk_id in reserved_ids]
        remaining = [
            result
            for result in ranked
            if result.chunk_id not in selected_ids
        ]

        selected.extend(remaining[: top_k - len(selected)])
        selected.sort(key=lambda result: (-result.score, result.chunk_id))

        logger.debug(
            "graph_fusion_selection top_k=%s baseline_reserve=%s "
            "reserved_ids=%s returned_ids=%s",
            top_k,
            reserve_count,
            reserved_ids,
            [result.chunk_id for result in selected],
        )

        return selected
