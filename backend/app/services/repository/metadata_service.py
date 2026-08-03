from __future__ import annotations

from collections import Counter

from app.models.repository_file import (
    LanguageSupportTier,
)
from app.schemas.repository_file import RepositoryFileCreate


class MetadataService:
    """
    Calculates repository-level metadata from scanned files.
    """

    def calculate(
        self,
        files: list[RepositoryFileCreate],
    ) -> dict:
        """
        Calculate repository metadata.
        """

        supported_files = [
            file
            for file in files
            if file.support_tier != LanguageSupportTier.NONE
        ]

        language_counter = Counter(
            file.language
            for file in supported_files
            if file.language
        )

        primary_language = None

        if language_counter:
            primary_language = language_counter.most_common(1)[0][0]

        return {
            "primary_language": primary_language,
            "total_files": len(files),
            "supported_files": len(supported_files),
            "skipped_files": len(files) - len(supported_files),
            "repository_size": sum(
                file.size
                for file in files
            ),
        }


metadata_service = MetadataService()