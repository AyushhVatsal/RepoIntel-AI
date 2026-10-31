# Retrieval quality, latency, and Swagger test guide

**Run date:** 2026-10-31
**Target:** local RepoIntel-AI backend, indexed repository ID `49`
**Indexed corpus at evaluation:** 121 files, 847 chunks; 633 source chunks after excluding test and fixture roles.

This report is stored in `reports/retrieval-quality/`, outside the git-ignored `docs/` folder.

## Historical V1 results: pre-PR, post-PR, and current

The V1 comparison uses the same eight queries and database snapshot. All values are percentages.

| Mode | Version | Hit@1 | Hit@3 | Hit@5 | Recall@5 | Precision@5 | MRR@5 | nDCG@5 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Dense | Pre-PR | 75.0 | 100.0 | 100.0 | 95.8 | 30.0 | 83.3 | 83.1 |
| Dense | Post-PR | 75.0 | 100.0 | 100.0 | 95.8 | 30.0 | 83.3 | 83.1 |
| Dense | Current | 75.0 | 100.0 | 100.0 | 95.8 | 30.0 | 83.3 | 83.1 |
| BM25 | Pre-PR | 12.5 | 37.5 | 50.0 | 37.5 | 12.5 | 26.0 | 23.5 |
| BM25 | Post-PR | 12.5 | 37.5 | 50.0 | 37.5 | 12.5 | 26.0 | 23.5 |
| BM25 | Current | 12.5 | 37.5 | 50.0 | 37.5 | 12.5 | 26.0 | 23.5 |
| Hybrid only | Pre-PR | 62.5 | 87.5 | 100.0 | 91.7 | 27.5 | 77.5 | 76.1 |
| Hybrid only | Post-PR | 50.0 | 75.0 | 87.5 | 70.8 | 20.0 | 65.6 | 58.8 |
| Hybrid only | Current | 62.5 | 87.5 | 100.0 | 91.7 | 27.5 | 77.5 | 76.1 |
| V2.2 cross-encoder | Pre-PR | 50.0 | 87.5 | 100.0 | 91.7 | 27.5 | 69.2 | 69.3 |
| V2.2 cross-encoder | Post-PR | 50.0 | 87.5 | 87.5 | 75.0 | 22.5 | 64.6 | 60.5 |
| V2.2 cross-encoder | Current | 50.0 | 87.5 | 100.0 | 91.7 | 27.5 | 69.2 | 69.3 |
| Graph enhanced | Pre-PR | 62.5 | 87.5 | 87.5 | 75.0 | 22.5 | 75.0 | 68.2 |
| Graph enhanced | Post-PR | 50.0 | 87.5 | 87.5 | 64.6 | 17.5 | 66.7 | 56.3 |
| Graph enhanced | Current | 62.5 | 87.5 | 100.0 | 87.5 | 25.0 | 78.1 | 74.1 |

The PR regressed hybrid, cross-encoder, and graph quality on this fixture. The corrective pass restored hybrid and cross-encoder scores to their pre-PR values and improved graph scores over pre-PR.

### V1 stage latency

Average stage timings at `top_k=5`, in milliseconds per query. The pre-PR run includes a substantial cold-start sample; these are directional single-run measurements.

| Stage | Pre-PR | Post-PR, before fixes | Current |
|---|---:|---:|---:|
| Query embedding | 614 | 52 | 48 |
| Hybrid retrieval | 241 | 125 | 66 |
| Initial hydration | 10.1 | 5.6 | 1.8 |
| Cross-encoder | 1,617 | 342 | 337 |
| Weighted fusion | <1 | <1 | <1 |
| Final hydration | 7.3 | 6.2 | 2.4 |
| **Total** | **2,490** | **531** | **456** |

Post-PR to current stage total decreased about **14%**; measured hybrid retrieval stage decreased about **47%**.

## V2 current results across retrieval layers

V2 contains 50 answerable queries: the original eight plus 42 additions across exact identifiers, partial identifiers, conceptual questions, and path/navigation. It also contains eight separate no-answer cases. The same cases were run through every layer. Values are percentages.

