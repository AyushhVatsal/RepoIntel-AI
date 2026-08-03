from __future__ import annotations

import json
from pathlib import Path

from app.schemas.framework_detection import (
    FrameworkDetectionResult,
)

from app.services.repository.constants import (
    FRAMEWORK_DETECTION_RULES,
    LANGUAGE_MANIFEST_FILES,
)


class FrameworkDetectionService:
    """
    Detect the primary framework used by a repository.
    """

    def detect(
        self,
        repository_path: Path,
    ) -> FrameworkDetectionResult:

        framework_counts = self._detect_frameworks(
            repository_path,
        )

        fallback_language = self._detect_language(
            repository_path,
        )

        return self._resolve_frameworks(
            framework_counts=framework_counts,
            fallback_language=fallback_language,
        )

    def _detect_frameworks(
        self,
        repository_path: Path,
    ) -> dict[str, int]:
        framework_counts: dict[str, int] = {}

        for rules in FRAMEWORK_DETECTION_RULES.values():

            # Handle Node.js projects separately
            if rules.get("package_json"):

                self._detect_node_frameworks(
                    repository_path=repository_path,
                    frameworks=rules["frameworks"],
                    framework_counts=framework_counts,
                )

                continue

            manifests = rules.get(
                "manifests",
                [],
            )

            frameworks = rules.get(
                "frameworks",
                {},
            )

            for manifest in manifests:

                # Support wildcard manifests (*.csproj)
                if "*" in manifest:

                    manifest_paths = repository_path.rglob(
                        manifest,
                    )

                else:

                    manifest_path = repository_path / manifest

                    manifest_paths = (
                        [manifest_path]
                        if manifest_path.exists()
                        else []
                    )

                for path in manifest_paths:

                    content = self._read_file(
                        path,
                    )

                    if not content:
                        continue

                    self._count_frameworks(
                        content=content,
                        frameworks=frameworks,
                        framework_counts=framework_counts,
                    )

        return framework_counts

    def _detect_node_frameworks(
        self,
        repository_path: Path,
        frameworks: dict[str, str],
        framework_counts: dict[str, int],
    ) -> None:
        package_json = repository_path / "package.json"

        if not package_json.exists():
            return

        try:
            data = json.loads(
                package_json.read_text(
                    encoding="utf-8",
                )
            )

        except json.JSONDecodeError:
            return

        dependencies = {
            **data.get("dependencies", {}),
            **data.get("devDependencies", {}),
        }

        for dependency, framework in frameworks.items():

            if dependency in dependencies:

                framework_counts[framework] = (
                    framework_counts.get(
                        framework,
                        0,
                    )
                    + 1
                )

    def _detect_language(
        self,
        repository_path: Path,
    ) -> str | None:
        for language, manifests in LANGUAGE_MANIFEST_FILES.items():

            for manifest in manifests:

                # Support wildcard manifests (*.csproj)
                if "*" in manifest:

                    if any(repository_path.rglob(manifest)):
                        return language

                elif (repository_path / manifest).exists():

                    return language

        return None

    @staticmethod
    def _read_file(
        path: Path,
    ) -> str:
        """
        Safely read a manifest file.

        Returns an empty string if the file does not exist
        or cannot be decoded.
        """

        if not path.exists():
            return ""

        return path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

    @staticmethod
    def _count_frameworks(
        content: str,
        frameworks: dict[str, str],
        framework_counts: dict[str, int],
    ) -> None:

        content = content.lower()

        for dependency, framework in frameworks.items():

            occurrences = content.count(
                dependency.lower()
            )

            if occurrences:

                framework_counts[framework] = (
                    framework_counts.get(
                        framework,
                        0,
                    )
                    + occurrences
                )

    @staticmethod
    def _resolve_frameworks(
        framework_counts: dict[str, int],
        fallback_language: str | None,
    ) -> FrameworkDetectionResult:
        """
        Resolve the final framework detection result.
        """

        if not framework_counts:
            return FrameworkDetectionResult(
                primary_framework=fallback_language,
            )

        max_count = max(
            framework_counts.values()
        )

        frameworks = sorted(
            framework
            for framework, count in framework_counts.items()
            if count == max_count
        )

        return FrameworkDetectionResult(
            primary_framework=frameworks[0],
            frameworks=frameworks,
        )
        

framework_detection_service = FrameworkDetectionService()