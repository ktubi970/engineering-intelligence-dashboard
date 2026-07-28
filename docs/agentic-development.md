# Agentic development record

MergeLens was delivered as eight reviewed vertical slices. The entries below use the task reports
and progress ledger; times, savings, quality scores, and unobserved outcomes are intentionally
omitted.

## Task 1 ? reproducible Python foundation

- **Request:** pin runtime/dev dependencies, establish the `src` package, and add repository/domain
  contracts.
- **Human decision:** no product choice was required.
- **Files/outcome:** packaging files, `domain.py`, package marker, and domain tests; commit
  `0b89faa`.
- **RED/GREEN:** missing `engineering_intelligence.domain`; then 6 focused tests passed. Ruff check
  and format were clean.
- **Review/fix:** review clean.
- **Residual risk:** generated egg-info remained untracked; Task 8 resolves this with an ignore
  rule without deleting it.

## Task 2 ? mockable GitHub client

- **Request:** collect public GitHub repository, merged-PR detail, and workflow data behind an
  injected transport with deterministic offline tests.
- **Human decision:** no product choice was required.
- **Files/outcome:** `github_client.py`, fake transport/fixtures, client tests; commits `bfb7970`
  and `5793711`.
- **RED/GREEN:** missing client module; final focused suite passed 12 tests and the then-full suite
  passed 17.
- **Review/fix:** an empty-page pagination regression test was added and mutation-proven.
- **Residual risk:** a valid falsey injected transport is still replaced because construction uses
  `transport or RequestsTransport()` rather than an explicit `None` check.

## Task 3 ? privacy-minimized snapshot pipeline

- **Request:** normalize API records with pandas, validate exact schemas, write/load an atomic local
  snapshot, and expose an explicit refresh CLI.
- **Human decision:** public data only; secrets must remain process-local and absent from output.
- **Files/outcome:** transformation, pipeline, CLI, fixtures, and behavior/privacy tests; commits
  `f850317` and `4b54534`.
- **RED/GREEN:** missing transform module, then missing pipeline/CLI interfaces; final full suite
  passed 47 tests.
- **Review/fix:** review found private-repository collection and in-progress workflow handling;
  both received focused RED/GREEN tests and fixes.
- **Residual risk:** `load_snapshot` validates frames but not the complete metadata schema/version
  and cross-file row-count agreement.

## Task 4 ? delivery metrics

- **Request:** calculate delivery indicators, UTC weekly trends, and repository summaries as pure
  pandas behavior.
- **Human decision:** no product choice was required.
- **Files/outcome:** `metrics.py` and metric tests; commit `efef9e0`.
- **RED/GREEN:** missing metrics module and later missing `repository_summary`; 5 focused and 52
  full tests passed.
- **Review/fix:** approved without Critical or Important findings.
- **Residual risk:** an empty repository summary has object dtype for every column rather than
  stable numeric dtypes.

## Task 5 ? merge-time model

- **Request:** chronologically evaluate a deterministic random forest against a train-median
  baseline and expose predictions plus feature importance.
- **Human decision:** **Option 1**?an honest PR-opening-time forecast using only repository, number,
  and UTC calendar features derived from creation time.
- **Files/outcome:** `model.py` and model tests; commits `bad0cad` and `4a9d1b9`.
- **RED/GREEN:** missing model module; the review fix then proved mutable fields changed predictions
  and all-NaN columns broke preprocessing. Final model suite passed 16 and full suite passed 68.
- **Review/fix:** mutable final-state features were removed and imputer dimensions stabilized with
  `keep_empty_features=True`.
- **Residual risk:** production usefulness is unproven under distribution shift; deferred minors
  cover test-fraction validation, tolerance, and stronger categorical-importance coverage.

## Task 6 ? Plotly and Streamlit product

- **Request:** present delivery pulse, retrospective bottlenecks, and forecast/trust views in a thin
  local Streamlit app.
- **Human decision:** show an honest winner/tie verdict and never present the model as causal or a
  developer score.
- **Files/outcome:** Streamlit config/entry point, charts, dashboard, and UI tests; commits `6efd2ae`
  and `9ffc47d`.
- **RED/GREEN:** missing charts and root app; after review fixes, 17 focused and 85 full tests
  passed.
- **Review/fix:** shared repository/date filtering and effective palette contrast each received a
  focused failing test and fix.
