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
total. These are integrated local Windows results, distinct from hosted CI evidence.

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
total. These integrated local Windows results include the current contract, model, data-integrity,
dashboard, and no-network tests.

## Deployment publication check

Deployment URL:
https://engineering-intelligence-dashboard-jq9xccatzgwy9y9hcrwmor.streamlit.app/

On 2026-07-27 at 16:04 UTC, a cookie-free anonymous HEAD request returned **HTTP 303** with a
`Location` beginning `https://share.streamlit.io/-/auth/app`.

The deployment is therefore **auth-gated**, not yet a recruiter-accessible public showcase.
The current `Overview`, `Drivers & retrospective patterns`, and `Forecast & trust` tabs are
verified locally, but must be rechecked anonymously after the owner makes the app public and
reboots it in Streamlit Community Cloud.
