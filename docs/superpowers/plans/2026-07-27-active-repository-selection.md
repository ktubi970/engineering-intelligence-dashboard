# Active Repository Selection Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `microsoft/vscode`, `tensorflow/tensorflow`, `rust-lang/rust`, and `ruby/ruby` to
MergeLens so the committed offline dashboard offers six repository choices with real snapshot
data.

**Architecture:** Extend the refresh CLI's ordered defaults and regenerate the three atomic
snapshot artifacts through the existing GitHub client and normalization pipeline. Keep Streamlit
offline: its existing repository multiselect continues to derive options from the loaded snapshot.
Recompute every snapshot-derived claim and preserve remote deployment evidence as historical.

**Tech Stack:** Python 3.13, pandas, scikit-learn, Streamlit, pytest, Ruff, GitHub public REST API,
Playwright CLI

## Global Constraints

- The ordered repository set is exactly `pandas-dev/pandas`, `streamlit/streamlit`,
  `microsoft/vscode`, `tensorflow/tensorflow`, `rust-lang/rust`, and `ruby/ruby`.
- Keep the existing limit of 150 merged pull requests and 150 workflow runs per repository.
- Do not call GitHub from the Streamlit application or from tests.
- Do not change metric definitions, model features, model hyperparameters, or developer-safety
  guardrails.
- Tests use fake data sources and local files only.
- Use `GITHUB_TOKEN` only if the user explicitly supplies it for the in-scope snapshot refresh;
  never print or persist it.
- Treat regenerated model results as reviewable product evidence and report them exactly, even when
  the baseline wins.
- Do not deploy or rewrite historical hosted evidence to imply that this branch passed remote CI.
- Preserve the unrelated untracked `output/` directory in the target worktree.

---

### Task 1: Expand the refresh CLI's default repository contract

**Files:**
- Modify: `tests/test_refresh_cli.py:1-58`
- Modify: `scripts/refresh_data.py:11-16`

**Interfaces:**
- Consumes: `RepositoryRef.parse(value: str) -> RepositoryRef` and
  `main(argv, *, environ, client_factory) -> int`.
- Produces: `DEFAULT_REPOSITORIES: tuple[RepositoryRef, ...]` containing the six ordered public
  repositories.

- [ ] **Step 1: Prepare the isolated worktree and prove the focused baseline**

Run from `C:\Users\ktubi\Documents\iacv\.worktrees\add-active-repositories`:

```powershell
git rev-parse --git-dir
git rev-parse --git-common-dir
git branch --show-current
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests\test_refresh_cli.py -q
```

Expected: the branch is `codex/add-active-repositories`; the focused baseline passes before any
production change. If the baseline fails, stop and diagnose it before continuing.

- [ ] **Step 2: Write the failing six-repository CLI test**

Add the ordered test constant near the imports in `tests/test_refresh_cli.py`:

```python
EXPECTED_DEFAULT_REPOSITORIES = [
    "pandas-dev/pandas",
    "streamlit/streamlit",
    "microsoft/vscode",
    "tensorflow/tensorflow",
    "rust-lang/rust",
    "ruby/ruby",
]
```

Change
`test_cli_uses_default_repositories_environment_token_and_sanitized_output` so its result
assertions are:

```python
assert captured_tokens == [secret]
assert metadata["repositories"] == EXPECTED_DEFAULT_REPOSITORIES
assert len(pulls) == 6
assert len(workflows) == 6
assert output.out == (
    f"Refreshed 6 pull requests and 6 workflow runs across 6 repositories into {tmp_path}.\n"
)
assert secret not in output.out + output.err
assert "Authorization" not in output.out + output.err
```

- [ ] **Step 3: Run the test and verify the expected RED state**

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\test_refresh_cli.py::test_cli_uses_default_repositories_environment_token_and_sanitized_output `
  -q
```

Expected: FAIL because metadata still contains only `pandas-dev/pandas` and
`streamlit/streamlit`, proving that the new assertion detects the missing defaults.

- [ ] **Step 4: Add the four production defaults**