| Layer | Hit@1 | Hit@3 | Hit@5 | Recall@5 | Precision@5 | MRR@5 | nDCG@5 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Dense only | 56.0 | 90.0 | 94.0 | **90.3** | **26.8** | **71.7** | **73.3** |
| BM25 only | 42.0 | 72.0 | 82.0 | 71.0 | 19.6 | 56.8 | 56.8 |
| Hybrid RRF only | 50.0 | 84.0 | 94.0 | 85.0 | 24.0 | 68.7 | 68.5 |
| Cross-encoder reranking | 52.0 | 82.0 | 90.0 | 84.7 | 24.8 | 67.9 | 68.7 |
| Weighted RRF + cross-encoder | 54.0 | 86.0 | 94.0 | 85.0 | 24.0 | 71.0 | 69.5 |
| Hybrid production baseline, before graph integration | 54.0 | 88.0 | 94.0 | 85.0 | 24.0 | 71.7 | 70.1 |
| Graph enhanced | 54.0 | 80.0 | 92.0 | 82.3 | 23.2 | 69.0 | 67.4 |
| Current production default, graph integrated | 54.0 | 80.0 | 92.0 | 82.3 | 23.2 | 69.0 | 67.4 |
| Graph-only, dense-seeded | 46.0 | 48.0 | 58.0 | 43.3 | 12.0 | 49.2 | 40.6 |

On V2, dense is strongest overall on Recall@5 and nDCG@5. BM25 performs best on exact identifiers (Recall@5 100.0%, MRR@5 80.6%) and less well on conceptual queries (Recall@5 50.0%). Every layer returned results for all eight no-answer queries, for a no-answer false-positive rate of **100%**; there is no abstention behavior in these retrieval paths.

### V2 query latency

Earlier offline service-runner rerun, median / p95 milliseconds per query, before graph was made the API's production default. Model initialization is excluded. Dense and hybrid modes include query embedding and hydration; BM25 is shown warm, with index-build time separately.

| Layer | p50 | p95 |
|---|---:|---:|
| Dense only | 15.8 | 28.6 |
| BM25 only, warm | 1.5 | 2.5 |
| Hybrid RRF only | 17.4 | 23.0 |
| Cross-encoder reranking | 426.5 | 482.1 |
| Weighted RRF + cross-encoder | 205.7 | 239.0 |
| Production hybrid | 60.4 | 291.0 |
| Graph enhanced | 238.2 | 1,835.9 |

BM25's first query, including index construction, measured **46.7 ms** in this rerun. Latency is variable across runs, especially graph p95; repeat before treating p95 as a stable service target.

## Current API and Swagger test

The API uses one route, `POST /retrieval/search`, and preserves the pre-graph production behavior: dense + BM25 candidate retrieval, RRF fusion, and the existing conditional cross-encoder reranking. The API request does not expose ablation modes. The earlier API mode selector and graph-default wiring have been removed. The graph experiments remain in the service-level evaluation runners and do not change the production route.

## Test retrieval through Swagger yourself

Start the backend and open `http://127.0.0.1:8000/docs`. Expand **POST `/retrieval/search`**, then select **Try it out**. Use this request body:

1. Open [Swagger UI](http://127.0.0.1:8000/docs).
2. Expand **POST `/retrieval/search`**, then select **Try it out**.
3. Use this request body to match the V1 semantic query:

```json
{
  "repository_id": 49,
  "query": "How are code chunks converted into embeddings?",
  "top_k": 5,
  "filters": {
    "exclude_roles": ["test", "fixture"]
  }
}
```

4. Select **Execute**. A successful response should be HTTP 200 and include `repository_id`, `query`, and `results`; each result includes a `file_path`, `content`, `chunk_id`, and score fields. The expected relevant file for this query is `backend/app/services/embedding/service.py`.
5. For an exact-identifier check, repeat with query `EmbeddingService`; the expected relevant file is the same.

6. Compare isolated hybrid and cross-encoder quality using the offline evaluation runners; Swagger exercises the production hybrid + conditional CE path only.

From `backend/`, run the V1 hybrid-only and cross-encoder quality checks with:

```powershell
.venv\Scripts\python.exe -m pytest tests/evals/retrieval/test_hybrid_only_runner.py tests/evals/retrieval/test_v22_runner.py -q -s
```
