# Retrieval evaluation suites

`retrieval_v1.json` is the original eight-query regression set. `retrieval_v2.json` keeps those cases and adds 42 labeled cases covering exact identifiers, partial code terms, conceptual questions, and path/navigation queries. `retrieval_v2_no_answer.json` contains eight intentionally unanswerable queries; score these separately as false-positive-at-5 because ordinary recall is undefined when there are no relevant files.

The labels target repository 49 (`RepoIntel-AI`) in the local evaluation database. At suite creation it contained 121 indexed files and 847 chunks; excluding tests and fixtures left 633 source chunks. The eval filters exclude TEST and FIXTURE roles for every mode.

Compare the same positive and no-answer cases across:

1. Dense-only retrieval
2. BM25-only retrieval
3. Hybrid RRF candidates without cross-encoder reranking
4. Cross-encoder reranking of hybrid candidates
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

The Swagger endpoint remains a single production route and does not expose retrieval ablation modes. Use the offline runners above to compare retrieval layers; `hybrid_only_runner.py` isolates hybrid RRF and `v22_runner.py` evaluates the cross-encoder reranking path.
