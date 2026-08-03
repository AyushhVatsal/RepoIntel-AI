from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from app.models.repository_file import (
    FileCategory,
    LanguageSupportTier,
)

from app.services.repository.constants import (
    CATEGORY_EXTENSION_MAP,
    EXTENSION_LANGUAGE_MAP,
    EXTENSION_TIER_MAP,
    IGNORED_DIRECTORIES,
    IGNORED_FILES,
    MAX_FILE_SIZE_BYTES,
    MAX_REPOSITORY_SIZE_BYTES,
    MAX_REPOSITORY_SIZE_MB,
    SPECIAL_TEXT_FILENAMES
)

from app.schemas.repository_file import RepositoryFileCreate
from app.exceptions.repository import (
    RepositoryScanError,
    RepositoryTooLargeError,
)


class ScannerService:
    """
    Scans a repository and discovers all files that should be processed.

    Responsibilities
    ----------------
    - Walk the repository recursively
    - Ignore excluded directories
    - Ignore excluded files

    This service DOES NOT:
    - Parse code
    - Detect frameworks
    - Generate embeddings
    - Save to the database
    """

    def scan(
        self,
        repository_id: int,
        repository_path: Path,
    ) -> list[RepositoryFileCreate]:
        """
        Scan a repository and build metadata for all supported files.
        """

        self._validate_repository_size(repository_path)

        repository_files: list[RepositoryFileCreate] = []

        try:
            for path in repository_path.rglob("*"):

                if not path.is_file():
                    continue

                if self._should_ignore(path):
                    continue

                # Skip files larger than the configured limit
                if (
                    self._get_file_size(path)
                    > MAX_FILE_SIZE_BYTES
                ):
                    continue

                repository_files.append(
                    self._build_repository_file(
                        repository_id=repository_id,
                        repository_root=repository_path,
                        file_path=path,
                    )
                )

            return repository_files

        except RepositoryTooLargeError:
            raise

        except Exception as exc:
            raise RepositoryScanError(
                "Failed to scan repository."
            ) from exc

    def _should_ignore(self, path: Path) -> bool:
        """
        Determine whether a file should be ignored.
        """

        # Ignore excluded directories
        if any(
            directory in IGNORED_DIRECTORIES
            for directory in path.parts
        ):
            return True

        # Ignore excluded filenames
        if path.name in IGNORED_FILES:
            return True

        return False

    def _get_category(
        self,
        path: Path,
    ) -> FileCategory:

        extension = path.suffix.lower()

        for category, extensions in CATEGORY_EXTENSION_MAP.items():
            if extension in extensions:
                return category

        if path.name in SPECIAL_TEXT_FILENAMES:
            return FileCategory.CONFIGURATION

        return FileCategory.IGNORED

    def _get_language(
        self,
        path: Path,
    ) -> str | None:
        return EXTENSION_LANGUAGE_MAP.get(
            path.suffix.lower()
        )

    def _get_support_tier(
        self,
        path: Path,
    ) -> LanguageSupportTier:
        return EXTENSION_TIER_MAP.get(
            path.suffix.lower(),
            LanguageSupportTier.NONE,
        )

    def _calculate_sha256(
        self,
        path: Path,
    ) -> str:
        """
        Calculate the SHA256 hash of a file.
        """

        sha256 = hashlib.sha256()

        with path.open("rb") as file:
            while chunk := file.read(8192):
                sha256.update(chunk)

        return sha256.hexdigest()

    def _get_file_size(
        self,
        path: Path,
    ) -> int:
        return path.stat().st_size

    def _get_last_modified(
        self,
        path: Path,
    ) -> datetime:
        return datetime.fromtimestamp(
            path.stat().st_mtime
        )

    def _build_repository_file(
        self,
        repository_id: int,
        repository_root: Path,
        file_path: Path,
    ) -> RepositoryFileCreate:
        """
        Build a RepositoryFileCreate object from a physical file.
        """

        category = self._get_category(file_path)

        language = self._get_language(file_path)
        support_tier = self._get_support_tier(file_path)
        size = self._get_file_size(file_path)
        last_modified = self._get_last_modified(file_path)
        sha256_hash = self._calculate_sha256(file_path)

        return RepositoryFileCreate(
            repository_id=repository_id,
            path=str(file_path.resolve()),
            relative_path=str(file_path.relative_to(repository_root)),
            filename=file_path.name,
            extension=file_path.suffix.lower() or None,
            language=language,
            category=category,
            support_tier=support_tier,
            size=size,
            sha256_hash=sha256_hash,
            is_binary=category == FileCategory.BINARY,
            last_modified=last_modified,
        )
    
    def _validate_repository_size(
        self,
        repository_path: Path,
    ) -> None:

        total_size = sum(
            file.stat().st_size
            for file in repository_path.rglob("*")
            if file.is_file()
        )

        if total_size > MAX_REPOSITORY_SIZE_BYTES:
            raise RepositoryTooLargeError(
                f"Repository size exceeds the maximum allowed limit of "
                f"{MAX_REPOSITORY_SIZE_MB} MB."
            )
        
scanner_service = ScannerService()