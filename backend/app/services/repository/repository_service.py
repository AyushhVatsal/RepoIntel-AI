from __future__ import annotations

import shutil
from pathlib import Path

from sqlalchemy.orm import Session

from app.crud.chunk import chunk_crud
from app.crud.repository import repository_crud
from app.crud.repository_file import repository_file_crud
from app.crud.repository_symbol import repository_symbol_crud
from app.exceptions.repository import (
    RepositoryAlreadyExistsError,
    RepositoryNotFoundError,
)
from app.models.repository import RepositoryStatus
from app.models.repository_file import LanguageSupportTier
from app.schemas.repository import RepositoryCreate
from app.services.chunking.service import ChunkingService
from app.services.embedding.models.embedding_config import EmbeddingConfig
from app.services.embedding.providers.local import LocalEmbeddingProvider
from app.services.embedding.service import EmbeddingService
from app.services.parsers.models.file_content import FileContent
from app.services.parsers.parser_service import ParserService
from app.services.parsers.symbol_converter import SymbolConverter
from app.services.repository.clone_service import clone_service
from app.services.repository.framework_detector import (
    framework_detection_service,
)
from app.services.repository.metadata_service import metadata_service
from app.services.repository.scanner_service import scanner_service
from app.services.vector_store.service import VectorStoreService


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

        self.parser_service = parser_service or ParserService()
        self.chunking_service = chunking_service or ChunkingService()

        if embedding_service is None:
            embedding_config = EmbeddingConfig()
            embedding_provider = LocalEmbeddingProvider(
                model_name=embedding_config.model,
            )
            embedding_service = EmbeddingService(
                provider=embedding_provider,
                config=embedding_config,
            )

        self.embedding_service = embedding_service

    def index_repository(
        self,
        db: Session,
        owner_id: int,
        repository_in: RepositoryCreate,
    ):
        """
        Clone, scan, parse, chunk, embed and index a repository.
        """

        # ---------------------------------------------------------
        # Check for duplicate repository
        # ---------------------------------------------------------

        existing_repository = repository_crud.get_by_github_url(
            db=db,
            github_url=str(repository_in.github_url),
            owner_id=owner_id,
        )

        if existing_repository is not None:
            raise RepositoryAlreadyExistsError(
                "Repository has already been indexed."
            )

        # ---------------------------------------------------------
        # Create initial repository record
        # ---------------------------------------------------------

        repository = repository_crud.create(
            db=db,
            repository_in=repository_in,
            owner_id=owner_id,
            status=RepositoryStatus.PENDING,
            name="",
            clone_path="",
        )

        try:
            # -----------------------------------------------------
            # Clone repository
            # -----------------------------------------------------

            repository_crud.update(
                db=db,
                repository=repository,
                status=RepositoryStatus.CLONING,
            )

            clone_path = clone_service.clone(
                repository_in.github_url,
                str(repository.id),
            )

            repository_name = clone_service.get_repository_name(
                repository_in.github_url,
            )

            default_branch = clone_service.get_default_branch(
                clone_path,
            )

            repository_crud.update(
                db=db,
                repository=repository,
                name=repository_name,
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
            )

            all_repository_files = scanner_service.scan(
                repository_id=repository.id,
                repository_path=clone_path,
            )

            supported_repository_files = [
                repository_file
                for repository_file in all_repository_files
                if repository_file.support_tier != LanguageSupportTier.NONE
            ]

            # -----------------------------------------------------
            # Persist supported files
            # -----------------------------------------------------

            persisted_files = repository_file_crud.create_many(
                db=db,
                files=supported_repository_files,
            )

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
            )

            for index, repo_file in enumerate(
                persisted_files,
                start=1,
            ):
                print(
                    f"[PARSING {index}/{len(persisted_files)}] "
                    f"{repo_file.relative_path}"
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
                        continue

                    content = file_path.read_bytes()

                    # -------------------------------------------------
                    # Create parser input
                    # -------------------------------------------------

                    file_content = FileContent(
                        repository_file=repo_file,
                        content=content,
                    )

                    # -------------------------------------------------
                    # Parse file
                    #
                    # ParserService selects:
                    # Tier 1 -> Tree-sitter
                    # Tier 0 -> Generic parser
                    # -------------------------------------------------

                    parsed_document = self.parser_service.parse(
                        file_content,
                    )

                    # -------------------------------------------------
                    # Persist symbols for Tier 1 files
                    # -------------------------------------------------

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
                            )

                    # -------------------------------------------------
                    # Generate code-aware chunks
                    # -------------------------------------------------

                    chunks = self.chunking_service.chunk(
                        parsed_document,
                        support_tier=repo_file.support_tier,
                    )

                    if not chunks:
                        print(
                            f"[NO CHUNKS] "
                            f"{repo_file.relative_path}"
                        )
                        continue

                    # -------------------------------------------------
                    # Persist chunks
                    # -------------------------------------------------

                    persisted_chunks = chunk_crud.create_many(
                        db=db,
                        chunks=chunks,
                    )

                    print(
                        f"[CHUNKS] "
                        f"{repo_file.relative_path} "
                        f"count={len(persisted_chunks)}"
                    )

                    # -------------------------------------------------
                    # Generate embeddings
                    # -------------------------------------------------

                    embedding_results = self.embedding_service.embed(
                        chunks,
                    )

                    if len(embedding_results) != len(
                        persisted_chunks
                    ):
                        raise RuntimeError(
                            "Embedding result count does not match "
                            "persisted chunk count."
                        )

                    # -------------------------------------------------
                    # Map persisted chunks by file/chunk index
                    # -------------------------------------------------

                    chunk_map = {
                        (
                            chunk.file_id,
                            chunk.chunk_index,
                        ): chunk
                        for chunk in persisted_chunks
                    }

                    # -------------------------------------------------
                    # Persist embeddings in vector storage
                    # -------------------------------------------------

                    vector_store_service = VectorStoreService(
                        db=db,
                    )

                    for embedding_result in embedding_results:
                        chunk = chunk_map.get(
                            (
                                embedding_result.file_id,
                                embedding_result.chunk_index,
                            )
                        )

                        if chunk is None:
                            raise RuntimeError(
                                "Could not match embedding result "
                                f"to persisted chunk: "
                                f"file_id="
                                f"{embedding_result.file_id}, "
                                f"chunk_index="
                                f"{embedding_result.chunk_index}"
                            )

                        vector_store_service.store_embedding(
                            chunk_id=chunk.id,
                            model=embedding_result.model,
                            dimensions=embedding_result.dimensions,
                            embedding=embedding_result.vector,
                        )

                    # -------------------------------------------------
                    # Commit embeddings for this file
                    # -------------------------------------------------

                    db.commit()

                    print(
                        f"[EMBEDDED] "
                        f"{repo_file.relative_path} "
                        f"count={len(embedding_results)}"
                    )

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

            framework_result = framework_detection_service.detect(
                clone_path,
            )

            # -----------------------------------------------------
            # Calculate repository metadata
            # -----------------------------------------------------

            metadata = metadata_service.calculate(
                all_repository_files,
            )

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
                **metadata,
            )

            return repository

        except Exception as e:
            import traceback

            print(f"INDEXING FAILED: {e}")
            traceback.print_exc()

            self._cleanup_failed_indexing(
                db=db,
                repository=repository,
            )

            raise

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
                    shutil.rmtree(
                        clone_path,
                        ignore_errors=True,
                    )
        except Exception:
            pass

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
        repository,
    ) -> None:
        """
        Clean up all resources created during a failed indexing operation.
        """

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
                    shutil.rmtree(
                        clone_path,
                        ignore_errors=True,
                    )
        except Exception:
            pass

        # Delete repository record.
        repository_crud.delete(
            db=db,
            repository=repository,
        )


repository_service = RepositoryService()