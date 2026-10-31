# Retrieval V2 initial baseline

Run against repository 49 (`RepoIntel-AI`) with TEST and FIXTURE roles excluded. The suite contains 50 answerable queries and 8 no-answer queries. These are single-run measurements on the local environment; treat them as a starting point, not frozen quality floors or production latency guarantees.

## Positive query quality

| Layer | Hit@1 | Hit@3 | Hit@5 | Recall@5 | Precision@5 | MRR@5 | nDCG@5 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Dense only | .560 | .900 | .940 | .903 | .268 | .717 | .733 |
| BM25 only | .420 | .720 | .820 | .710 | .196 | .568 | .568 |
| Hybrid RRF only | .500 | .840 | .940 | .850 | .240 | .687 | .685 |
| Cross-encoder reranking | .520 | .820 | .900 | .847 | .248 | .679 | .687 |
| Weighted RRF + cross-encoder | .540 | .860 | .940 | .850 | .240 | .710 | .695 |
| Production hybrid | .540 | .880 | .940 | .850 | .240 | .717 | .701 |
| Graph enhanced | .540 | .800 | .920 | .823 | .232 | .690 | .674 |

## Query-level latency

Median / p95 milliseconds per case. Model construction is excluded; query embedding, retrieval, and result hydration are included. The BM25 eval runner hydrates result paths in one query. Its first call includes index creation; its warm-only values should be read separately.

| Layer | p50 / p95 |
|---|---:|
| Dense only | 21.0 / 43.9 ms |
| BM25 only, warm queries | 1.1 / 1.6 ms |
| Hybrid RRF only | 18.3 / 25.3 ms |
| Cross-encoder reranking | 547.7 / 3,387.1 ms |
| Weighted RRF + cross-encoder | 204.2 / 235.0 ms |
| Production hybrid | 57.9 / 242.4 ms |
| Graph enhanced | 69.9 / 262.4 ms |

BM25's first query, including index construction, measured **355 ms** in a separate run. That one-time startup figure is environment-sensitive; warm p50/p95 are more representative of steady-state lookup on this corpus.

## What the categories show

- BM25 exact-identifier Recall@5 was **1.000**, MRR@5 **.806**, its strongest category.
- Dense conceptual Recall@5 was **.950**; BM25 conceptual Recall@5 was **.500**. Dense retrieval carries most natural-language concept matching.
- BM25 path/navigation Recall@5 was **.750**, compared with dense at **.700**.
- Production hybrid matched RRF Recall@5 (**.850**) and improved MRR@5 from **.687** to **.717** on this run.
- Graph-enhanced Recall@5 (**.823**) and nDCG@5 (**.674**) were below production hybrid on this set.
- Every mode returned at least one result for all eight no-answer queries (false-positive rate at 5: **1.000**). The retrieval stack currently has no abstention behavior; this set measures that limitation separately from answerable-query recall.

Run the suite and its per-category breakdown with:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests/evals/retrieval/test_retrieval_v2_all_layers.py -q -s
```