Replace `DEFAULT_REPOSITORIES` in `scripts/refresh_data.py` with:

```python
DEFAULT_REPOSITORIES = (
    RepositoryRef.parse("pandas-dev/pandas"),
    RepositoryRef.parse("streamlit/streamlit"),
    RepositoryRef.parse("microsoft/vscode"),
    RepositoryRef.parse("tensorflow/tensorflow"),
    RepositoryRef.parse("rust-lang/rust"),
    RepositoryRef.parse("ruby/ruby"),
)
```

- [ ] **Step 5: Run the focused tests and verify GREEN**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_refresh_cli.py -q
.\.venv\Scripts\python.exe -m ruff check scripts\refresh_data.py tests\test_refresh_cli.py
.\.venv\Scripts\python.exe -m ruff format --check scripts\refresh_data.py tests\test_refresh_cli.py
```

Expected: all refresh CLI tests and both Ruff checks pass with no warnings.

- [ ] **Step 6: Commit the default expansion**

```powershell
git add -- scripts\refresh_data.py tests\test_refresh_cli.py
git commit -m "feat: expand default repository set"
```

---

### Task 2: Regenerate and prove the six-repository committed snapshot

**Files:**
- Modify: `tests/test_project_contract.py:1-178`
- Modify: `tests/test_dashboard.py:1-145`
- Modify: `data/snapshots/pull_requests.csv`
- Modify: `data/snapshots/workflow_runs.csv`
- Modify: `data/snapshots/metadata.json`

**Interfaces:**
- Consumes: `load_snapshot(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]`
  and the existing `Repository` sidebar multiselect.
- Produces: an atomic committed snapshot whose metadata and pull-request frame represent all six
  repositories, with exactly 900 merged pull-request rows; workflow coverage remains whatever the
  public Actions API returns for each project.

- [ ] **Step 1: Write the failing committed-snapshot coverage test**

Import the snapshot loader in `tests/test_project_contract.py`:

```python
from engineering_intelligence.pipeline import load_snapshot
```

Add this contract test:

```python
def test_committed_snapshot_covers_the_six_default_repositories() -> None:
    expected_repositories = [
        "pandas-dev/pandas",
        "streamlit/streamlit",
        "microsoft/vscode",
        "tensorflow/tensorflow",
        "rust-lang/rust",
        "ruby/ruby",
    ]

    pulls, workflows, metadata = load_snapshot(PROJECT_ROOT / "data" / "snapshots")

    assert metadata["repositories"] == expected_repositories
    assert set(pulls["repository"]) == set(expected_repositories)
    assert set(workflows["repository"]).issubset(expected_repositories)
    assert len(pulls) == 150 * len(expected_repositories)
```

- [ ] **Step 2: Write the failing dashboard behavior test**

Add this test to `tests/test_dashboard.py`:

```python
def test_committed_snapshot_exposes_all_six_repository_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("EID_DATA_DIR", raising=False)

    app = AppTest.from_file(APP_PATH)
    app.run(timeout=30)

    assert not app.exception
    assert app.sidebar.multiselect[0].options == [
        "microsoft/vscode",
        "pandas-dev/pandas",
        "ruby/ruby",
        "rust-lang/rust",
        "streamlit/streamlit",
        "tensorflow/tensorflow",
    ]
```

- [ ] **Step 3: Run both tests and verify the expected RED state**

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\test_project_contract.py::test_committed_snapshot_covers_the_six_default_repositories `
  tests\test_dashboard.py::test_committed_snapshot_exposes_all_six_repository_options `
  -q
```

Expected: both tests fail because the committed metadata and UI still expose only the two original
repositories.

- [ ] **Step 4: Require an explicitly supplied credential before the large refresh**

Run this guard without printing the token:

```powershell
if (-not (Test-Path Env:GITHUB_TOKEN)) {
    throw "Set GITHUB_TOKEN explicitly for the six-repository snapshot refresh."
}
```

