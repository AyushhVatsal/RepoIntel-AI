from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from time import perf_counter

from sqlalchemy.orm import Session

from app.crud.chunk import chunk_crud
from app.crud.repository import repository_crud
from app.crud.repository_file import repository_file_crud
from app.crud.repository_symbol import repository_symbol_crud
from app.exceptions.repository import (
    RepositoryAlreadyExistsError,
    RepositoryNotFoundError,
)
from app.models.repository import (
    GraphBuildStatus,
    Repository,
    RepositoryStatus,
)
from app.models.repository_file import LanguageSupportTier
from app.schemas.repository import RepositoryCreate
from app.services.chunking.service import ChunkingService
from app.services.embedding.models.embedding_config import EmbeddingConfig
from app.services.embedding.providers.local import (
    get_local_embedding_provider,
)
from app.services.embedding.service import EmbeddingService
from app.services.knowledge_graph.lifecycle import build_repository_graph
from app.services.parsers.models.file_content import FileContent
from app.services.parsers.parser_service import ParserService
from app.services.parsers.symbol_converter import SymbolConverter
from app.services.repository.clone_service import (
    clone_service,
    remove_clone_directory,
)
from app.services.repository.framework_detector import (
    framework_detection_service,
)
from app.services.repository.metadata_service import metadata_service
from app.services.repository.scanner_service import scanner_service
from app.services.retrieval.lexical.manager import get_bm25_index_manager
from app.services.vector_store.service import VectorStoreService

logger = logging.getLogger(__name__)

INDEX_PROGRESS_COMMIT_FILES = 10


