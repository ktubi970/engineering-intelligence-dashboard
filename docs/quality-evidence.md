# MergeLens quality evidence

## Local evidence

Task 8 began with a focused project-contract test. Before the requested artifacts existed:

```powershell
.\.venv\Scripts\python -m pytest tests\test_project_contract.py -q
```

```text
3 failed in 0.22s
```

The failures named the missing CI workflow, README, and AGENTS file. The committed-snapshot model
evaluation also ran locally through `load_snapshot` and `train_merge_time_model`: model MAE
`26.624744394610`, baseline MAE `21.071861111111`, 60 test rows, baseline winner.

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
collected 89 items
TOTAL  487 statements  19 missed  96%
Required test coverage of 85% reached. Total coverage: 96.10%
89 passed in 39.87s
```

The percentage shown as `96%` is pytest-cov's table display; `96.10%` is its reported precise
total. These are local Windows results, not hosted CI evidence.

## GitHub Actions

The initial GitHub Actions quality check passed in 57s on SHA `f987033`:
https://github.com/ktubi970/engineering-intelligence-dashboard/actions/runs/30259194189/job/89954838617

That hosted job ran the binding Ruff lint, Ruff format, and pytest/coverage workflow for the initial
published revision. Pull request: https://github.com/ktubi970/engineering-intelligence-dashboard/pull/1

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
collected 91 items
TOTAL  487 statements  19 missed  96%
Required test coverage of 85% reached. Total coverage: 96.10%
91 passed in 51.38s
```

The percentage shown as `96%` is pytest-cov's table display; `96.10%` is its reported precise
total. These are local Windows results for the current branch and are distinct from the initial
hosted `f987033` result above.

## Verified live deployment

Public URL:
https://engineering-intelligence-dashboard-jq9xccatzgwy9y9hcrwmor.streamlit.app/

Anonymous Playwright verification of the initial deployed SHA `f987033` observed title
`MergeLens · Streamlit`. Inside the application iframe, both repositories and the snapshot
timestamp were visible with 300 merged pull requests, median merge time 17.4h, P90 merge time
152.2h, and workflow success 62.8%.
The deployed tabs were `Delivery pulse`, `Bottlenecks`, and `Forecast & trust`.
No visible traceback appeared. The iframe client and scroll widths were both
1280, confirming no horizontal iframe overflow.

The main anonymous Streamlit shell logged account/API 403/404 responses while the application
iframe loaded normally. This remote evidence is scoped to `f987033`; the current local branch
renames the first two tabs to `Overview` and `Drivers & retrospective patterns` and is covered by
the local browser and full-gate evidence above.
