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

`.github/workflows/ci.yml` defines the same binding commands for pushes to `master` and all pull
requests. This document does not claim a GitHub Actions result: the workflow has not been observed
running in this Task 8 worktree. Local evidence and future hosted CI status are separate.
