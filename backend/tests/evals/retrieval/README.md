# Retrieval evaluation suites

`retrieval_v1.json` is the original eight-query regression set. `retrieval_v2.json` keeps those cases and adds 42 labeled cases covering exact identifiers, partial code terms, conceptual questions, and path/navigation queries. `retrieval_v2_no_answer.json` contains eight intentionally unanswerable queries; score these separately as false-positive-at-5 because ordinary recall is undefined when there are no relevant files.

The labels target repository 49 (`RepoIntel-AI`) in the local evaluation database. At suite creation it contained 121 indexed files and 847 chunks; excluding tests and fixtures left 633 source chunks. The eval filters exclude TEST and FIXTURE roles for every mode.

Compare the same positive and no-answer cases across:

1. Dense-only retrieval
2. BM25-only retrieval
3. Hybrid RRF candidates without cross-encoder reranking
4. Cross-encoder-only ranking of hybrid candidates
5. Weighted RRF and cross-encoder fusion
6. Production retrieval using the existing hybrid + conditional cross-encoder pipeline
7. Graph-enhanced retrieval
8. Graph-only expansion, seeded from each query's top two dense results

Report Hit@1/3/5, Recall@5, Precision@5, MRR@5, and nDCG@5 overall and by query category. For no-answer cases, report the fraction returning any file in the top five. Report latency separately for each layer, with warm and cold BM25 index behavior distinguished. Do not set hard quality floors from one run; review the per-case failures and confirm labels before freezing V2 as a regression gate.