- **Residual risk:** MAE verdict and displayed one-decimal precision can disagree near equality;
  the form-widget exclusivity check is not exact.

## Task 7 ? committed public snapshot

- **Request:** generate, audit, and commit a recruiter-ready public snapshot through the approved
  refresh path.
- **Human decision:** use two approved public repositories and keep authentication only in the
  refresh process.
- **Files/outcome:** 300 PR rows, 199 workflow rows, metadata, and acceptance tests; commits
  `2d7bd2f` and `ac018ec`.
- **RED/GREEN:** the committed-snapshot contract failed because files were absent; final full suite
  passed 86 tests.
- **Review/fix:** workflow metadata parity and independent exact schema allowlists were added with
  mutation-proven REDs; snapshot bytes were restored and remained identical.
- **Residual risk:** a recent two-repository snapshot has survivorship, selection, and
  representativeness limits.

## Task 8 ? visible quality and agent safeguards

- **Request:** add binding CI, recruiter-first documentation, model/data/architecture evidence,
  agent guardrails, MIT licensing, and egg-info hygiene.
- **Human decision:** report the actual committed-snapshot result plainly; do not claim deployment
  before Task 9 verifies a screenshot and live URL.
- **Files/outcome:** CI, `AGENTS.md`, license, README, five supporting documents, a focused project
  contract test, and `.gitignore`.
- **RED:** `.\.venv\Scripts\python -m pytest tests\test_project_contract.py -q` failed 3 tests
  because the CI workflow, README, and AGENTS file were absent.
- **GREEN/review:** the focused contract passed 3 tests. The complete gate passed 89 tests with
  96.10% coverage; Ruff lint and format checks passed. Self-review corrected an overly
  case-sensitive data-card heading anchor and Ruff normalized the test file's mixed newline.
  Exact commands and results are in the quality-evidence document.
- **Residual risk:** GitHub Actions has not yet run; screenshot and deployment evidence remain
  explicitly deferred to Task 9.

## Task 9 - publication QA and live evidence

- **Request:** exercise the real local Streamlit UI, capture a genuine publication screenshot,
  publish the demo, and distinguish local browser, hosted CI, and live observations.
- **Human decision:** preserve the honest baseline-winning model result and label every claim by
  environment and revision rather than treating a deployment URL as proof.
- **Files/outcome:** browser and quality evidence, exact public tab labels, a 1440x1000 PNG, and
  the original live-demo/CI references, including the then-current screenshot in `ce303f2`.
  That initial remote evidence was later superseded by verified CI on `82e86b2` and the
  evidence refresh in `7990089`.
- **RED/GREEN:** local Playwright covered repository/date filters, empty states, Plotly hover,
  forecast safeguards, desktop/narrow overflow, and a zero-error application console. The final
  Task 9 gate passed 91 tests with 96.10% coverage; Ruff lint and format checks passed.
- **Review/fix:** the later publication-evidence pass pinned the screenshot URL to immutable SHA
  `ce303f2a4b5d81e98a478ec542542698e0f991b1`, decoded and verified the real PNG, enforced exact
  1440x1000 dimensions, and added corrupt/wrong-size negative cases in commit `a439c9c`.
- **Residual risk:** the initial live observation predates the verified CI evidence on `82e86b2`
  and the refresh in `7990089`; the current anonymous check is auth-gated. Local, CI, and live
  evidence remain distinct and are not interchangeable.

## Reviewer-driven hardening - current passes

A later read-only review opened bounded follow-up slices. A coordinator assigned disjoint file
ownership, required RED/GREEN evidence, and left integration of concurrent commits to the root
owner rather than letting agents overwrite each other's work.

- **Collection and isolation scope:** workflow runs now paginate at no more than 100 records per
  request, accumulate only completed runs, continue past partial/non-completed pages, and stop on
  the requested bound, an empty page, or a short final page. An autouse stdlib guard rejects
  outbound `socket.connect`, `socket.connect_ex`, and `socket.create_connection` entry points
  while injected transports and in-process AppTest remain network-free.
- **RED/GREEN:** the focused pagination/guard slice moved from 4 failed and 1 passed to 5 passed;
  the complete GitHub client suite then passed 18 tests. No real network request was used.
- **Evidence boundary:** other concurrent review findings are owned and verified separately; this
