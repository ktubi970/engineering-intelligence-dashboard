# MergeLens quality evidence

## Local evidence

Task 8 began with a focused project-contract test. Before the requested artifacts existed:

```powershell
.\.venv\Scripts\python -m pytest tests\test_project_contract.py -q
```

```text
3 failed in 0.22s
```

The failures named the missing CI workflow, README, and AGENTS file. The integrated, time-safe
evaluation uses 223 training rows, 60 chronological test rows, and purges 17 labels unavailable
at the cutoff. Its random-forest MAE is `17.499891193309` hours, versus
`20.535763888889` hours for the training-median baseline; the random forest wins this fixed
holdout by `3.035872695580` hours.

### Final local quality gate

All final-gate commands used the verified repository virtual environment on Python 3.13.9.

```powershell
.\.venv\Scripts\python -m ruff check .
```

```text
All checks passed!
```

```powershell
.\.venv\Scripts\python -m ruff format --check .
```

```text
30 files already formatted
```

```powershell
.\.venv\Scripts\python -m pytest --cov=engineering_intelligence --cov-report=term-missing --cov-fail-under=85
```

```text
collected 170 items
TOTAL  806 statements  44 missed  95%
Required test coverage of 85% reached. Total coverage: 94.54%
170 passed in 72.27s
```

The percentage shown as `95%` is pytest-cov's rounded table display; `94.54%` is its precise
total. These are target-commit local Windows results, distinct from the hosted CI evidence.

## GitHub Actions

The complete GitHub Actions quality gate passed on commit
`82e86b2fedc2526f6fc1eff6ce27941efbe0a00b`:
https://github.com/ktubi970/engineering-intelligence-dashboard/actions/runs/30282867104/job/90033339637

The Linux job used Python 3.13.14: Ruff lint and format checks passed, then **170 passed** in
12.25 seconds with **94.54%** coverage (85% required).
Pull request: https://github.com/ktubi970/engineering-intelligence-dashboard/pull/1

## Task 9 local browser evidence

This section records local Windows evidence collected on 2026-07-27 for the current branch.

The app ran from the committed snapshot with the repository virtual environment:

```powershell
.venv\Scripts\python.exe -m streamlit run streamlit_app.py --server.headless true --server.port 8501
```

The health endpoint returned `ok`. A named Playwright CLI session (`task-9`) then verified:

- the Overview loaded without an application error and reported 300 merged pull requests;
- the exact tabs `Overview`, `Drivers & retrospective patterns`, and `Forecast & trust` all opened;
- selecting only `pandas-dev/pandas` changed merged pull requests from 300 to 150 and changed the
  other metrics and trend;
- the real pandas-only date gap `2026-07-18` produced 0 pull requests plus the readable messages
  `No pull requests match the selected filters.` and
  `No data available for the selected filters.`, after which the full data was restored;
- hovering a rendered Plotly point produced `Repository: pandas-dev/pandas`,
  `Week: 2026-07-06`, and `Median merge time: 26.9 hours`;
- the forecast warning read exactly `Experimental forecast — not a causal measure and never a
  developer performance score.`; the visible inputs remained repository, pull-request number,
  opening date, and opening time only;
- at 1440x1000, document scroll/client widths were 1440/1440 and body widths were 1440/1440;
- at 390x844, document scroll/client widths were 390/390 and body widths were 390/390; and
- after all interactions, the browser console contained 0 errors. Fifteen repeated warnings were
  Streamlit's bundled Popper message that `preventOverflow` is required by `hide`; no application
  exception or failed data load accompanied them.

The restored 1440x1000 Overview was captured directly from that browser session as
`docs/images/dashboard.png` (PNG, 80,350 bytes). This is local browser evidence only.

### Task 9 final local quality gate

All commands used the verified repository virtual environment on Python 3.13.9.

```powershell
.venv\Scripts\python.exe -m ruff check .
```

```text
All checks passed!
```

```powershell
.venv\Scripts\python.exe -m ruff format --check .
```

```text
31 files already formatted
```

```powershell
.venv\Scripts\python.exe -m pytest --cov=engineering_intelligence --cov-report=term-missing --cov-fail-under=85
```

