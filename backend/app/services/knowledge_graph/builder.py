
from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.graph_edge import GraphEdge, GraphEdgeType
from app.models.graph_node import GraphNode, GraphNodeType
from app.models.repository import Repository
from app.models.repository_file import RepositoryFile
from app.models.repository_symbol import RepositorySymbol


class KnowledgeGraphBuilder:
    """Build a repository-scoped knowledge graph from stored records."""

    def build(self, db: Session, repository_id: int) -> dict[str, int]:
        """Build or rebuild the graph for one repository."""

        repository = db.get(Repository, repository_id)

        if repository is None:
            raise ValueError(
                f"Repository {repository_id} does not exist"
            )

        files = list(
            db.scalars(
                select(RepositoryFile)
                .where(RepositoryFile.repository_id == repository_id)
                .order_by(RepositoryFile.relative_path)
            ).all()
        )

        symbols = list(
            db.scalars(
                select(RepositorySymbol)
                .where(RepositorySymbol.repository_id == repository_id)
                .order_by(
                    RepositorySymbol.file_id,
                    RepositorySymbol.id,
                )
            ).all()
        )

        chunks = list(
            db.scalars(
                select(Chunk)
                .where(Chunk.repository_id == repository_id)
                .order_by(
                    Chunk.file_id,
                    Chunk.chunk_index,
                )
            ).all()
        )

        existing_nodes = list(
            db.scalars(
                select(GraphNode).where(
                    GraphNode.repository_id == repository_id
                )
            ).all()
        )

        nodes_by_identity = {
            (node.node_type, node.entity_key): node
            for node in existing_nodes
        }

        desired_identities: set[tuple[str, str]] = set()

        file_nodes: dict[int, GraphNode] = {}
        symbol_nodes: dict[int, GraphNode] = {}
        chunk_nodes: dict[int, GraphNode] = {}

        def upsert_node(
            node_type: GraphNodeType,
            entity_key: str,
            name: str,
            *,
            qualified_name: str | None = None,
            file_id: int | None = None,
            symbol_id: int | None = None,
            chunk_id: int | None = None,
            metadata: dict[str, Any] | None = None,
        ) -> GraphNode:
            identity = (node_type.value, entity_key)
            desired_identities.add(identity)

            node = nodes_by_identity.get(identity)

            if node is None:
                node = GraphNode(
                    repository_id=repository_id,
                    node_type=node_type.value,
                    entity_key=entity_key,
                    name=name[:255],
                    qualified_name=qualified_name,
                    file_id=file_id,
                    symbol_id=symbol_id,
                    chunk_id=chunk_id,
                    node_metadata=metadata or {},
                )
                db.add(node)
                nodes_by_identity[identity] = node
            else:
                node.name = name[:255]
                node.qualified_name = qualified_name
                node.file_id = file_id
                node.symbol_id = symbol_id
                node.chunk_id = chunk_id
                node.node_metadata = metadata or {}

            return node

        # 1. Repository node.
        root = upsert_node(
            GraphNodeType.REPOSITORY,
            f"repository:{repository_id}",
            repository.name or f"repository-{repository_id}",
            metadata={
                "primary_language": repository.primary_language,
            },
        )

        # 2. File nodes.
        for repo_file in files:
            file_node = upsert_node(
                GraphNodeType.FILE,
                f"file:{repo_file.relative_path}",
                repo_file.filename,
                qualified_name=repo_file.relative_path,
                file_id=repo_file.id,
                metadata={
                    "relative_path": repo_file.relative_path,
                    "language": repo_file.language,
                    "category": repo_file.category.value,
                    "role": repo_file.role.value,
                },
            )
            file_nodes[repo_file.id] = file_node

        # 3. Symbol nodes.
        for symbol in symbols:
            symbol_node = upsert_node(
                GraphNodeType.SYMBOL,
                f"symbol:{symbol.file_id}:{symbol.id}",
                symbol.name,
                qualified_name=symbol.qualified_name,
                file_id=symbol.file_id,
                symbol_id=symbol.id,
                metadata={
                    "symbol_type": symbol.symbol_type,
                    "location": symbol.location or {},
                    "symbol_metadata": symbol.symbol_metadata or {},
                },
            )
            symbol_nodes[symbol.id] = symbol_node

        # 4. Chunk nodes.
        for chunk in chunks:
            chunk_node = upsert_node(
                GraphNodeType.CHUNK,
                f"chunk:{chunk.file_id}:{chunk.chunk_index}",
                chunk.symbol_name
                or f"{chunk.chunk_type.value} chunk {chunk.chunk_index}",
                qualified_name=chunk.qualified_name,
                file_id=chunk.file_id,
                chunk_id=chunk.id,
                metadata={
                    "chunk_index": chunk.chunk_index,
                    "chunk_type": chunk.chunk_type.value,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "token_count": chunk.token_count,
                    "parent_symbol": chunk.parent_symbol,
                },
            )
            chunk_nodes[chunk.id] = chunk_node

        # Persist pending nodes to obtain their database IDs.
        db.flush()

        # Rebuild only this repository's edges.
        db.execute(
            delete(GraphEdge).where(
                GraphEdge.repository_id == repository_id
            )
        )
        db.flush()

        edges: dict[tuple[int, int, str], GraphEdge] = {}

        def add_edge(
            source: GraphNode,
            target: GraphNode,
            edge_type: GraphEdgeType,
            metadata: dict[str, Any] | None = None,
        ) -> None:
            if source.id == target.id:
                return

            key = (source.id, target.id, edge_type.value)

            if key not in edges:
                edges[key] = GraphEdge(
                    repository_id=repository_id,
                    source_node_id=source.id,
                    target_node_id=target.id,
                    edge_type=edge_type.value,
                    metadata_=metadata or {},
                )

        # 5. Repository CONTAINS file.
        for repo_file in files:
            add_edge(
                root,
                file_nodes[repo_file.id],
                GraphEdgeType.CONTAINS,
            )

        # 6. File DEFINES symbol.
        for symbol in symbols:
            file_node = file_nodes.get(symbol.file_id)
            symbol_node = symbol_nodes[symbol.id]

            if file_node is not None:
                add_edge(
                    file_node,
                    symbol_node,
                    GraphEdgeType.DEFINES,
                )

        # 7. File HAS_CHUNK chunk.
        for chunk in chunks:
            file_node = file_nodes.get(chunk.file_id)
            chunk_node = chunk_nodes[chunk.id]

            if file_node is not None:
                add_edge(
                    file_node,
                    chunk_node,
                    GraphEdgeType.HAS_CHUNK,
                )

        # 8. Build normalized module-to-file lookup tables.
        def normalize_module_path(value: str) -> str:
            value = value.strip().replace("\\", "/").strip("/")
            if value.casefold().endswith(".py"):
                value = value[:-3]
            return value.casefold()


        # Sets preserve collisions instead of silently overwriting files.
        exact_paths: dict[str, set[int]] = {}
        suffix_paths: dict[str, set[int]] = {}
        nodes_by_id: dict[int, GraphNode] = {}

        def register_exact(path: str, node: GraphNode) -> None:
            normalized = normalize_module_path(path)
            if not normalized:
                return

            exact_paths.setdefault(normalized, set()).add(node.id)
            nodes_by_id[node.id] = node

        def register_suffix(path: str, node: GraphNode) -> None:
            """Register a path alias without silently resolving ambiguity."""
            normalized = normalize_module_path(path)

            if not normalized:
                return

            suffix_paths.setdefault(normalized, set()).add(node.id)
            nodes_by_id[node.id] = node

        for repo_file in files:
            relative = PurePosixPath(
                repo_file.relative_path.replace("\\", "/")
            ).as_posix()

            node = file_nodes[repo_file.id]
            normalized_path = normalize_module_path(relative)

            register_exact(normalized_path, node)
            register_suffix(normalized_path, node)

            parts = normalized_path.split("/")

            # Support repository prefixes such as backend/ or src/.
            for index in range(1, len(parts)):
                register_suffix("/".join(parts[index:]), node)

            # Treat Python __init__.py as its package module.
            if PurePosixPath(relative).name == "__init__.py":
                package_path = normalize_module_path(
                    str(PurePosixPath(relative).parent)
                )

                if package_path:
                    register_exact(package_path, node)
                    register_suffix(package_path, node)

                    package_parts = package_path.split("/")
                    for index in range(1, len(package_parts)):
                        register_suffix(
                            "/".join(package_parts[index:]),
                            node,
                        )

        files_by_id = {repo_file.id: repo_file for repo_file in files}

        def resolve_normalized_path(
            path: str,
        ) -> tuple[GraphNode | None, bool]:
            """
            Return (target, matched).

            A matched but ambiguous path is not guessed, and must not
            fall through to a less-specific alias.
            """
            normalized = normalize_module_path(path)
            if not normalized:
                return None, False

            exact_ids = exact_paths.get(normalized, set())

            if exact_ids:
                if len(exact_ids) == 1:
                    return nodes_by_id[next(iter(exact_ids))], True
                return None, True

            matching_ids = suffix_paths.get(normalized, set())

            if matching_ids:
                if len(matching_ids) == 1:
                    return nodes_by_id[next(iter(matching_ids))], True
                return None, True

            return None, False

        def resolve_import_target(
            module: str,
            source_file: RepositoryFile,
            imported_symbol: Any,
        ) -> GraphNode | None:
            # Resolve Python relative imports using the importing file's
            # package rather than stripping dots and guessing a root module.
            leading_dots = len(module) - len(module.lstrip("."))

            if leading_dots:
                source_path = PurePosixPath(
                    source_file.relative_path.replace("\\", "/")
                )
                package_parts = list(source_path.parent.parts)

                # One dot means the current package. Each additional dot
                # moves up one package level.
                if leading_dots > 1:
                    package_parts = package_parts[
                        : max(0, len(package_parts) - (leading_dots - 1))
                    ]

                remainder = module[leading_dots:].replace(".", "/").strip("/")
                package_path = "/".join(package_parts)
                candidates: list[str] = []

                if remainder:
                    candidates.append(
                        "/".join(
                            part
                            for part in (package_path, remainder)
                            if part
                        )
                    )
                else:
                    # For `from . import helper`, try the imported module
                    # before falling back to the package's __init__.py.
                    if (
                        isinstance(imported_symbol, str)
                        and imported_symbol.strip()
                    ):
                        candidates.append(
                            "/".join(
                                part
                                for part in (
                                    package_path,
                                    imported_symbol.replace(".", "/").strip("/"),
                                )
                                if part
                            )
                        )

                    if package_path:
                        candidates.append(package_path)

                for candidate in candidates:
                    target, matched = resolve_normalized_path(candidate)
                    if matched:
                        return target

                return None

            # Absolute imports use dotted module notation. For imports such as
            # `from package import helper`, prefer an indexed submodule file
            # (`package/helper.py`) before falling back to the package module
            # (`package/__init__.py`). This avoids pointing the edge at the
            # package initializer when the imported name is itself a module.
            normalized_module = module.replace(".", "/")
            candidates: list[str] = []

            if isinstance(imported_symbol, str) and imported_symbol.strip():
                imported_name = imported_symbol.strip().replace(".", "/").strip("/")
                if imported_name:
                    candidates.append(f"{normalized_module}/{imported_name}")

            candidates.append(normalized_module)

            for candidate in candidates:
                target, matched = resolve_normalized_path(candidate)
                if matched:
                    return target

            return None

        # 9. Resolve import symbols to indexed files.
        for symbol in symbols:
            if symbol.symbol_type.lower() != "import":
                continue

            metadata = symbol.symbol_metadata or {}
            module = metadata.get("module")

            if not isinstance(module, str) or not module.strip():
                continue

            source_file = files_by_id.get(symbol.file_id)
            if source_file is None:
                continue

            target_node = resolve_import_target(
                module.strip(),
                source_file,
                metadata.get("symbol"),
            )

            # Unresolved or ambiguous imports are intentionally skipped.
            if target_node is None:
                continue

            source_node = file_nodes.get(symbol.file_id)

            if source_node is None or source_node.id == target_node.id:
                continue

            add_edge(
                source_node,
                target_node,
                GraphEdgeType.IMPORTS,
                metadata={
                    "import_symbol_id": symbol.id,
                    "module": module,
                    "imported_symbol": metadata.get("symbol"),
                    "alias": metadata.get("alias"),
                },
            )

        # 10. Insert reconstructed relationships.
        db.add_all(edges.values())

        # 11. Remove nodes no longer represented by source records.
        stale_nodes = [
            node
            for identity, node in nodes_by_identity.items()
            if identity not in desired_identities
        ]

        for node in stale_nodes:
            db.delete(node)

        db.flush()

        result = {
            "nodes": len(desired_identities),
            "edges": len(edges),
            "files": len(files),
            "symbols": len(symbols),
            "chunks": len(chunks),
        }

        db.commit()
        return result


knowledge_graph_builder = KnowledgeGraphBuilder()
