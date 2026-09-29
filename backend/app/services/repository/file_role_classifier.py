from pathlib import PurePath

from app.models.repository_file import FileCategory, FileRole


class FileRoleClassifier:
    """Classify repository files into retrieval-oriented roles."""

    TEST_DIRECTORIES = {
        "test",
        "tests",
        "__tests__",
    }

    FIXTURE_DIRECTORIES = {
        "fixture",
        "fixtures",
    }

    def classify(
        self,
        *,
        relative_path: str,
        filename: str,
        category: FileCategory,
    ) -> FileRole:
        """Return the retrieval role for a repository file."""

        normalized_path = relative_path.replace("\\", "/").lower()
        normalized_filename = filename.lower()

        path_parts = PurePath(normalized_path).parts

        # Fixtures must be checked before tests because fixtures
        # commonly live inside test directories.
        if any(
            part in self.FIXTURE_DIRECTORIES
            for part in path_parts
        ):
            return FileRole.FIXTURE

        # Conventional test directories.
        if any(
            part in self.TEST_DIRECTORIES
            for part in path_parts
        ):
            return FileRole.TEST

        # Conventional test filenames.
        if (
            normalized_filename.startswith("test_")
            or normalized_filename.endswith("_test.py")
            or ".test." in normalized_filename
            or ".spec." in normalized_filename
            or normalized_filename.endswith("test.java")
        ):
            return FileRole.TEST

                # Conventional configuration filenames.
        if (
            normalized_filename.endswith("_config.py")
            or normalized_filename.endswith(".config.py")
        ):
            return FileRole.CONFIG

        # Preserve the existing broad repository classification.
        if category == FileCategory.CONFIGURATION:
            return FileRole.CONFIG

        if category == FileCategory.DOCUMENTATION:
            return FileRole.DOCUMENTATION

        if category == FileCategory.SOURCE:
            return FileRole.SOURCE

        return FileRole.UNKNOWN