```text
collected 170 items
TOTAL  806 statements  44 missed  95%
Required test coverage of 85% reached. Total coverage: 94.54%
170 passed in 72.27s
```

The percentage shown as `95%` is pytest-cov's rounded table display; `94.54%` is its precise
total. These target-branch local Windows results include the current contract, model, data-integrity,
dashboard, and no-network tests.

## Active repository expansion local evidence

This section records local Windows browser evidence collected on 2026-07-27 for
`codex/add-active-repositories`. The committed snapshot contains 900 pull-request rows and 560
workflow-run rows and was generated at `2026-07-27T13:56:40.155501Z`.

A named Playwright CLI session (`active-repositories`) verified:

- the `Repository` multiselect exposed exactly the sorted choices `microsoft/vscode`,
  `pandas-dev/pandas`, `ruby/ruby`, `rust-lang/rust`, `streamlit/streamlit`, and
  `tensorflow/tensorflow`;
- all six repositories produced the expected 900 merged pull requests, while selecting only
  `microsoft/vscode` produced 150 merged pull requests without an application exception;
- `Overview`, `Drivers & retrospective patterns`, and `Forecast & trust` all rendered
  successfully;
- the browser console contained 0 errors; and
- the restored 1440x1000 Overview was captured as `docs/images/dashboard.png` (PNG, 91,844
  bytes).

This is local evidence for `codex/add-active-repositories`, not deployment or CI evidence.

### Active repository expansion final local quality gate

The complete feature-branch gate ran locally on Windows with Python 3.12.10.

```powershell
.\.venv\Scripts\python.exe -m ruff check .
```

```text
All checks passed!
```

```powershell
.\.venv\Scripts\python.exe -m ruff format --check .
```

```text
33 files already formatted
```

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=engineering_intelligence --cov-report=term-missing --cov-fail-under=85
```

```text
collected 93 items
TOTAL  487 statements  19 missed  96%
Required test coverage of 85% reached. Total coverage: 96.10%
93 passed in 39.29s
```

The percentage shown as `96%` is pytest-cov's table display; `96.10%` is its reported precise
total. `git diff --check` also completed without output. These are local Windows results for
`codex/add-active-repositories`, not hosted CI or deployment evidence.

## Integrated six-repository merge local evidence

This section records local Windows evidence for the resolved six-repository snapshot, schema-2
manifest, time-safe model evaluation, and record-aware canonical CSV hashing. No network collection
ran during integration.

### Post-fast-forward target local quality gate

All commands used the required repository environment on Python 3.13.9.

```powershell
C:\tmp\engineering-intelligence-dashboard\.venv\Scripts\python.exe -m ruff check .
```

```text
All checks passed!
```

```powershell
C:\tmp\engineering-intelligence-dashboard\.venv\Scripts\python.exe -m ruff format --check .
```

```text
33 files already formatted
```

```powershell
C:\tmp\engineering-intelligence-dashboard\.venv\Scripts\python.exe -m pytest --cov=engineering_intelligence --cov-report=term-missing --cov-fail-under=85
```

```text
collected 172 items
TOTAL  806 statements  44 missed  95%
Required test coverage of 85% reached. Total coverage: 94.54%
172 passed in 37.08s
```

`git diff --check` completed without output. These are local post-fast-forward target results, not
hosted CI or deployment evidence. The official GitHub Actions result on `82e86b2` remains
**170 passed**; this separate local target result is **172 passed** because it includes integration
evidence-contract coverage.

## Deployment publication check

Deployment URL:
https://engineering-intelligence-dashboard-jq9xccatzgwy9y9hcrwmor.streamlit.app/

On 2026-07-27 at 16:04 UTC, a cookie-free anonymous HEAD request returned **HTTP 303** with a
`Location` beginning `https://share.streamlit.io/-/auth/app`.

The deployment is therefore **auth-gated**, not yet a recruiter-accessible public showcase.
The current `Overview`, `Drivers & retrospective patterns`, and `Forecast & trust` tabs are
verified locally, but must be rechecked anonymously after the owner makes the app public and
reboots it in Streamlit Community Cloud.
