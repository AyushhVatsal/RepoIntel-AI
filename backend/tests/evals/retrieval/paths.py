"""Path normalization helpers for retrieval evaluation."""

import posixpath
import re

_DRIVE = re.compile(r"^[A-Za-z]:")
_UNC = re.compile(r"^(?:\\\\|//)")


def normalize_path(path: str) -> str:
    """Normalize a repository-relative path to canonical POSIX form.

    Preserve case and reject paths that appear absolute or escape
    the repository root.
    """
    if not isinstance(path, str):
        raise ValueError(f"invalid repo-relative path: {path!r}")

    cleaned = path.strip().replace("\\", "/")

    if not cleaned or _DRIVE.match(cleaned) or _UNC.match(cleaned):
        raise ValueError(f"invalid repo-relative path: {path!r}")

    normalized = posixpath.normpath(cleaned).lstrip("/")

    if (
        normalized in ("", ".")
        or normalized == ".."
        or normalized.startswith("../")
    ):
        raise ValueError(f"invalid repo-relative path: {path!r}")

    return normalized


def deduplicate_paths(paths: tuple[str, ...]) -> tuple[str, ...]:
    """Deduplicate paths while preserving their first-occurrence order."""
    unique_paths: list[str] = []
    seen: set[str] = set()

    for path in paths:
        normalized = normalize_path(path)
        if normalized not in seen:
            seen.add(normalized)
            unique_paths.append(normalized)

    return tuple(unique_paths)