# MergeLens architecture

## The flow in plain language

MergeLens has a collection path and a viewing path. Collection asks GitHub for public repository
records, converts them into small fixed-shape tables, validates them, and seals them into a local
snapshot. Viewing opens that snapshot and performs calculations locally. The dashboard never
silently falls back to the network.

```text
GitHub public REST API
        |
        v
mockable client -> pandas normalization -> validated CSV/JSON snapshot
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
the interactive app simple and makes the same inputs reproducible in tests.

## Boundaries and contracts

| Stage | Inputs | Outputs | Main dependencies | Important failure modes |
| --- | --- | --- | --- | --- |
| Source client | Public `owner/repository` references; optional environment token | Repository metadata, merged PR summaries/details, workflow-run dictionaries | `requests`, GitHub public REST API | rate limit, non-2xx response, malformed JSON, timeout, or repository marked private |
| pandas normalization | Public API dictionaries plus repository slug | Exact validated pull-request and workflow DataFrames | `pandas` | missing/null fields, wrong schema/order, duplicate repository identifiers, non-UTC timestamps, invalid duration |
| Snapshot pipeline | Valid frames and generated provenance | `pull_requests.csv`, `workflow_runs.csv`, `metadata.json` | `pathlib`, pandas, JSON | validation failure before write, filesystem error, or process interruption between individually atomic replacements |
| Metrics | Valid loaded frames | `DeliveryMetrics`, weekly trends, repository summaries | pandas | empty selections return explicit zero/`None` states; invalid input is expected to be rejected upstream |
| Model | At least 80 pull rows; repository, number, UTC creation time | trained predictor, test MAE, baseline MAE, test count, global importances | pandas, NumPy, scikit-learn | too few rows, missing opening fields, distribution shift, or baseline outperforming the model |
| Plotly/Streamlit | Local snapshot and optional filters | charts, metrics, evaluation, what-if forecast | Plotly, Streamlit | missing/invalid snapshot becomes an in-page error; empty filters become readable empty states |
| Tests and CI | Source, committed snapshot, deterministic fixtures | lint, format, behavior, privacy, snapshot, and coverage evidence | pytest, pytest-cov, Ruff, GitHub Actions | any failed command blocks the job; no test is allowed to make a network call |

## Precise data movement

1. `scripts/refresh_data.py` parses repository references and reads an optional `GITHUB_TOKEN`
   only from the process environment.
2. `GitHubClient` checks repository visibility, fetches merged pull requests and detail records,
   and fetches workflow runs.
3. `transform.py` derives durations, UTC calendar fields, and aggregate text/change sizes while
   discarding unapproved raw fields.
4. `pipeline.py` validates both frames before writing. Each final file is replaced atomically;
   metadata is written last as the natural completion marker. The operating system does not
   provide one transaction spanning all three files.
5. `load_snapshot` parses UTC timestamps and revalidates table schemas. Metrics and the model
   consume those DataFrames through public interfaces.
6. `dashboard.py` supplies UI behavior; the root `streamlit_app.py` is only a thin entry point.

The architecture deliberately stays in one Python package. There is no database, service layer,
background scheduler, hidden telemetry, or deployment dependency.
