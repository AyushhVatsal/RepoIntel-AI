from pathlib import Path

from app.services.repository.scanner_service import ScannerService


def test_scan_prunes_ignored_directories(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    (repository / "src").mkdir(parents=True)
    (repository / ".git" / "objects").mkdir(parents=True)
    (repository / "node_modules" / "dependency").mkdir(parents=True)

    (repository / "src" / "app.py").write_text(
        "def run():\n    return True\n",
        encoding="utf-8",
    )
    (repository / ".git" / "objects" / "ignored.py").write_text(
        "must not be indexed",
        encoding="utf-8",
    )
    (repository / "node_modules" / "dependency" / "ignored.js").write_text(
        "must not be indexed",
        encoding="utf-8",
    )

    files = ScannerService().scan(
        repository_id=1,
        repository_path=repository,
    )

    assert {file.relative_path.replace("\\", "/") for file in files} == {
        "src/app.py",
    }