Expected: the command succeeds only after the user has explicitly supplied `GITHUB_TOKEN` for this
operation. Do not inspect, echo, log, or persist its value.

- [ ] **Step 5: Regenerate the real snapshot through the production CLI**

```powershell
.\.venv\Scripts\python.exe scripts\refresh_data.py `
  --limit-per-repo 150 `
  --output-dir data\snapshots
```

Expected: the sanitized summary reports 900 pull requests, the collected workflow-run count, six
repositories, and no token or authorization header. Because snapshot writes are atomic, an API
failure must leave the three prior final files intact.

- [ ] **Step 6: Inspect the regenerated public metadata and repository distribution**

```powershell
Get-Content -Raw data\snapshots\metadata.json
Import-Csv data\snapshots\pull_requests.csv |
  Group-Object repository |
  Select-Object Name,Count
Import-Csv data\snapshots\workflow_runs.csv |
  Group-Object repository |
  Select-Object Name,Count
git diff --check
```

Expected: metadata lists the six repositories in the approved order; each pull-request group has
150 rows; workflow groups contain only approved repositories and may omit projects that expose no
completed GitHub Actions runs; `git diff --check` reports nothing.

- [ ] **Step 7: Run the snapshot and dashboard tests and verify GREEN**

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\test_project_contract.py::test_committed_snapshot_covers_the_six_default_repositories `
  tests\test_dashboard.py::test_committed_snapshot_exposes_all_six_repository_options `
  tests\test_pipeline.py `
  tests\test_dashboard.py `
  -q
```

Expected: all selected tests pass from local files without network calls.

- [ ] **Step 8: Commit the expanded snapshot**

```powershell
git add -- `
  data\snapshots\metadata.json `
  data\snapshots\pull_requests.csv `
  data\snapshots\workflow_runs.csv `
  tests\test_project_contract.py `
  tests\test_dashboard.py
git commit -m "data: add six-repository snapshot"
```

---

### Task 3: Recompute and bind snapshot-derived portfolio evidence

**Files:**
- Modify: `tests/test_project_contract.py:102-127`
- Modify: `README.md:15-35,110-139`
- Modify: `docs/data-card.md:1-82`
- Modify: `docs/model-card.md:24-82`
- Modify: `.github/pull_request_body.md:28-62`

**Interfaces:**
- Consumes: the six-repository snapshot and
  `train_merge_time_model(frame: pd.DataFrame) -> ModelResult`.
- Produces: exact repository counts, row counts, train/test sizes, model MAE, baseline MAE, winner,
  and difference claims bound to the committed snapshot.

- [ ] **Step 1: Replace hard-coded evidence expectations with snapshot-derived expectations**

Import the model trainer in `tests/test_project_contract.py`:

```python
from engineering_intelligence.model import train_merge_time_model
```

At the start of `test_published_portfolio_claims_match_verified_snapshot_and_evaluation`, load and
evaluate the committed data:

```python
pulls, workflows, _ = load_snapshot(PROJECT_ROOT / "data" / "snapshots")
result = train_merge_time_model(pulls)
model_mae = f"{result.mae_hours:.12f}"
baseline_mae = f"{result.baseline_mae_hours:.12f}"
difference = f"{abs(result.mae_hours - result.baseline_mae_hours):.12f}"

if result.mae_hours < result.baseline_mae_hours:
    winner = "model"
    result_sentence = "The model outperforms the baseline on this snapshot."
    model_card_difference = f"model is {difference} hours better"
elif result.baseline_mae_hours < result.mae_hours:
    winner = "baseline"
    result_sentence = "The model underperforms the baseline on this snapshot."
    model_card_difference = f"model is {difference} hours worse"
else:
    winner = "tie"
    result_sentence = "The model matches the baseline on this snapshot."
    model_card_difference = "model and baseline are equal"

honest_result = "tie" if winner == "tie" else f"{winner} wins"
```

Replace the old numeric README assertions with:

```python
readme = _artifact("README.md")
for claim in (
    f"{len(pulls)} merged pull requests and {len(workflows)} completed workflow runs",
    f"model and the newest 20% ({result.test_rows} rows) is held out for evaluation.",
    f"- Random-forest MAE: **{model_mae} hours**",
    f"- Training-median baseline MAE: **{baseline_mae} hours**",
    f"- Winner: **{winner}**, by **{difference} hours**",
    result_sentence,
):
    assert claim in readme
```

Replace the old numeric model-card assertions with:

```python
model_card = _artifact("docs/model-card.md")
training_rows = len(pulls) - result.test_rows
for claim in (
    f"With {len(pulls)} committed rows, that produces {training_rows} training rows and "
    f"{result.test_rows}\ntest rows.",
    f"| Test rows | {result.test_rows} |",
    f"| Random-forest MAE | {model_mae} hours |",
    f"| Train-median baseline MAE | {baseline_mae} hours |",
    f"| Difference | {model_card_difference} |",
    f"| Honest result | {honest_result} |",
    result_sentence.replace("this snapshot", "the committed snapshot"),
):
    assert claim in model_card
```

At the start of
`test_recruiter_readme_and_supporting_documents_publish_the_core_contract`, load the snapshot:

```python
pulls, workflows, _ = load_snapshot(PROJECT_ROOT / "data" / "snapshots")
```

Then change the data-card anchor assertion from fixed `("300", "199", ...)` values to:

```python
"docs/data-card.md": (
    str(len(pulls)),
    str(len(workflows)),
    "privacy",
    "## Limitations",
),
```

- [ ] **Step 2: Run the evidence contract and verify the expected RED state**

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\test_project_contract.py::test_recruiter_readme_and_supporting_documents_publish_the_core_contract `
  tests\test_project_contract.py::test_published_portfolio_claims_match_verified_snapshot_and_evaluation `
  -q
```

Expected: FAIL because README, data card, and model card still publish the two-repository snapshot
values.

- [ ] **Step 3: Print the exact local evidence without writing credentials or private fields**

```powershell
.\.venv\Scripts\python.exe -c "import json; from pathlib import Path; from engineering_intelligence.pipeline import load_snapshot; from engineering_intelligence.model import train_merge_time_model; p,w,m=load_snapshot(Path('data/snapshots')); r=train_merge_time_model(p); print(json.dumps({'generated_at_utc':m['generated_at_utc'],'repositories':m['repositories'],'pull_request_rows':len(p),'workflow_run_rows':len(w),'training_rows':len(p)-r.test_rows,'test_rows':r.test_rows,'model_mae_hours':f'{r.mae_hours:.12f}','baseline_mae_hours':f'{r.baseline_mae_hours:.12f}','difference_hours':f'{abs(r.mae_hours-r.baseline_mae_hours):.12f}','winner':'model' if r.mae_hours < r.baseline_mae_hours else 'baseline' if r.baseline_mae_hours < r.mae_hours else 'tie'}, indent=2))"
```

Expected: one JSON object containing only public snapshot metadata and aggregate evaluation values.
Use these exact formatted values in the documentation changes below.

- [ ] **Step 4: Update the README's current snapshot claims**

In `README.md`:

- replace the two-repository and 300/199-row current-snapshot language with the exact six-repository
  counts printed in Step 3;
- list the six repository slugs in the offline demo or data-refresh explanation;
- change the chronological split, both MAEs, winner, difference, and honest result sentence to the
  exact Step 3 values;
- change the limitation from two Python repositories to six large public projects while retaining
  the point-in-time, merged-only, public-project, and non-causal limitations;
- preserve the initial deployment observation as superseded historical context; current claims
  use the verified CI evidence from `82e86b2` and the evidence refresh in `7990089`.

- [ ] **Step 5: Update the data card, model card, and pull-request evidence**

Use the same Step 3 values:

- `docs/data-card.md`: generation timestamp, six ordered repositories, exact pull and workflow
  counts, and a limitation describing six high-volume public projects rather than two Python
  projects;
- `docs/model-card.md`: exact total/training/test rows, both MAEs, difference wording, winner, and
  honest comparison sentence;
- `.github/pull_request_body.md`: current committed-snapshot counts and model result, while retaining
  the initial deployment observation as superseded historical context and using `82e86b2`/`7990089`
  for the current verified evidence.

Do not alter metric definitions, model parameters, or the interpretation that the forecast is
experimental and non-causal.

- [ ] **Step 6: Run the evidence and model tests and verify GREEN**

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\test_project_contract.py `
  tests\test_model.py `
  -q
.\.venv\Scripts\python.exe -m ruff check tests\test_project_contract.py
.\.venv\Scripts\python.exe -m ruff format --check tests\test_project_contract.py
git diff --check
```