class RepositoryService:
    """
    Coordinate the complete repository indexing workflow.

    Responsibilities
    ----------------
    - Create repository record
    - Clone repository
    - Scan repository
    - Parse supported files
    - Persist repository symbols
    - Generate code-aware chunks
    - Persist chunks
    - Generate embeddings
    - Persist embeddings
    - Detect framework
    - Calculate metadata
    - Update repository status
    """

    def __init__(
        self,
        parser_service: ParserService | None = None,
        chunking_service: ChunkingService | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        """
        Initialize repository indexing dependencies.

        Services can be injected for testing or alternative
        implementations. Production defaults use the existing
        parser, chunker, and local BGE embedding pipeline.
        """

        self.parser_service = parser_service
        self.chunking_service = chunking_service
        self.embedding_service = embedding_service

    def _initialize_pipeline(self) -> None:
        """Initialize CPU/model-backed services inside the worker, not POST."""
        if self.parser_service is None:
            self.parser_service = ParserService()
        if self.chunking_service is None:
            self.chunking_service = ChunkingService()
        if self.embedding_service is None:
            embedding_config = EmbeddingConfig()
            # Share the process-wide provider with retrieval so indexing and
            # querying do not each load a separate copy of the same weights.
            embedding_provider = get_local_embedding_provider(
                embedding_config.model,
            )
            self.embedding_service = EmbeddingService(
                provider=embedding_provider,
                config=embedding_config,
            )

    def index_repository(
        self,
        db: Session,
        owner_id: int,
        repository_in: RepositoryCreate,
    ):
        """
        Clone, scan, parse, chunk, embed and index a repository.
        """

        repository = self.create_indexing_job(db, owner_id, repository_in)
        return self.process_indexing_job(db, repository)

    def create_indexing_job(
        self,
        db: Session,
        owner_id: int,
        repository_in: RepositoryCreate,
    ) -> Repository:
        """Persist a queued repository before the indexing work begins."""
        github_url = str(repository_in.github_url)
        existing_repository = repository_crud.get_by_github_url(
            db=db,
            github_url=github_url,
            owner_id=owner_id,
        )
        if (
            existing_repository is not None
            and existing_repository.status != RepositoryStatus.FAILED
        ):
            raise RepositoryAlreadyExistsError(
                "Repository has already been indexed."
            )

        if existing_repository is not None:
            return repository_crud.update(
                db=db,
                repository=existing_repository,
                status=RepositoryStatus.PENDING,
                indexing_progress=0,
                indexing_stage="queued",
                indexing_processed_files=0,
                indexing_total_files=0,
                indexing_error=None,
                graph_status=GraphBuildStatus.NOT_BUILT.value,
                graph_error=None,
            )

        return repository_crud.create(
            db=db,
            repository_in=repository_in,
            owner_id=owner_id,
            status=RepositoryStatus.PENDING,
            name=clone_service.get_repository_name(github_url),
            clone_path="",
            indexing_progress=0,
            indexing_stage="queued",
            indexing_processed_files=0,
            indexing_total_files=0,
            indexing_error=None,
            graph_status=GraphBuildStatus.NOT_BUILT.value,
            graph_error=None,
        )

    def process_indexing_job(
        self,
        db: Session,
        repository: Repository,
    ) -> Repository:
        """Run indexing for an already-persisted job record."""
        repository_in = RepositoryCreate(github_url=repository.github_url)
        indexing_started = perf_counter()
        clone_elapsed_ms = 0.0
        scan_elapsed_ms = 0.0
        file_persistence_elapsed_ms = 0.0
        parse_elapsed_ms = 0.0
        chunk_elapsed_ms = 0.0
        embedding_elapsed_ms = 0.0
        vector_store_elapsed_ms = 0.0
        commit_elapsed_ms = 0.0
        framework_elapsed_ms = 0.0
        metadata_elapsed_ms = 0.0
        original_expire_on_commit = db.expire_on_commit
        db.expire_on_commit = False
        try:
            stage_started = perf_counter()
            self._initialize_pipeline()
            pipeline_setup_elapsed_ms = (perf_counter() - stage_started) * 1000
            self.embedding_service.reset_profile()
            # -----------------------------------------------------
            # Clone repository
            # -----------------------------------------------------

            repository_crud.update(
                db=db,
                repository=repository,
                status=RepositoryStatus.CLONING,
                indexing_stage="cloning",
                indexing_progress=1,
                indexing_error=None,
            )

            stage_started = perf_counter()
            clone_path = clone_service.clone(
                repository_in.github_url,
                str(repository.id),
            )
            default_branch = clone_service.get_default_branch(
                clone_path,
            )
            clone_elapsed_ms = (perf_counter() - stage_started) * 1000

            repository_crud.update(
                db=db,
                repository=repository,
                clone_path=str(clone_path),
                default_branch=default_branch,
            )

            # -----------------------------------------------------
            # Scan repository
            # -----------------------------------------------------

            repository_crud.update(
                db=db,
                repository=repository,
                status=RepositoryStatus.SCANNING,
                indexing_stage="scanning",
                indexing_progress=5,
            )

            scan_started = perf_counter()
            all_repository_files = scanner_service.scan(
                repository_id=repository.id,
                repository_path=clone_path,
            )
            scan_elapsed_ms = (perf_counter() - scan_started) * 1000

            supported_repository_files = [
                repository_file
                for repository_file in all_repository_files
                if repository_file.support_tier != LanguageSupportTier.NONE
            ]

            # -----------------------------------------------------
            # Persist supported files
            # -----------------------------------------------------

            stage_started = perf_counter()
            persisted_files = repository_file_crud.create_many(
                db=db,
                files=supported_repository_files,
                commit=False,
            )
            file_persistence_elapsed_ms = (
                perf_counter() - stage_started
            ) * 1000

            print(
                f"[FILES PERSISTED] "
                f"scanned={len(all_repository_files)} "
                f"supported={len(supported_repository_files)} "
                f"persisted={len(persisted_files)}"
            )

            # -----------------------------------------------------
            # Parse, chunk and embed supported files
            # -----------------------------------------------------

            repository_crud.update(
                db=db,
                repository=repository,
                status=RepositoryStatus.PARSING,
                indexing_stage="parsing",
                indexing_progress=10,
                indexing_processed_files=0,
                indexing_total_files=len(persisted_files),
            )

            vector_store_service = VectorStoreService(db=db)
            pending_chunks = []
            pending_chunk_rows = []

            def persist_embedding_batch() -> None:
                nonlocal embedding_elapsed_ms, vector_store_elapsed_ms
                if not pending_chunks:
                    return

                # One flush assigns chunk IDs for all files in this bounded
                # group before embedding rows are written.
                db.flush()

                stage_started = perf_counter()
                embedding_results = self.embedding_service.embed(
                    pending_chunks,
                )
                embedding_elapsed_ms += (
                    perf_counter() - stage_started
                ) * 1000
                if len(embedding_results) != len(pending_chunk_rows):
                    raise RuntimeError(
                        "Embedding result count does not match persisted "
                        "chunk count."
                    )

                chunk_map = {
                    (chunk.file_id, chunk.chunk_index): chunk
                    for chunk in pending_chunk_rows
                }
                rows = []
                for result in embedding_results:
                    chunk = chunk_map.get(
                        (result.file_id, result.chunk_index),
                    )
                    if chunk is None:
                        raise RuntimeError(
                            "Could not match embedding result to persisted "
                            f"chunk: file_id={result.file_id}, "
                            f"chunk_index={result.chunk_index}"
                        )
                    rows.append((
                        chunk.id,
                        result.model,
                        result.dimensions,
                        list(result.vector),
                    ))

                stage_started = perf_counter()
                batch_size = self.embedding_service.batch_size
                for start in range(0, len(rows), batch_size):
                    vector_store_service.store_embeddings(
                        rows[start:start + batch_size],
                    )
                vector_store_elapsed_ms += (
                    perf_counter() - stage_started
                ) * 1000
                pending_chunks.clear()
                pending_chunk_rows.clear()

            for index, repo_file in enumerate(
                persisted_files,
                start=1,
            ):
                if index == 1 or index % INDEX_PROGRESS_COMMIT_FILES == 0:
                    logger.info(
                        "Indexing repository %s: %s/%s supported files",
                        repository.id,
                        index,
                        len(persisted_files),
                    )

                try:
                    # -------------------------------------------------
                    # Read file content
                    # -------------------------------------------------

                    file_path = Path(repo_file.path)

                    if not file_path.exists():
                        print(
                            f"File does not exist: "
                            f"{repo_file.relative_path}"
                        )
                    else:
                        content = file_path.read_bytes()
                        file_content = FileContent(
                            repository_file=repo_file,
                            content=content,
                        )

                        stage_started = perf_counter()
                        parsed_document = self.parser_service.parse(
                            file_content,
                        )
                        parse_elapsed_ms += (
                            perf_counter() - stage_started
                        ) * 1000

                        if (
                            repo_file.support_tier
                            == LanguageSupportTier.TIER_1
                        ):
                            db_symbols = SymbolConverter.convert_all(
                                symbols=parsed_document.symbols,
                                repository_id=repository.id,
                                file_id=repo_file.id,
                            )
                            if db_symbols:
                                repository_symbol_crud.create_many(
                                    db=db,
                                    symbols=db_symbols,
                                    commit=False,
                                )

                        stage_started = perf_counter()
                        chunks = self.chunking_service.chunk(
                            parsed_document,
                            support_tier=repo_file.support_tier,
                        )
                        chunk_elapsed_ms += (
                            perf_counter() - stage_started
                        ) * 1000
                        persisted_chunks = chunk_crud.create_many(
                            db=db,
                            chunks=chunks,
                            commit=False,
                        )
                        pending_chunks.extend(chunks)
                        pending_chunk_rows.extend(persisted_chunks)

                    should_commit = (
                        len(pending_chunks) >= self.embedding_service.batch_size
                        or index % INDEX_PROGRESS_COMMIT_FILES == 0
                        or index == len(persisted_files)
                    )
                    if should_commit:
                        persist_embedding_batch()
                        repository.indexing_processed_files = index
                        repository.indexing_total_files = len(persisted_files)
                        repository.indexing_progress = 10 + int(
                            85 * index / max(len(persisted_files), 1)
                        )
                        repository.indexing_stage = "indexing files"
                        stage_started = perf_counter()
                        db.commit()
                        commit_elapsed_ms += (
                            perf_counter() - stage_started
                        ) * 1000

                except Exception as e:
                    # Roll back the failed file transaction so the
                    # session can continue processing subsequent files.
                    db.rollback()

                    print(
                        f"Error indexing "
                        f"{repo_file.relative_path}: {e}"
                    )
                    raise

            # -----------------------------------------------------
            # Framework detection
            # -----------------------------------------------------

            print(
                "[PARSING / CHUNKING / EMBEDDING COMPLETE] "
                "Moving to framework detection"
            )

            repository.indexing_stage = "framework detection"
            repository.indexing_progress = 96
            db.commit()
            stage_started = perf_counter()
            framework_result = framework_detection_service.detect(
                clone_path,
            )
            framework_elapsed_ms = (perf_counter() - stage_started) * 1000

            # -----------------------------------------------------
            # Calculate repository metadata
            # -----------------------------------------------------

            stage_started = perf_counter()
            metadata = metadata_service.calculate(
                all_repository_files,
            )
            metadata_elapsed_ms = (perf_counter() - stage_started) * 1000

            # -----------------------------------------------------
            # Final repository update
            # -----------------------------------------------------

            print(
                "[INDEXING COMPLETE] "
                "Updating repository to INDEXED"
            )

            repository = repository_crud.update(
                db=db,
                repository=repository,
                primary_framework=framework_result.primary_framework,
                status=RepositoryStatus.INDEXED,
                indexing_progress=100,
                indexing_stage="completed",
                indexing_error=None,
                **metadata,
            )

            get_bm25_index_manager().invalidate(repository.id)

            # Graph persistence is a recoverable post-index stage. Its own
            # status/error fields are independent of vector indexing status.
            try:
                build_repository_graph(db, repository.id)
            except Exception:
                logger.exception(
                    "Graph lifecycle failed after indexing: repository_id=%s",
                    repository.id,
                )

            logger.info(
                "[INDEX TIMING] "
                f"clone_ms={clone_elapsed_ms:.1f} "
                f"pipeline_setup_ms={pipeline_setup_elapsed_ms:.1f} "
                f"scan_ms={scan_elapsed_ms:.1f} "
                f"file_persistence_ms={file_persistence_elapsed_ms:.1f} "
                f"parse_ms={parse_elapsed_ms:.1f} "
                f"chunk_ms={chunk_elapsed_ms:.1f} "
                f"embedding_ms={embedding_elapsed_ms:.1f} "
                f"vector_store_ms={vector_store_elapsed_ms:.1f} "
                f"commit_ms={commit_elapsed_ms:.1f} "
                f"framework_ms={framework_elapsed_ms:.1f} "
                f"metadata_ms={metadata_elapsed_ms:.1f} "
                f"total_ms={(perf_counter() - indexing_started) * 1000:.1f}"
            )

            embedding_profile = self.embedding_service.profile_snapshot()
            provider_profile = embedding_profile.get("provider", {})
            logger.info(
                "[EMBED PROFILE] "
                "chunks=%s cache_hits=%s cache_misses=%s "
                "cache_lookup_ms=%.1f provider_wall_ms=%.1f "
                "tokenize_ms=%.1f model_forward_ms=%.1f "
                "encode_ms=%.1f tensor_to_list_ms=%.1f "
                "service_overhead_ms=%.1f batches=%s mean_batch_size=%.1f "
                "token_positions=%s embeddings_per_second=%.2f device=%s",
                embedding_profile["chunks"],
                embedding_profile["cache_hits"],
                embedding_profile["cache_misses"],
                embedding_profile["cache_lookup_ms"],
                embedding_profile["provider_wall_ms"],
                provider_profile.get("tokenize_ms", 0.0),
                provider_profile.get("model_forward_ms", 0.0),
                provider_profile.get("encode_ms", 0.0),
                provider_profile.get("tensor_to_list_ms", 0.0),
                embedding_profile["service_overhead_ms"],
                provider_profile.get("model_batches", 0),
                provider_profile.get("mean_batch_size", 0.0),
                provider_profile.get("token_positions", 0),
                provider_profile.get("embeddings_per_second", 0.0),
                provider_profile.get("device", "unknown"),
            )

            return repository

        except Exception as exc:
            logger.exception("Repository indexing failed")
            db.rollback()
            self._cleanup_failed_indexing(
                db=db,
                repository=repository,
                error=str(exc),
            )

            raise
        finally:
            db.expire_on_commit = original_expire_on_commit

    def list_repositories(
        self,
        db: Session,
        owner_id: int,
    ):
        """
        Return all repositories owned by the user.
        """

        return repository_crud.get_by_owner(
            db=db,
            owner_id=owner_id,
        )

    def get_repository(
        self,
        db: Session,
        repository_id: int,
        owner_id: int,
    ):
        """
        Retrieve a repository owned by the user.
        """

        repository = repository_crud.get(
            db=db,
            repository_id=repository_id,
        )

        if repository is None:
            raise RepositoryNotFoundError(
                "Repository not found."
            )

        if repository.owner_id != owner_id:
            raise RepositoryNotFoundError(
                "Repository not found."
            )

        return repository

    def delete_repository(
        self,
        db: Session,
        repository_id: int,
        owner_id: int,
    ) -> None:
        """
        Delete a repository and all associated resources.
        """

        repository = self.get_repository(
            db=db,
            repository_id=repository_id,
            owner_id=owner_id,
        )

        get_bm25_index_manager().invalidate(repository.id)


        # Delete indexed files.
        #
        # The database FK cascade handles:
        #
        # RepositoryFile
        #      ↓
        # Chunk
        #      ↓
        # Embedding
        #
        repository_file_crud.delete_by_repository(
            db=db,
            repository_id=repository.id,
        )

        # Delete cloned repository.
        try:
            if repository.clone_path:
                clone_path = Path(repository.clone_path)

                if clone_path.exists():
                    remove_clone_directory(clone_path)
        except OSError:
            logger.warning(
                "Could not remove clone for repository %s",
                repository.id,
                exc_info=True,
            )

        # Delete repository.
        repository_crud.delete(
            db=db,
            repository=repository,
        )

    def list_repository_files(
        self,
        db: Session,
        repository_id: int,
        owner_id: int,
    ):
        """
        Return all indexed files for a repository.
        """

        repository = self.get_repository(
            db=db,
            repository_id=repository_id,
            owner_id=owner_id,
        )

        return repository_file_crud.get_by_repository(
            db=db,
            repository_id=repository.id,
        )

    def _cleanup_failed_indexing(
        self,
        db: Session,
        repository: Repository,
        error: str,
    ) -> None:
        """
        Clean up all resources created during a failed indexing operation.
        """
        get_bm25_index_manager().invalidate(repository.id)

        # Delete symbols.
        repository_symbol_crud.delete_by_repository(
            db=db,
            repository_id=repository.id,
        )

        # Delete indexed files.
        #
        # FK cascades remove associated chunks and embeddings.
        repository_file_crud.delete_by_repository(
            db=db,
            repository_id=repository.id,
        )

        # Delete cloned repository.
        try:
            if repository.clone_path:
                clone_path = Path(repository.clone_path)

                if clone_path.exists():
                    remove_clone_directory(clone_path)
        except OSError:
            logger.warning(
                "Could not remove failed clone for repository %s",
                repository.id,
                exc_info=True,
            )

        # Keep the job record so clients can poll persistent failure state and
        # retry the same repository URL.
        repository = repository_crud.get(
            db=db,
            repository_id=repository.id,
        )
        if repository is not None:
            repository_crud.update(
                db=db,
                repository=repository,
                status=RepositoryStatus.FAILED,
                indexing_stage="failed",
                indexing_error=error[:2000],
            )


@lru_cache(maxsize=1)
def get_repository_service() -> RepositoryService:
    """Create the indexing pipeline only when a repository operation needs it.

    Importing API routes or unit tests must not eagerly initialize chunkers,
    tokenizers, or embedding providers (some of which load local assets).
    """
    return RepositoryService()
