from __future__ import annotations

from statistics import median
from time import perf_counter

from app.services.retrieval.reranking.cross_encoder import (
    CrossEncoderReranker,
)
from app.services.retrieval.result import RetrievalResult


def test_v22_cross_encoder_inference_latency() -> None:
    """Benchmark isolated Cross-Encoder latency for fixed candidate pools."""

    query = (
        "Where is repository deletion handled and how are "
        "associated chunks removed?"
    )

    # Fixed inputs isolate reranking from database and retrieval overhead.
    documents = {
        i: (
            f"Python module {i}: "
            f"repository management, file indexing, chunk processing, "
            f"database operations, and retrieval implementation. "
            f"Function process_item_{i} handles this module's operations."
        )
        for i in range(1, 21)
    }

    results = [
        RetrievalResult(
            chunk_id=i,
            score=1.0 / i,
            retrieval_score=1.0 / i,
        )
        for i in range(1, 21)
    ]

    pool_sizes = (5, 10, 20)
    measured_runs = 5

    # Model initialization is deliberately outside the timed sections.
    reranker = CrossEncoderReranker()

    def measure_once(pool_size: int) -> float:
        candidates = results[:pool_size]

        start = perf_counter()

        reranker.rerank(
            query=query,
            results=candidates,
            documents=documents,
            top_k=pool_size,
        )

        return (perf_counter() - start) * 1000.0

    # Warm up each candidate count before recording measurements.
    for pool_size in pool_sizes:
        measure_once(pool_size)

    timings: dict[int, list[float]] = {
        pool_size: [] for pool_size in pool_sizes
    }

    # Alternate measurement order to reduce order-related timing bias.
    for run_index in range(measured_runs):
        ordered_sizes = (
            pool_sizes
            if run_index % 2 == 0
            else tuple(reversed(pool_sizes))
        )

        for pool_size in ordered_sizes:
            elapsed_ms = measure_once(pool_size)
            timings[pool_size].append(elapsed_ms)

    print("\n=== Isolated Cross-Encoder Latency ===")
    print(f"Model: cross-encoder/ms-marco-MiniLM-L-6-v2")
    print(f"Measured runs per pool: {measured_runs}")
    print(
        f"{'Pool':>5} "
        f"{'Median ms':>12} "
        f"{'Min ms':>12} "
        f"{'Max ms':>12} "
        f"{'Spread ms':>12}"
    )

    for pool_size in pool_sizes:
        samples = timings[pool_size]

        median_ms = median(samples)
        min_ms = min(samples)
        max_ms = max(samples)

        print(
            f"{pool_size:>5} "
            f"{median_ms:>12.2f} "
            f"{min_ms:>12.2f} "
            f"{max_ms:>12.2f} "
            f"{max_ms - min_ms:>12.2f}"
        )

        assert len(samples) == measured_runs
        assert all(value > 0 for value in samples)