Expected: the documentation contracts and model tests pass, Ruff is clean, and Git reports no
whitespace errors.

- [ ] **Step 7: Commit the bound evidence**

```powershell
git add -- `
  README.md `
  docs\data-card.md `
  docs\model-card.md `
  .github\pull_request_body.md `
  tests\test_project_contract.py
git commit -m "docs: align evidence with six-repository snapshot"
```

---

### Task 4: Verify the real dashboard and refresh local visual evidence

**Files:**
- Modify: `docs/images/dashboard.png`
- Modify: `docs/quality-evidence.md:59-119`
- Test: `tests/test_dashboard.py`

**Interfaces:**
- Consumes: `streamlit_app.py`, the committed six-repository snapshot, and the browser-visible
  `Repository` multiselect.
- Produces: local browser evidence that all six options render, filtering works, no application
  exception is visible, and the restored 1440x1000 Overview matches the current snapshot.

- [ ] **Step 1: Start the local application as a hidden helper process**

```powershell
$streamlitProcess = Start-Process `
  -FilePath '.\.venv\Scripts\python.exe' `
  -ArgumentList '-m','streamlit','run','streamlit_app.py','--server.headless','true','--server.port','8501' `
  -PassThru `
  -WindowStyle Hidden
Invoke-WebRequest -UseBasicParsing http://localhost:8501/_stcore/health
```

Expected: the health endpoint returns `ok`. Keep `$streamlitProcess` so only this helper is stopped
after browser verification.

- [ ] **Step 2: Exercise the actual six-repository selection in a named Playwright session**

Use the `playwright` skill and a named session `active-repositories` to:

1. open `http://localhost:8501`;
2. set the viewport to 1440x1000;
3. verify the `Repository` multiselect contains exactly the six expected sorted options;
4. record the all-repository merged pull-request metric;
5. select only `microsoft/vscode` and verify the metric changes without an exception;
6. restore all six repositories;
7. verify all three tabs open and the browser console contains no application errors;
8. save the restored Overview to `docs/images/dashboard.png`.

Expected: the visible all-repository count equals the committed snapshot pull-row count, the
single-repository count is 150, all tabs render, and the screenshot contains the current values.

- [ ] **Step 3: Stop only the helper process started in Step 1**

```powershell
Stop-Process -Id $streamlitProcess.Id
```

Expected: the named local Streamlit helper exits; no unrelated process is touched.

- [ ] **Step 4: Record the new local browser evidence**

Append a dated `Active repository expansion local evidence` section to
`docs/quality-evidence.md`. Record:

- the exact snapshot counts and generation timestamp;
- the six visible repository choices;
- the 150-row `microsoft/vscode` filter result;
- successful rendering of `Overview`, `Drivers & retrospective patterns`, and
  `Forecast & trust`;
- console error count;
- screenshot path, dimensions, and byte size;
- that this is local evidence for `codex/add-active-repositories`, not deployment or CI evidence.

This original instruction was later superseded: retain the initial deployment observation only as
historical context, without its obsolete identifier. Current claims use verified CI evidence from
`82e86b2`, the evidence refresh in `7990089`, and the current auth-gated deployment observation.

- [ ] **Step 5: Verify the visual artifact and dashboard contracts**

