"""Independent graph seed selection using the existing repository BM25 index."""

from __future__ import annotations

import re
from time import perf_counter

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.graph_node import GraphNode, GraphNodeType
from app.models.repository_file import RepositoryFile
from app.services.retrieval.filters import RetrievalFilters
from app.services.retrieval.lexical.retriever import LexicalRetriever
from app.services.retrieval.lexical.tokenizer import tokenize_code

MAX_GRAPH_SEED_CANDIDATES = 80
_QUERY_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "does", "for",
    "from", "how", "in", "into", "is", "it", "of", "on", "or", "the",
    "through", "to", "what", "which", "where", "who", "with",
}


class GraphSeedRetriever:
    """Find graph entry chunks without using Hybrid V2's result ranking.

    Candidate documents come from RepoIntel's cached BM25 index. A bounded
    metadata lookup over those candidates adds exact symbol, qualified-name,
    and file/module-path matches, then enforces per-file diversity.
    """

    def __init__(self, db: Session, lexical_retriever: LexicalRetriever) -> None:
        self._db = db
        self._lexical_retriever = lexical_retriever
        self.last_latency_ms = 0.0
        self.last_candidate_count = 0

    def retrieve(
        self,
        *,
        repository_id: int,
        query: str,
        top_k: int,
        filters: RetrievalFilters | None = None,
        candidate_pool_k: int | None = None,
        max_per_file: int = 1,
    ) -> list[int]:
        if repository_id <= 0:
            raise ValueError("repository_id must be positive")
        if top_k <= 0:
            return []
        if max_per_file <= 0:
            raise ValueError("max_per_file must be positive")

        pool_size = min(
            MAX_GRAPH_SEED_CANDIDATES,
            candidate_pool_k
            if candidate_pool_k is not None
            else max(top_k * 8, top_k),
        )
        if pool_size < top_k:
            raise ValueError("candidate_pool_k must be at least top_k")

        started = perf_counter()
        lexical_results = self._lexical_retriever.search(
            repository_id=repository_id,
            query=query,
            top_k=pool_size,
            filters=filters,
        )
        self.last_candidate_count = len(lexical_results)
        candidate_ids = [result.chunk_id for result in lexical_results]
        if not candidate_ids:
            self.last_latency_ms = (perf_counter() - started) * 1000
            return []

        lexical_rank = {
            result.chunk_id: (rank, result.score)
            for rank, result in enumerate(lexical_results)
        }
        query_tokens = set(tokenize_code(query)) - _STOPWORDS
        identifier_tokens = {
            token.casefold()
            for token in _QUERY_TOKEN_RE.findall(query)
            if "_" in token
            or any(char.isdigit() for char in token)
            or any(char.isupper() for char in token)
        }

        statement = (
            select(
                Chunk.id,
                Chunk.file_id,
                Chunk.symbol_name,
                Chunk.qualified_name,
                RepositoryFile.relative_path,
                RepositoryFile.filename,
            )
            .join(
                GraphNode,
                and_(
                    GraphNode.chunk_id == Chunk.id,
                    GraphNode.file_id == Chunk.file_id,
                    GraphNode.repository_id == repository_id,
                    GraphNode.node_type == GraphNodeType.CHUNK.value,
                ),
            )
            .join(
                RepositoryFile,
                and_(
                    RepositoryFile.id == Chunk.file_id,
                    RepositoryFile.repository_id == repository_id,
                ),
            )
            .where(
                Chunk.repository_id == repository_id,
                Chunk.id.in_(candidate_ids),
            )
        )
        effective_filters = filters or RetrievalFilters()
        if effective_filters.language:
            statement = statement.where(
                RepositoryFile.language == effective_filters.language
            )
        if effective_filters.file_path:
            statement = statement.where(
                or_(
                    RepositoryFile.relative_path
                    == effective_filters.file_path,
                    RepositoryFile.relative_path.like(
                        f"{effective_filters.file_path}%"
                    ),
                )
            )
        if effective_filters.chunk_type:
            statement = statement.where(
                Chunk.chunk_type == effective_filters.chunk_type
            )
        if effective_filters.symbol_name:
            statement = statement.where(
                Chunk.symbol_name == effective_filters.symbol_name
            )
        if effective_filters.role:
            statement = statement.where(
                RepositoryFile.role == effective_filters.role
            )
        if effective_filters.exclude_roles:
            statement = statement.where(
                ~RepositoryFile.role.in_(effective_filters.exclude_roles)
            )

        rows = self._db.execute(statement).all()
        ranked: list[tuple[int, int, int, int, int, int, int]] = []
        for (
            chunk_id,
            file_id,
            symbol_name,
            qualified_name,
            relative_path,
            filename,
        ) in rows:
            metadata_tokens = set(
                tokenize_code(
                    " ".join(
                        value
                        for value in (
                            symbol_name,
                            qualified_name,
                            relative_path,
                            filename,
                        )
                        if value
                    )
                )
            )
            matched_tokens = query_tokens & metadata_tokens
            matched_identifiers = identifier_tokens & metadata_tokens
            rank, _score = lexical_rank[chunk_id]
            normalized_symbol = (symbol_name or "").casefold().strip()
            normalized_qualified = (
                (qualified_name or "").casefold().strip()
            )
            exact_symbol_match = int(
                normalized_symbol in identifier_tokens
            )
            exact_qualified_match = int(
                normalized_qualified in identifier_tokens
                or normalized_qualified.rsplit(".", 1)[-1]
                in identifier_tokens
            )
            # Exact declared-name evidence is a stronger, auditable signal
            # than token counts. BM25 rank then breaks ties without mixing
            # incomparable scores or inventing weights.
            ranked.append(
                (
                    -exact_symbol_match,
                    -exact_qualified_match,
                    -len(matched_identifiers),
                    -len(matched_tokens),
                    rank,
                    chunk_id,
                    file_id,
                )
            )

        ranked.sort()
        selected: list[int] = []
        counts_by_file: dict[int, int] = {}
        for _, _, _, _, _, chunk_id, file_id in ranked:
            if counts_by_file.get(file_id, 0) >= max_per_file:
                continue
            selected.append(chunk_id)
            counts_by_file[file_id] = counts_by_file.get(file_id, 0) + 1
            if len(selected) >= top_k:
                break

        self.last_latency_ms = (perf_counter() - started) * 1000
        return selected
