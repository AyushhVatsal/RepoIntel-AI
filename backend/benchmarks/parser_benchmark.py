from __future__ import annotations

import sys
import time
from pathlib import Path

from datetime import datetime, timezone

from app.models.repository_file import LanguageSupportTier
from app.schemas.repository_file import RepositoryFileResponse
from app.services.parsers.models.file_content import FileContent
from app.services.parsers.tree_sitter.parser import TreeSitterParser
from app.services.repository.scanner_service import scanner_service


# Change these two values for each repository you benchmark.
REPOSITORY_ID = 23
REPOSITORY_PATH = Path("storage/repositories/23")


def main() -> None:
    print("=" * 70)
    print("RepoIntel Parser Benchmark")
    print("=" * 70)
    print(f"Repository ID   : {REPOSITORY_ID}")
    print(f"Repository path : {REPOSITORY_PATH}")
    print()

    if not REPOSITORY_PATH.exists():
        print(f"ERROR: Repository path does not exist: {REPOSITORY_PATH}")
        sys.exit(1)

    # ---------------------------------------------------------
    # Scan using the real scanner
    # ---------------------------------------------------------

    print("Scanning repository...")

    scan_start = time.perf_counter()

    repository_files = scanner_service.scan(
        repository_id=REPOSITORY_ID,
        repository_path=REPOSITORY_PATH,
    )

    scan_time = time.perf_counter() - scan_start

    tier1_files = [
        file
        for file in repository_files
        if file.support_tier == LanguageSupportTier.TIER_1
    ]

    print(f"Total scanned files : {len(repository_files)}")
    print(f"Tier 1 files        : {len(tier1_files)}")
    print(f"Scan time           : {scan_time:.3f}s")
    print()

    # ---------------------------------------------------------
    # Parser benchmark
    # ---------------------------------------------------------

    print("Parsing...")
    print("-" * 70)

    parsed_count = 0
    failed_count = 0
    total_symbols = 0

    timings: list[float] = []
    failures: list[tuple[str, str]] = []
    language_stats: dict[str, dict[str, float | int]] = {}

    benchmark_start = time.perf_counter()

    for index, repo_file in enumerate(tier1_files, start=1):
        file_path = Path(repo_file.path)

        if not file_path.exists():
            failed_count += 1
            failures.append(
                (repo_file.relative_path, "file does not exist")
            )
            continue

        try:
            content = file_path.read_bytes()

            file_data = repo_file.model_dump()

            repository_file = RepositoryFileResponse(
                **file_data,
                id=index,
                created_at=datetime.now(timezone.utc),
            )
            
            file_content = FileContent(
                repository_file=repository_file,
                content=content,
            )

            start = time.perf_counter()

            parsed_document = TreeSitterParser.parse(
                file_content
            )

            elapsed = time.perf_counter() - start

            timings.append(elapsed)

            symbol_count = len(parsed_document.symbols)
            total_symbols += symbol_count
            parsed_count += 1

            language = repo_file.language or "unknown"

            stats = language_stats.setdefault(
                language,
                {
                    "files": 0,
                    "time": 0.0,
                    "symbols": 0,
                },
            )

            stats["files"] += 1
            stats["time"] += elapsed
            stats["symbols"] += symbol_count

        except Exception as exc:
            failed_count += 1
            failures.append(
                (
                    repo_file.relative_path,
                    f"{type(exc).__name__}: {exc}",
                )
            )

        if index % 100 == 0 or index == len(tier1_files):
            print(
                f"Processed {index}/{len(tier1_files)} "
                f"| parsed={parsed_count} "
                f"| failed={failed_count}"
            )

    total_parse_time = time.perf_counter() - benchmark_start

    # ---------------------------------------------------------
    # Statistics
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("Results")
    print("=" * 70)

    print(f"Files attempted : {len(tier1_files)}")
    print(f"Files parsed    : {parsed_count}")
    print(f"Files failed    : {failed_count}")
    print(f"Total time      : {total_parse_time:.3f}s")

    if timings:
        sorted_timings = sorted(timings)

        average = sum(timings) / len(timings)

        middle = len(sorted_timings) // 2

        if len(sorted_timings) % 2:
            median = sorted_timings[middle]
        else:
            median = (
                sorted_timings[middle - 1]
                + sorted_timings[middle]
            ) / 2

        files_per_second = len(timings) / total_parse_time

        print(f"Average/file    : {average * 1000:.3f} ms")
        print(f"Median/file     : {median * 1000:.3f} ms")
        print(f"Files/second    : {files_per_second:.2f}")

    print(f"Symbols extracted: {total_symbols}")

    # ---------------------------------------------------------
    # Language breakdown
    # ---------------------------------------------------------

    print()
    print("Language Breakdown")
    print("-" * 70)

    for language, stats in sorted(language_stats.items()):
        files = int(stats["files"])
        total_time = float(stats["time"])
        symbols = int(stats["symbols"])

        average_ms = (
            (total_time / files) * 1000
            if files
            else 0.0
        )

        print(
            f"{language:<12} "
            f"files={files:<6} "
            f"time={total_time:.3f}s "
            f"avg={average_ms:.3f}ms "
            f"symbols={symbols}"
        )

    # ---------------------------------------------------------
    # Failures
    # ---------------------------------------------------------

    if failures:
        print()
        print("Failures")
        print("-" * 70)

        for path, error in failures[:20]:
            print(f"{path}")
            print(f"  {error}")

        if len(failures) > 20:
            print(
                f"... and {len(failures) - 20} more failures"
            )

    print()
    print("=" * 70)
    print("Benchmark complete")
    print("=" * 70)


if __name__ == "__main__":
    main()