The suite is run with:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests/evals/retrieval/test_retrieval_v2_all_layers.py -q -s
```

The JSON cases default to repository 49. If they are being evaluated against another indexed copy of the same repository, set `RETRIEVAL_EVAL_REPOSITORY_ID` to that database ID before running; for example, `$env:RETRIEVAL_EVAL_REPOSITORY_ID = "1752"` in PowerShell. Verify that the target repository has indexed files and chunks first, since a missing corpus otherwise produces meaningless all-zero metrics.

The Swagger endpoint remains a single production route and does not expose retrieval ablation modes. In the all-layer evaluation, `rrf_only_runner.py` measures hybrid RRF, `v22_fusion_runner.py` is run with RRF weight 0 for CE-only and 0.90 for weighted fusion, and `v22_runner.py` measures the production hybrid + conditional cross-encoder path. The hybrid-only service runner is not included as a separate row because it duplicates the RRF-only measurement.

## Knowledge Graph V1 comparison

Run the same answerable and no-answer cases against Hybrid V2 and graph modes:

```powershell
cd backend
$env:RETRIEVAL_EVAL_REPOSITORY_ID = "<indexed matching repository id>"
$env:GRAPH_EVAL_REPOSITORY_ID = $env:RETRIEVAL_EVAL_REPOSITORY_ID
uv run python -m tests.evals.retrieval.benchmark_graph_v1
```

The benchmark compares Hybrid V2 (A), Hybrid-seeded graph retrieval (B), independent graph-only retrieval (C), and combined Hybrid plus independent seeds (D). Independent seeding uses the existing repository-scoped BM25 index with exact symbol, qualified-name, and path metadata ranking; candidate lookup is bounded and filters are applied before selection. It does not run Hybrid V2 to generate seeds. Graph-only results use the existing query embedding and graph traversal; no second embedding model is introduced. The report includes seed hit rate/recall, candidate counts, per-stage latency, slowest case, and how many Hybrid misses each graph strategy recovers. `GRAPH_MAX_HOPS`, `GRAPH_CANDIDATE_MULTIPLIER`, `GRAPH_FUSION_WEIGHT`, and `GRAPH_COMBINED_BASELINE_RESERVE` control opt-in graph experiments. One-hop remains the default.

The 58-case V2 regression input remains unchanged. The separately versioned `retrieval_graph_structural_v1.json` now has 30 explicit file-level judgments spanning imports, cross-file dependencies, multi-hop tracing, authentication/configuration, retrieval internals, and cases where graph expansion should not help. Results remain a diagnostic and do not replace the 58-case quality baseline.

Measured independent-seed comparison (repository 2213; structural 30-case suite and unchanged 58-case V2 suite; one-hop; local run). The displayed p50/p95 values are per-query service timings; the first structural baseline query separately took **9,860 ms** during cold model initialization, so p95 does not represent process-startup latency.

| Suite / strategy | Hit@1 / 3 / 5 | Recall@5 | Precision@5 | MRR@5 | nDCG@5 | p50 / p95 ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Structural — Hybrid V2 (A) | 0.600 / 0.900 / 0.967 | 0.671 | 0.400 | 0.765 | 0.603 | 26.5 / 201.7 |
| Structural — Hybrid-seeded graph (B) | 0.600 / 0.900 / 0.967 | 0.604 | 0.367 | 0.761 | 0.566 | 39.3 / 75.1 |
| Structural — independent graph-only (C) | 0.567 / 0.900 / 0.933 | 0.533 | 0.313 | 0.725 | 0.517 | 27.1 / 57.2 |
| Structural — combined (D, reserve 4/5 baseline slots) | 0.600 / 0.900 / 0.967 | 0.629 | 0.373 | 0.761 | 0.576 | 53.1 / 93.6 |
| V2 58 — Hybrid V2 (A) | 0.500 / 0.900 / 0.920 | 0.890 | 0.268 | 0.684 | 0.715 | 24.1 / 42.4 |
| V2 58 — Hybrid-seeded graph (B) | 0.500 / 0.900 / 0.920 | 0.890 | 0.268 | 0.684 | 0.713 | 41.9 / 64.4 |
| V2 58 — independent graph-only (C) | 0.520 / 0.840 / 0.880 | 0.773 | 0.220 | 0.666 | 0.633 | 20.6 / 39.8 |
| V2 58 — combined (D, reserve 4/5 baseline slots) | 0.500 / 0.900 / 0.940 | 0.910 | 0.272 | 0.689 | 0.721 | 55.2 / 87.4 |

Independent seeds hit at least one judged relevant file for 93.3% of structural queries and 88% of the V2 cases; relevant-file seed recall was 55.7% and 73.3%, respectively. In the V2 set Hybrid missed four answerable cases: independent graph-only recovered `path_navigation_007` and `path_navigation_008` (2/4), and combined recovered `path_navigation_007` (1/4). On the structural set, Hybrid missed one case, `graph_structural_graph_candidate_filter_001`, recovered by independent graph-only; combined and Hybrid-seeded graph did not recover it. Thus independent entry points demonstrably add discovery, but independent graph-only is not a replacement for Hybrid V2. Combined mode gains 2.0 percentage points of V2 Recall@5 while adding about 31 ms to p50 and 45 ms to p95; structural Recall@5 remains 4.2 points below Hybrid V2. Keep combined and independent modes opt-in pending better structural fusion and broader multi-hop evidence.

The builder currently creates deterministic `IMPORTS` file edges from stored import-symbol metadata and an unambiguous indexed-path match. It does not emit `CALLS`, `REFERENCES`, or `DEPENDS_ON`: the current persisted symbol model does not contain call-site/reference records, and name-only matching would create speculative edges across scopes and languages. Add these only after deterministic call/reference extraction is persisted with source locations and tested for supported grammars. In particular, the current graph can validate import chains, but not caller/callee queries.

Measured local comparison (repository 2213, same indexed corpus, 58-case V2 suite; latest run): Hybrid V2 was Recall@5 **0.890**, MRR@5 **0.684**, nDCG@5 **0.7148**, p50/p95 **30.3/41.0 ms**. Graph-only, seeded by Hybrid V2, was **0.710/0.600/0.588** on Recall/MRR/nDCG, p50/p95 **52.2/84.2 ms**. Hybrid V2 + graph (post-rerank seeds, one hop) was **0.890/0.684/0.7132**, p50/p95 **80.5/110.3 ms**. Pre-rerank and dual-source seeds had the same aggregate quality, at **93.9/117.7 ms** and **96.0/152.6 ms** p50/p95. Post-rerank had the lowest p95 in this run. Graph candidate generation itself measured p50/p95 **16.9/31.4 ms** for post-rerank; the candidate SQL query was **8.4/21.1 ms** and traversal **3.8/6.3 ms**. Graph enhancement did not beat Hybrid V2 and added latency. Timings varied across repeated local runs, so treat the graph-stage measurements as the more direct estimate of added work and rerun on a quiet machine for release-grade latency comparisons.

The separate six-case structural suite is diagnostic and small: Hybrid V2 Recall@5 was **0.811**; graph-enhanced recall ranged from **0.672** (post-rerank) to **0.811** (pre/dual). Dual-source nDCG was **0.590** versus **0.588** for Hybrid V2, while post-rerank nDCG was **0.521**. This is not enough evidence to declare one strategy generally better. The structural baseline's first case included an **11.1 s** cold CrossEncoder load; warm p50 was **59.1 ms**. The existing eight-case legacy graph evaluation passed on repository 2213 (Hit@5 **1.000**, Recall@5 **1.000**, MRR@5 **0.6875**, nDCG@5 **0.7628**).

A candidate-query consolidation experiment reduced repeated per-hop SQL calls to one ranked query, but on the same 58-case benchmark candidate-query p50 rose from about **8 ms to 14 ms** without a quality gain. A further SQL-side similarity-floor predicate was slower still. Both query rewrites were reverted; the relevance gate remains after query-aware candidate selection. This leaves candidate query/traversal as the measured graph overhead to optimize next, and avoids keeping an unverified latency regression.
