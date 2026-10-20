
from collections import defaultdict
from collections.abc import Sequence

from app.services.retrieval.graph_retriever import GraphRetrievalResult


def select_graph_candidates(
    candidates: Sequence[GraphRetrievalResult],
    *,
    top_k: int,
    max_per_file: int = 2,
) -> list[GraphRetrievalResult]:
    """Select graph candidates with per-file diversity.

    Candidates are selected round-robin across files, prioritizing
    shorter graph distances. This function only filters graph candidates;
    it never removes baseline retrieval results.
    """
    if top_k < 0:
        raise ValueError("top_k must be non-negative")
    if max_per_file < 1:
        raise ValueError("max_per_file must be at least 1")
    if top_k == 0 or not candidates:
        return []

    # Deduplicate chunk IDs, preferring the shortest graph distance.
    by_chunk_id: dict[int, GraphRetrievalResult] = {}

    for candidate in candidates:
        if candidate.hop_count < 0:
            raise ValueError("hop_count must be non-negative")

        previous = by_chunk_id.get(candidate.chunk_id)
        if previous is None or (
            candidate.hop_count,
            -candidate.score,
            candidate.file_id,
        ) < (
            previous.hop_count,
            -previous.score,
            previous.file_id,
        ):
            by_chunk_id[candidate.chunk_id] = candidate

    grouped: dict[int, list[GraphRetrievalResult]] = defaultdict(list)

    for candidate in by_chunk_id.values():
        grouped[candidate.file_id].append(candidate)

    for file_candidates in grouped.values():
        file_candidates.sort(
            key=lambda item: (
                item.hop_count,
                -item.score,
                item.chunk_id,
            )
        )

    selected: list[GraphRetrievalResult] = []

    # Round-robin selection: first candidate from each file, then
    # second candidate from each file, up to max_per_file.
    for rank_in_file in range(max_per_file):
        round_candidates = [
            file_candidates[rank_in_file]
            for file_candidates in grouped.values()
            if len(file_candidates) > rank_in_file
        ]

        round_candidates.sort(
            key=lambda item: (
                item.hop_count,
                -item.score,
                item.file_id,
                item.chunk_id,
            )
        )

        selected.extend(round_candidates)

        if len(selected) >= top_k:
            return selected[:top_k]

    return selected[:top_k]