from __future__ import annotations

import time

from app.services.embedding.providers.local import LocalEmbeddingProvider


MODEL_NAME = "BAAI/bge-small-en-v1.5"


def main() -> None:
    print("Loading model...")

    start = time.perf_counter()
    provider = LocalEmbeddingProvider(MODEL_NAME)
    load_time = time.perf_counter() - start

    print(f"Model load time: {load_time:.2f}s")
    print(f"Model: {provider.model}")
    print(f"Dimensions: {provider.dimensions}")

    text = (
        "This is a repository code chunk containing "
        "authentication and user management logic."
    )

    print("\nWarming up...")
    provider.embed([text] * 4)

    print("\nBenchmark:")

    for batch_size in [1, 8, 16, 32, 64, 128]:
        texts = [text] * batch_size

        start = time.perf_counter()
        embeddings = provider.embed(texts)
        elapsed = time.perf_counter() - start

        throughput = batch_size / elapsed

        print(
            f"batch={batch_size:>3} | "
            f"time={elapsed:.3f}s | "
            f"chunks/sec={throughput:.2f} | "
            f"vectors={len(embeddings)}"
        )


if __name__ == "__main__":
    main()