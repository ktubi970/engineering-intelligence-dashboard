# Active Repository Selection Expansion Design

## Context

MergeLens currently exposes repository options from the repositories present in its committed
privacy-minimized snapshot. The committed snapshot contains `pandas-dev/pandas` and
`streamlit/streamlit`, and `scripts/refresh_data.py` uses those same two repositories by default.

The repository selection will be expanded with four public projects that have substantial pull
request histories:

- `microsoft/vscode`
- `tensorflow/tensorflow`
- `rust-lang/rust`
- `ruby/ruby`

Together with the two existing projects, the default and committed repository set will contain six
repositories.

## Goal

Make all six repositories available in the dashboard's existing `Repository` multiselect while
preserving the local-snapshot architecture, deterministic tests, privacy rules, and the existing
per-repository collection limit of 150 merged pull requests and 150 workflow runs.

## Non-goals

- Do not add repository text entry or arbitrary runtime repository discovery to the dashboard.
- Do not call GitHub from the Streamlit application or from tests.
- Do not change metric definitions, model features, model hyperparameters, or developer-safety
  guardrails.
- Do not deploy or claim updated remote or CI evidence as part of this local change.

## Chosen approach

Add the four repositories to `DEFAULT_REPOSITORIES` in `scripts/refresh_data.py`, then regenerate
the committed snapshot with the existing refresh pipeline and its default 150-row limit. The
dashboard already builds its repository options from the union of repository values in the pull
request and workflow frames, so it needs no new selection logic.

This approach is preferred over hard-coding options in the UI, which could expose repositories
without data, and over runtime GitHub fetching, which would introduce latency, credentials, API
failures, and non-deterministic behavior into the dashboard.

## Data flow

1. `scripts/refresh_data.py` supplies the six ordered `RepositoryRef` values to
   `refresh_snapshot`.
2. The existing GitHub client validates that every repository is public and collects at most 150
   merged pull requests plus at most 150 workflow runs per repository.
3. The existing pipeline normalizes and validates all rows before atomically replacing
   `pull_requests.csv`, `workflow_runs.csv`, and `metadata.json`.
4. `load_snapshot` reads the committed files.
5. `_render_filters` derives the sorted repository options from snapshot rows, so every repository
   with pull-request or workflow data becomes selectable.

If the refresh fails for any repository, the existing atomic-write behavior must leave the prior
committed snapshot intact. Authentication material may be passed only through `GITHUB_TOKEN`; it
must never be written to files, tests, logs, or user-facing output.

## Snapshot-derived evidence

Refreshing from two to six repositories changes the dataset and therefore changes model evaluation
results and portfolio claims derived from the committed snapshot. The implementation must
recalculate and update:

- snapshot row counts and repository coverage in `README.md`, `docs/data-card.md`, and
  `.github/pull_request_body.md`;
- chronological train/test row counts and model-versus-baseline results in `README.md` and
  `docs/model-card.md`;
- local quality evidence when it describes the old committed snapshot;
- contract tests that intentionally pin these published values.

Existing remote deployment and CI observations must remain clearly historical. They must not be
rewritten to imply that the expanded snapshot has been deployed or verified by CI.

The dashboard screenshot should be regenerated only if it visibly presents values from the old
snapshot. Any regenerated screenshot is local evidence and must be described as such.

## Testing

The change will follow test-driven development:

1. Update the refresh CLI test to expect the six ordered default repositories and six fake rows for
   each data type; run it and observe failure before changing production defaults.
2. Add or update a committed-snapshot contract assertion that all six repositories are represented
   in the metadata and in at least one snapshot data frame; observe failure before refreshing data.
3. Refresh the real snapshot outside the tests, recalculate derived model evidence, and update the
   relevant documentation and exact contract assertions.
4. Run the focused CLI, snapshot, dashboard, and model tests.
5. Run Ruff linting, Ruff formatting checks, and the full coverage gate.

Tests must use fake data sources and local files only. No test may call GitHub.

## Git integration

All specification, implementation, data, test, and documentation changes live on
`codex/add-active-repositories`, created from `codex/engineering-intelligence-dashboard`.
After local verification passes, merge the feature branch back into
`codex/engineering-intelligence-dashboard` without staging or deleting unrelated files such as the
existing untracked `output/` directory.
