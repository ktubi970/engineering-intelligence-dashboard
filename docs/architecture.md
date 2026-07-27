# MergeLens architecture

## The flow in plain language

MergeLens has a collection path and a viewing path. Collection asks GitHub for public repository
records, converts them into small fixed-shape tables, validates them, and seals their canonical
logical CSV hashes and provenance into a local snapshot. Viewing verifies and opens that snapshot
before performing calculations locally. The dashboard never silently falls back to the network.

```text
GitHub public REST API (2022-11-28)
        |
        v
mockable client -> pandas normalization -> validated CSVs + exact JSON manifest
                                                   |
                                          row/repository/hash checks
                                                   |
                                                   v
                                        metrics + model evaluation
                                                   |
                                                   v
                                           Plotly + Streamlit
                                                   |
                                                   v
                                     behavior tests + CI quality gate
```

Think of the snapshot as a checked, dated handoff between collection and presentation. This keeps
the interactive app simple and makes the same logical CSV inputs reproducible in tests.

## Boundaries and contracts

| Stage | Inputs | Outputs | Main dependencies | Important failure modes |
| --- | --- | --- | --- | --- |
| Source client | Public `owner/repository` references; optional environment token | Repository metadata, merged PR summaries/details, workflow-run dictionaries | `requests`, GitHub public REST API | rate limit, non-2xx response, malformed JSON, timeout, or repository marked private |
| pandas normalization | Public API dictionaries plus repository slug | Exact validated pull-request and workflow DataFrames | `pandas` | missing/null fields, wrong schema/order, duplicate identifiers, invalid repository, numeric type/range, state enum, UTC ordering, or derived-value mismatch |
| Snapshot pipeline | Valid frames, repository order, requested limits, generation time | two CSVs and schema-v2 `metadata.json` with source, counts, collection semantics, and canonical CSV SHA-256 | `pathlib`, pandas, JSON, SHA-256 | invalid manifest, count/repository mismatch, content-hash mismatch, filesystem error, or interruption between individually atomic replacements |
| Metrics | Valid loaded frames | `DeliveryMetrics`, weekly trends, repository summaries | pandas | empty selections return explicit zero/`None` states; invalid input is rejected upstream |
| Model | At least 80 pull rows; repository, number, UTC creation time | trained predictor, test MAE, baseline MAE, test count, global importances | pandas, NumPy, scikit-learn | too few rows, missing opening fields, distribution shift, or baseline outperforming the model |
| Plotly/Streamlit | Verified local snapshot and optional filters | charts, metrics, evaluation, what-if forecast | Plotly, Streamlit | missing/invalid snapshot becomes an in-page error; empty filters become readable empty states |
| Tests and CI | Source, committed snapshot, deterministic fixtures | lint, format, behavior, privacy, snapshot, and coverage evidence | pytest, pytest-cov, Ruff, GitHub Actions | any failed command blocks the job; no test is allowed to make a network call |

## Precise data movement

1. `scripts/refresh_data.py` parses repository references and reads an optional `GITHUB_TOKEN`
   only from the process environment.
2. `GitHubClient` checks repository visibility, uses GitHub REST API version `2022-11-28`, fetches
   merged pull requests and detail records, and fetches workflow runs.
3. `transform.py` derives durations, UTC calendar fields, and aggregate text/change sizes while
   discarding unapproved raw fields. Its validators independently recompute those values and
   enforce repository, identifier, numeric, enum, and timestamp invariants.
4. `pipeline.py` validates both frames, serializes both temporary CSV files, and computes SHA-256
   after normalizing CRLF and bare CR line endings to LF. This canonicalization is limited to
   snapshot CSV hashing; it does not rewrite other files. `.gitattributes` pins committed snapshot
   CSV checkouts to LF. The pipeline then creates an exact schema-v2 manifest with the generation
   time, public GitHub source/API version, repository order, row counts, selection, requested
   per-repository limits, API-default ordering, and file digests.
5. Each final file is replaced atomically, with metadata last as the natural completion marker.
   The operating system does not provide one transaction spanning all three files.
6. `load_snapshot` validates the manifest and hashes before parsing timestamps. It then revalidates
   both frames and compares manifest counts and repository set with the loaded rows. Metrics and
   the model consume only those verified DataFrames through public interfaces.
7. `dashboard.py` supplies UI behavior; the root `streamlit_app.py` is only a thin entry point.

The generation timestamp describes local snapshot creation, not a server-side as-of cutoff.
Collection did not request an explicit sort or direction, so the manifest truthfully records
`api_default` order.

The architecture deliberately stays in one Python package. There is no database, service layer,
background scheduler, hidden telemetry, or deployment dependency.
