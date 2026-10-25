import pytest

from tests.evals.retrieval.paths import (
    deduplicate_paths,
    normalize_path,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            r"backend\app\crud\embedding.py",
            "backend/app/crud/embedding.py",
        ),
        (
            "backend/app/crud/embedding.py",
            "backend/app/crud/embedding.py",
        ),
        (
            "./backend/app//crud/embedding.py",
            "backend/app/crud/embedding.py",
        ),
        (
            "  backend/app/crud/embedding.py ",
            "backend/app/crud/embedding.py",
        ),
        (
            "/backend/app/crud/embedding.py",
            "backend/app/crud/embedding.py",
        ),
    ],
)
def test_normalize_path(raw: str, expected: str) -> None:
    assert normalize_path(raw) == expected


def test_preserves_case() -> None:
    assert normalize_path("Backend/App.py") != normalize_path(
        "backend/app.py"
    )


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "   ",
        ".",
        "..",
        "../x.py",
        r"C:\x\y.py",
        r"\\server\share\file.py",
        "//server/share/file.py",
    ],
)
def test_rejects_invalid_paths(bad: str) -> None:
    with pytest.raises(ValueError):
        normalize_path(bad)


def test_deduplicate_paths_preserves_order() -> None:
    paths = (
        r"backend\app\crud\embedding.py",
        "backend/app/crud/embedding.py",
        "backend/app/api/health.py",
    )

    assert deduplicate_paths(paths) == (
        "backend/app/crud/embedding.py",
        "backend/app/api/health.py",
    )