```powershell
$png = [System.IO.File]::ReadAllBytes('docs\images\dashboard.png')
if ($png.Length -le 50000) { throw 'Dashboard screenshot is unexpectedly small.' }
if (-not ($png[0] -eq 137 -and $png[1] -eq 80 -and $png[2] -eq 78 -and $png[3] -eq 71)) {
    throw 'Dashboard screenshot is not a PNG.'
}
.\.venv\Scripts\python.exe -m pytest tests\test_dashboard.py tests\test_project_contract.py -q
git diff --check
```

Expected: the PNG validation, dashboard tests, documentation contracts, and whitespace check pass.

- [ ] **Step 6: Commit the local browser evidence**

```powershell
git add -- docs\images\dashboard.png docs\quality-evidence.md
git commit -m "docs: refresh expanded repository browser evidence"
```

---

### Task 5: Run the final quality gate and merge into the requested branch

**Files:**
- Modify if needed for exact final local evidence: `docs/quality-evidence.md`
- Merge target: `codex/engineering-intelligence-dashboard`

**Interfaces:**
- Consumes: all committed feature-branch changes and the repository's binding quality commands.
- Produces: a verified merge commit on `codex/engineering-intelligence-dashboard` while preserving
  unrelated target-worktree files.

- [ ] **Step 1: Run the complete feature-branch quality gate**

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pytest `
  --cov=engineering_intelligence `
  --cov-report=term-missing `
  --cov-fail-under=85
git diff --check
```

Expected: Ruff lint and formatting pass, all tests pass, coverage is at least 85%, and Git reports
no whitespace errors.

- [ ] **Step 2: Record the exact final local gate without implying CI**

Update the active-repository section in `docs/quality-evidence.md` with the exact Python version,
test count, elapsed time, and coverage emitted in Step 1. Label every value as local Windows
evidence for the feature branch.

Then rerun the binding checks after the documentation edit:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pytest `
  --cov=engineering_intelligence `
  --cov-report=term-missing `
  --cov-fail-under=85
git diff --check
```

Expected: the same complete gate passes again.

- [ ] **Step 3: Commit the final local evidence and verify a clean feature branch**

```powershell
git add -- docs\quality-evidence.md
git commit -m "docs: record active repository quality gate"
git status --short --branch
git log --oneline codex/engineering-intelligence-dashboard..HEAD
```

Expected: the feature worktree is clean and the log shows only the specification, plan, defaults,
snapshot, evidence, browser, and final-gate commits created for this feature.

- [ ] **Step 4: Inspect the target worktree before merging**

```powershell
git -C C:\tmp\engineering-intelligence-dashboard status --short --branch
git -C C:\tmp\engineering-intelligence-dashboard branch --show-current
```

Expected: the target branch is `codex/engineering-intelligence-dashboard`; the existing untracked
`output/` directory may remain. If tracked target changes exist, stop and inspect them before
merging so no user work is overwritten.

- [ ] **Step 5: Merge the verified feature branch**

Use the `superpowers:finishing-a-development-branch` skill, honoring the user's already selected
local-merge outcome, then run:

```powershell
git -C C:\tmp\engineering-intelligence-dashboard merge `
  --no-ff `
  codex/add-active-repositories `
  -m "merge: add active repository selection"
```

Expected: Git creates a merge commit without staging, deleting, or modifying `output/`.

- [ ] **Step 6: Verify the merged result on the target branch**

```powershell
C:\tmp\engineering-intelligence-dashboard\.venv\Scripts\python.exe -m ruff check .
C:\tmp\engineering-intelligence-dashboard\.venv\Scripts\python.exe -m ruff format --check .
C:\tmp\engineering-intelligence-dashboard\.venv\Scripts\python.exe -m pytest `
  --cov=engineering_intelligence `
  --cov-report=term-missing `
  --cov-fail-under=85
git -C C:\tmp\engineering-intelligence-dashboard status --short --branch
git -C C:\tmp\engineering-intelligence-dashboard log -3 --oneline --decorate
```

Expected: the merged branch passes the complete local gate; status contains no tracked changes and
still preserves any pre-existing untracked `output/` directory; the recent log contains the merge
commit.
