# Engineering Intelligence Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publish `engineering-intelligence-dashboard`, branded as MergeLens, to analyze public GitHub delivery activity and forecast pull-request merge time with a tested, reproducible Python pipeline.

**Architecture:** The deployed Streamlit app reads a committed public snapshot so the recruiter demo never needs a secret or a live GitHub connection. A separate refresh command uses the GitHub REST API when a token is available, normalizes the responses with pandas, and writes privacy-minimized CSV files plus provenance metadata. Pure metric, model, and chart modules feed a thin dashboard; tests replace every external HTTP call with a deterministic fake.

**Tech Stack:** Python 3.13, pandas 3.0.3, Plotly 6.9.0, scikit-learn 1.9.0, Streamlit 1.59.2, Requests 2.34.2, pytest 9.1.1, pytest-cov 7.1.0, Ruff 0.16.0, GitHub Actions, Streamlit Community Cloud.

## Global Constraints

- GitHub repository name: `engineering-intelligence-dashboard`.
- Product name in the interface: `MergeLens`.
- Work only on branch `codex/engineering-intelligence-dashboard`.
- Support Python `>=3.11,<3.14`; develop and run CI on Python 3.13.
- Runtime dependency pins: `pandas==3.0.3`, `plotly==6.9.0`, `requests==2.34.2`, `scikit-learn==1.9.0`, `streamlit==1.59.2`.
- Development dependency pins: `pytest==9.1.1`, `pytest-cov==7.1.0`, `ruff==0.16.0`.
- Use public GitHub data only; never persist author logins, email addresses, avatars, comment text, access tokens, or repository secrets.
- The public dashboard must start from committed snapshots without `GITHUB_TOKEN`.
- The optional refresh path reads `GITHUB_TOKEN` only from the process environment and never logs it.
- The committed snapshot must contain at least 300 merged pull requests across at least two public repositories.
- The ML target is total merge time in hours. Evaluation uses a chronological 80/20 split and compares test MAE with a training-set median baseline.
- The dashboard must state that the model is experimental, non-causal, and not suitable for evaluating individual developers.
- No production behavior without a test that was observed failing for the expected reason first.
- Unit tests make no network requests. The HTTP boundary is replaced with a complete deterministic fake.
- CI runs Ruff linting, Ruff format checking, and pytest with at least 85% coverage of `src/engineering_intelligence`.
- README includes the public demo URL, screenshot, installation, data provenance, model evaluation, architecture, limitations, agent workflow, and reproducible commands.
- `AGENTS.md` states what coding agents may do, what they must not do, and what evidence is required before claiming completion.

## File Map

```text
.
├── .github/workflows/ci.yml
├── .streamlit/config.toml
├── AGENTS.md
├── LICENSE
├── README.md
├── data/snapshots/
│   ├── metadata.json
│   ├── pull_requests.csv
│   └── workflow_runs.csv
├── docs/
│   ├── agentic-development.md
│   ├── architecture.md
│   ├── data-card.md
│   ├── model-card.md
│   ├── quality-evidence.md
│   └── images/dashboard.png
├── pyproject.toml
├── requirements-dev.txt
├── requirements.txt
├── scripts/refresh_data.py
├── src/engineering_intelligence/
│   ├── __init__.py
│   ├── charts.py
│   ├── dashboard.py
│   ├── domain.py
│   ├── github_client.py
│   ├── metrics.py
│   ├── model.py
│   ├── pipeline.py
│   └── transform.py
├── streamlit_app.py
└── tests/
    ├── fixtures/github/
    │   ├── pull_detail.json
    │   ├── pulls_page.json
    │   └── workflow_runs.json
    ├── conftest.py
    ├── test_charts.py
    ├── test_dashboard.py
    ├── test_domain.py
    ├── test_github_client.py
    ├── test_metrics.py
    ├── test_model.py
    ├── test_pipeline.py
    └── test_transform.py
```

---

### Task 1: Reproducible Python Foundation and Repository Contract

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `src/engineering_intelligence/__init__.py`
- Create: `src/engineering_intelligence/domain.py`
- Test: `tests/test_domain.py`

**Interfaces:**
- Produces: `RepositoryRef.parse(value: str) -> RepositoryRef`
- Produces: `RepositoryRef.slug: str`
- Produces: `DataContractError(ValueError)`

- [ ] **Step 1: Add dependency and tool configuration**

Create exact pinned requirements and configure Ruff with `target-version = "py311"`, line length 100, lint rules `E`, `F`, `I`, `B`, `UP`, and pytest with `testpaths = ["tests"]`, `addopts = "-ra --strict-markers"`.

- [ ] **Step 2: Create and install the isolated Python environment**

Run:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements-dev.txt
```

- [ ] **Step 3: Write the failing repository-reference tests**

```python
import pytest

from engineering_intelligence.domain import DataContractError, RepositoryRef


def test_repository_ref_parses_owner_and_name() -> None:
    ref = RepositoryRef.parse("pandas-dev/pandas")
    assert (ref.owner, ref.name, ref.slug) == (
        "pandas-dev",
        "pandas",
        "pandas-dev/pandas",
    )


@pytest.mark.parametrize("value", ["", "pandas", "/pandas", "pandas/", "a/b/c"])
def test_repository_ref_rejects_invalid_slugs(value: str) -> None:
    with pytest.raises(DataContractError, match="owner/repository"):
        RepositoryRef.parse(value)
```

- [ ] **Step 4: Run the tests and observe the expected RED state**

Run: `python -m pytest tests/test_domain.py -q`

Expected: collection fails because `engineering_intelligence.domain` does not exist.

- [ ] **Step 5: Implement the minimal domain contract**

```python
from dataclasses import dataclass


class DataContractError(ValueError):
    """Raised when external or stored data violates the project contract."""


@dataclass(frozen=True, slots=True)
class RepositoryRef:
    owner: str
    name: str

    @classmethod
    def parse(cls, value: str) -> "RepositoryRef":
        parts = value.strip().split("/")
        if len(parts) != 2 or not all(parts):
            raise DataContractError("Repository must use the owner/repository form.")
        return cls(owner=parts[0], name=parts[1])

    @property
    def slug(self) -> str:
        return f"{self.owner}/{self.name}"
```

- [ ] **Step 6: Verify GREEN and quality tools**

Run: `python -m pytest tests/test_domain.py -q`

Expected: all domain tests pass.

Run: `python -m ruff check .`

Expected: exit code 0.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml requirements.txt requirements-dev.txt src tests/test_domain.py
git commit -m "build: establish tested Python foundation"
```

---

### Task 2: GitHub REST Client with a Fully Fakeable HTTP Boundary

**Files:**
- Create: `src/engineering_intelligence/github_client.py`
- Create: `tests/fixtures/github/pulls_page.json`
- Create: `tests/fixtures/github/pull_detail.json`
- Create: `tests/fixtures/github/workflow_runs.json`
- Create: `tests/conftest.py`
- Test: `tests/test_github_client.py`

**Interfaces:**
- Consumes: `RepositoryRef`
- Produces: `HttpTransport.get(url, *, headers, params, timeout) -> HttpResponse`
- Produces: `RequestsTransport`
- Produces: `GitHubClient.list_merged_pull_requests(ref, limit) -> list[dict[str, object]]`
- Produces: `GitHubClient.get_pull_request(ref, number) -> dict[str, object]`
- Produces: `GitHubClient.list_workflow_runs(ref, limit) -> list[dict[str, object]]`
- Produces: `GitHubApiError` and `GitHubRateLimitError`

- [ ] **Step 1: Add complete sanitized GitHub response fixtures**

The pull fixture must include documented fields `number`, `html_url`, `title`, `body`, `user`, `created_at`, `updated_at`, `closed_at`, `merged_at`, `draft`, `labels`, `author_association`, `head`, and `base`. The detail fixture additionally includes `additions`, `deletions`, `changed_files`, and `commits`. The workflow fixture includes `id`, `name`, `status`, `conclusion`, `created_at`, `updated_at`, `run_started_at`, `html_url`, and `head_sha`.

- [ ] **Step 2: Write failing behavior tests against a deterministic fake transport**

```python
def test_client_returns_only_merged_pull_requests(
    fake_transport: FakeTransport,
    repository: RepositoryRef,
) -> None:
    fake_transport.queue_json(200, load_fixture("pulls_page.json"))
    client = GitHubClient(transport=fake_transport, token=None)

    pulls = client.list_merged_pull_requests(repository, limit=2)

    assert [pull["number"] for pull in pulls] == [101, 99]


def test_client_translates_rate_limit_response(
    fake_transport: FakeTransport,
    repository: RepositoryRef,
) -> None:
    fake_transport.queue_json(
        403,
        {"message": "API rate limit exceeded"},
        headers={"x-ratelimit-remaining": "0"},
    )
    client = GitHubClient(transport=fake_transport, token=None)

    with pytest.raises(GitHubRateLimitError, match="rate limit"):
        client.list_merged_pull_requests(repository, limit=1)
```

The assertions target returned records and raised domain errors, not whether the fake was called.

- [ ] **Step 3: Verify the tests fail because the client is absent**

Run: `python -m pytest tests/test_github_client.py -q`

Expected: import or attribute failure naming `GitHubClient`.

- [ ] **Step 4: Implement the minimal client**

Use GitHub REST API version `2022-11-28`, a 15-second timeout, `Accept: application/vnd.github+json`, and `User-Agent: MergeLens/1.0`. Add `Authorization: Bearer <token>` only when a token is supplied. Convert HTTP 403/429 with zero remaining requests into `GitHubRateLimitError`; convert every other non-2xx status into `GitHubApiError`. Paginate until the requested number of merged pull requests is collected or GitHub returns an empty page.

- [ ] **Step 5: Add and pass pagination, detail, workflow, malformed JSON, and server-error tests**

Run: `python -m pytest tests/test_github_client.py -q`

Expected: all client tests pass without network access.

- [ ] **Step 6: Commit**

```bash
git add src/engineering_intelligence/github_client.py tests/fixtures tests/test_github_client.py
git commit -m "feat: add mockable GitHub data client"
```

---

### Task 3: Privacy-Minimized pandas Transformation and Snapshot Pipeline

**Files:**
- Create: `src/engineering_intelligence/transform.py`
- Create: `src/engineering_intelligence/pipeline.py`
- Create: `scripts/refresh_data.py`
- Modify: `tests/conftest.py`
- Test: `tests/test_transform.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: raw pull and workflow dictionaries from `GitHubClient`
- Produces: `normalize_pull_requests(records, repository) -> pd.DataFrame`
- Produces: `normalize_workflow_runs(records, repository) -> pd.DataFrame`
- Produces: `validate_pull_request_frame(frame) -> None`
- Produces: `validate_workflow_frame(frame) -> None`
- Produces: `refresh_snapshot(client, repositories, output_dir, pr_limit=150) -> SnapshotMetadata`
- Produces: `load_snapshot(data_dir) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]`

- [ ] **Step 1: Write failing pull-request transformation tests**

```python
def test_normalize_pull_requests_derives_hours_and_removes_identity(
    raw_pull_details: list[dict[str, object]],
) -> None:
    frame = normalize_pull_requests(raw_pull_details, "pandas-dev/pandas")

    assert frame.loc[0, "merge_hours"] == pytest.approx(48.0)
    assert frame.loc[0, "change_size"] == 140
    assert frame.loc[0, "title_length"] == 18
    assert "user" not in frame.columns
    assert "author_login" not in frame.columns
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_transform.py -q`

Expected: import failure naming `normalize_pull_requests`.

- [ ] **Step 3: Implement pull and workflow normalization**

Pull CSV columns, in this exact order:

```text
repository,number,created_at,merged_at,merge_hours,title_length,body_length,
author_association,labels_count,additions,deletions,change_size,changed_files,
commits,opened_weekday,opened_hour
```

Workflow CSV columns, in this exact order:

```text
repository,run_id,workflow_name,status,conclusion,created_at,updated_at,
duration_minutes
```

Parse all dates as UTC, remove unmerged pull requests, reject non-positive merge durations, calculate `change_size = additions + deletions`, and never retain `user`, login, email, avatar, head SHA, title text, body text, or comment text.

- [ ] **Step 4: Add schema, null, duplicate, UTC, and empty-data tests**

Run: `python -m pytest tests/test_transform.py -q`

Expected: all transformation tests pass.

- [ ] **Step 5: Write failing snapshot round-trip and provenance tests**

```python
def test_refresh_snapshot_writes_privacy_safe_reproducible_files(
    tmp_path: Path,
    fake_github_client: FakeGitHubClient,
) -> None:
    metadata = refresh_snapshot(
        fake_github_client,
        [RepositoryRef.parse("pandas-dev/pandas")],
        tmp_path,
        pr_limit=2,
    )

    pulls, workflows, stored_metadata = load_snapshot(tmp_path)
    assert len(pulls) == metadata.pull_request_rows == 2
    assert stored_metadata["schema_version"] == 1
    assert stored_metadata["repositories"] == ["pandas-dev/pandas"]
    assert "author_login" not in pulls.columns
```

- [ ] **Step 6: Verify RED, implement atomic CSV/JSON writes, then verify GREEN**

Write files to sibling `.tmp` paths and replace final files only after validation. Metadata keys are `schema_version`, `generated_at_utc`, `source`, `repositories`, `pull_request_rows`, and `workflow_run_rows`.

Run: `python -m pytest tests/test_pipeline.py tests/test_transform.py -q`

Expected: all pipeline and transformation tests pass.

- [ ] **Step 7: Add the refresh CLI**

`scripts/refresh_data.py` reads repository slugs from repeated `--repo`, defaults to `pandas-dev/pandas` and `streamlit/streamlit`, reads `GITHUB_TOKEN` from the environment, accepts `--limit-per-repo`, and writes only aggregate success information. It never prints request headers or the token.

- [ ] **Step 8: Commit**

```bash
git add src/engineering_intelligence/transform.py src/engineering_intelligence/pipeline.py scripts tests
git commit -m "feat: add reproducible privacy-safe data pipeline"
```

---

### Task 4: Delivery Indicators as Tested Pure pandas Calculations

**Files:**
- Create: `src/engineering_intelligence/metrics.py`
- Test: `tests/test_metrics.py`

**Interfaces:**
- Consumes: validated pull-request and workflow DataFrames
- Produces: `DeliveryMetrics`
- Produces: `calculate_delivery_metrics(pulls, workflows) -> DeliveryMetrics`
- Produces: `weekly_delivery_trend(pulls) -> pd.DataFrame`
- Produces: `repository_summary(pulls, workflows) -> pd.DataFrame`

- [ ] **Step 1: Write a failing literal-value metric test**

```python
def test_calculate_delivery_metrics_uses_literal_expected_values() -> None:
    pulls = pd.DataFrame(
        {
            "merge_hours": [12.0, 24.0, 36.0, 48.0],
            "merged_at": pd.to_datetime(
                [
                    "2026-01-05T00:00:00Z",
                    "2026-01-06T00:00:00Z",
                    "2026-01-12T00:00:00Z",
                    "2026-01-13T00:00:00Z",
                ],
                utc=True,
            ),
        }
    )
    workflows = pd.DataFrame({"conclusion": ["success", "failure", "success"]})

    metrics = calculate_delivery_metrics(pulls, workflows)

    assert metrics.merged_pull_requests == 4
    assert metrics.median_merge_hours == 30.0
    assert metrics.p90_merge_hours == pytest.approx(44.4)
    assert metrics.average_weekly_throughput == 2.0
    assert metrics.workflow_success_rate == pytest.approx(2 / 3)
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_metrics.py -q`

Expected: import failure naming `calculate_delivery_metrics`.

- [ ] **Step 3: Implement minimal pure calculations**

Use pandas quantile with linear interpolation, weekly periods beginning Monday, and every completed workflow with a non-null conclusion in the success-rate denominator. Return `None` for workflow success rate when no completed workflow exists.

- [ ] **Step 4: Add tests for empty workflow data, empty pull data, repository grouping, and week boundaries**

Run: `python -m pytest tests/test_metrics.py -q`

Expected: all metric tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/engineering_intelligence/metrics.py tests/test_metrics.py
git commit -m "feat: calculate tested delivery intelligence metrics"
```

---

### Task 5: Chronologically Evaluated Merge-Time Model

**Files:**
- Create: `src/engineering_intelligence/model.py`
- Test: `tests/test_model.py`

**Interfaces:**
- Consumes columns: `repository`, `created_at`, `merge_hours`, `title_length`, `body_length`, `author_association`, `labels_count`, `additions`, `deletions`, `change_size`, `changed_files`, `commits`, `opened_weekday`, `opened_hour`
- Produces: `chronological_split(frame, test_fraction=0.2) -> tuple[pd.DataFrame, pd.DataFrame]`
- Produces: `train_merge_time_model(frame, min_samples=80) -> ModelResult`
- Produces: `MergeTimeModel.predict_hours(features: pd.DataFrame) -> np.ndarray`
- Produces: `InsufficientTrainingDataError`

- [ ] **Step 1: Write failing chronological split tests**

```python
def test_chronological_split_keeps_future_rows_out_of_training(
    model_frame: pd.DataFrame,
) -> None:
    train, test = chronological_split(model_frame, test_fraction=0.2)
    assert train["created_at"].max() < test["created_at"].min()
    assert (len(train), len(test)) == (80, 20)
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_model.py::test_chronological_split_keeps_future_rows_out_of_training -q`

Expected: import failure naming `chronological_split`.

- [ ] **Step 3: Implement and pass the split**

Sort by `created_at` with a stable sort, use the oldest 80% for training and newest 20% for testing, and reject frames with fewer than two rows.

- [ ] **Step 4: Write failing model quality and minimum-data tests**

```python
def test_trained_model_beats_median_baseline_on_predictable_data(
    model_frame: pd.DataFrame,
) -> None:
    result = train_merge_time_model(model_frame, min_samples=80)
    assert result.test_rows == 20
    assert result.mae_hours < result.baseline_mae_hours
    assert result.feature_importance["change_size"] > 0


def test_training_rejects_too_few_rows(model_frame: pd.DataFrame) -> None:
    with pytest.raises(InsufficientTrainingDataError, match="80"):
        train_merge_time_model(model_frame.head(79), min_samples=80)
```

- [ ] **Step 5: Verify RED, implement the model, then verify GREEN**

Use a scikit-learn `ColumnTransformer` with median imputation for numeric values, most-frequent imputation plus `OneHotEncoder(handle_unknown="ignore")` for categorical values, and `RandomForestRegressor(n_estimators=200, max_depth=8, min_samples_leaf=3, random_state=42, n_jobs=-1)`. Fit on `log1p(merge_hours)` and convert predictions back with `expm1`. Calculate test MAE in hours and compare it with the training-set median baseline. Aggregate one-hot feature importance back to the original column names.

Run: `python -m pytest tests/test_model.py -q`

Expected: all model tests pass deterministically.

- [ ] **Step 6: Add tests proving input data is not mutated, predictions are non-negative, unknown repositories are accepted, and target/leakage columns are excluded**

Run: `python -m pytest tests/test_model.py -q`

Expected: all model tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/engineering_intelligence/model.py tests/test_model.py
git commit -m "feat: forecast merge time with honest evaluation"
```

---

### Task 6: Plotly Figures and a Thin Streamlit Dashboard

**Files:**
- Create: `src/engineering_intelligence/charts.py`
- Create: `src/engineering_intelligence/dashboard.py`
- Create: `streamlit_app.py`
- Create: `.streamlit/config.toml`
- Test: `tests/test_charts.py`
- Test: `tests/test_dashboard.py`

**Interfaces:**
- Consumes: validated snapshot DataFrames, `DeliveryMetrics`, and `ModelResult`
- Produces: `merge_time_trend_figure(frame) -> plotly.graph_objects.Figure`
- Produces: `size_delay_figure(frame) -> plotly.graph_objects.Figure`
- Produces: `repository_comparison_figure(frame) -> plotly.graph_objects.Figure`
- Produces: `feature_importance_figure(frame) -> plotly.graph_objects.Figure`
- Produces: `render_dashboard(data_dir: Path) -> None`

- [ ] **Step 1: Write failing figure-contract tests**

```python
def test_merge_time_trend_has_accessible_labels(
    pull_request_frame: pd.DataFrame,
) -> None:
    figure = merge_time_trend_figure(pull_request_frame)
    assert figure.layout.title.text == "Weekly merge time"
    assert figure.layout.xaxis.title.text == "Week"
    assert figure.layout.yaxis.title.text == "Median hours"
    assert len(figure.data) >= 1
```

- [ ] **Step 2: Verify RED, implement figures, then verify GREEN**

Use a shared high-contrast template, color-blind-safe colors, explicit axis labels, hover text that includes repository and values, and a readable empty-state annotation.

Run: `python -m pytest tests/test_charts.py -q`

Expected: all chart contract tests pass.

- [ ] **Step 3: Write a failing Streamlit smoke test**

```python
def test_dashboard_loads_snapshot_and_shows_core_sections(
    snapshot_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EID_DATA_DIR", str(snapshot_dir))
    app = AppTest.from_file("streamlit_app.py")
    app.run(timeout=20)
    assert not app.exception
    assert any("MergeLens" in title.value for title in app.title)
    assert len(app.tabs) == 3
    assert len(app.metric) >= 4
```

- [ ] **Step 4: Verify RED**

Run: `python -m pytest tests/test_dashboard.py -q`

Expected: failure because `streamlit_app.py` or `render_dashboard` is absent.

- [ ] **Step 5: Implement the three-tab dashboard**

Tab names are `Delivery pulse`, `Bottlenecks`, and `Forecast & trust`. The sidebar filters repository and merge date. The first tab shows four metrics and weekly trends. The second shows size-versus-delay and repository comparison. The third shows model MAE, median-baseline MAE, test row count, global feature importance, a what-if prediction form, and the exact warning: `Experimental forecast — not a causal measure and never a developer performance score.`

- [ ] **Step 6: Pass the dashboard test and full focused slice**

Run: `python -m pytest tests/test_charts.py tests/test_dashboard.py -q`

Expected: all dashboard and chart tests pass.

- [ ] **Step 7: Commit**

```bash
git add .streamlit src/engineering_intelligence/charts.py src/engineering_intelligence/dashboard.py streamlit_app.py tests/test_charts.py tests/test_dashboard.py
git commit -m "feat: present delivery intelligence in MergeLens"
```

---

### Task 7: Reproducible Public Snapshot

**Files:**
- Create: `data/snapshots/pull_requests.csv`
- Create: `data/snapshots/workflow_runs.csv`
- Create: `data/snapshots/metadata.json`
- Modify: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: the tested `scripts/refresh_data.py` path
- Produces: a committed snapshot accepted by `load_snapshot`

- [ ] **Step 1: Add a failing acceptance test for the real committed snapshot**

```python
def test_committed_snapshot_meets_portfolio_contract() -> None:
    pulls, workflows, metadata = load_snapshot(Path("data/snapshots"))
    assert len(pulls) >= 300
    assert pulls["repository"].nunique() >= 2
    assert len(workflows) > 0
    assert metadata["pull_request_rows"] == len(pulls)
    assert not {"user", "author_login", "email", "avatar_url"} & set(pulls.columns)
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_pipeline.py::test_committed_snapshot_meets_portfolio_contract -q`

Expected: failure because the committed snapshot does not exist.

- [ ] **Step 3: Generate the public snapshot**

Run with `GITHUB_TOKEN` present only in the environment:

```powershell
python scripts/refresh_data.py --repo pandas-dev/pandas --repo streamlit/streamlit --limit-per-repo 150
```

The command must report at least 300 pull requests and at least one workflow run without printing identities or credentials.

- [ ] **Step 4: Validate the snapshot and inspect privacy-sensitive columns**

Run: `python -m pytest tests/test_pipeline.py -q`

Expected: all pipeline tests pass, including the portfolio contract.

Run: `python -m ruff check .`

Expected: exit code 0.

- [ ] **Step 5: Commit**

```bash
git add data/snapshots tests/test_pipeline.py
git commit -m "data: add reproducible public GitHub snapshot"
```

---

### Task 8: CI, Documentation, Agent Guardrails, and Portfolio Evidence

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `AGENTS.md`
- Create: `LICENSE`
- Create: `README.md`
- Create: `docs/agentic-development.md`
- Create: `docs/architecture.md`
- Create: `docs/data-card.md`
- Create: `docs/model-card.md`
- Create: `docs/quality-evidence.md`

**Interfaces:**
- Consumes: all application commands and current evidence
- Produces: one reproducible CI workflow and recruiter-facing documentation

- [ ] **Step 1: Create the CI workflow**

On pushes to `master` and all pull requests, use `actions/checkout@v4` and `actions/setup-python@v5` with Python `3.13` and pip caching. Install `requirements-dev.txt`, then run:

```bash
python -m ruff check .
python -m ruff format --check .
python -m pytest --cov=engineering_intelligence --cov-report=term-missing --cov-fail-under=85
```

- [ ] **Step 2: Create human and agent documentation**

`README.md` includes problem, 30-second value statement, three feature bullets, metric definitions, architecture link, installation, offline demo, optional refresh, tests, model results read from the actual generated metadata/evaluation, limitations, privacy, and license. Task 9 adds the screenshot and live-demo URL only after both artifacts exist and have been verified.

`AGENTS.md` permits scoped code/test/doc changes and local verification. It prohibits secret access or output, production claims without evidence, network calls in tests, silent model-metric changes, author scoring, destructive Git commands, and deployment without an explicit in-scope request.

`docs/agentic-development.md` records each agent-assisted slice with request, human decision, files changed, RED evidence, GREEN evidence, and residual risk.

`docs/quality-evidence.md` records exact final commands and results, not predicted results.

- [ ] **Step 3: Run the complete local quality gate**

Run: `python -m ruff check .`

Expected: exit code 0.

Run: `python -m ruff format --check .`

Expected: exit code 0.

Run: `python -m pytest --cov=engineering_intelligence --cov-report=term-missing --cov-fail-under=85`

Expected: all tests pass and total package coverage is at least 85%.

- [ ] **Step 4: Commit**

```bash
git add .github AGENTS.md LICENSE README.md docs
git commit -m "docs: make quality and agent safeguards visible"
```

---

### Task 9: Visual QA, GitHub Publication, and Streamlit Deployment

**Files:**
- Create: `docs/images/dashboard.png`
- Modify: `README.md`
- Modify: `docs/quality-evidence.md`

**Interfaces:**
- Consumes: the complete local application and clean quality gate
- Produces: screenshot, public GitHub repository, public Streamlit URL, and final evidence

- [ ] **Step 1: Start and inspect the dashboard locally**

Run:

```powershell
python -m streamlit run streamlit_app.py --server.headless true --server.port 8501
```

Use browser automation to verify all three tabs, repository/date filters, empty-state behavior, interactive charts, forecast warning, and absence of horizontal overflow at desktop and narrow widths.

- [ ] **Step 2: Capture the real application**

Save a desktop screenshot of the running application to `docs/images/dashboard.png`. Do not generate or edit a substitute image.

- [ ] **Step 3: Re-run the final local gate after the screenshot and README update**

Run:

```bash
python -m ruff check .
python -m ruff format --check .
python -m pytest --cov=engineering_intelligence --cov-report=term-missing --cov-fail-under=85
```

Expected: every command exits 0 and coverage remains at least 85%.

- [ ] **Step 4: Publish the repository**

Verify GitHub authentication without printing a token, then run:

```bash
gh repo create engineering-intelligence-dashboard --public --source . --remote origin
git push -u origin master
git push -u origin codex/engineering-intelligence-dashboard
gh repo edit --default-branch master
gh pr create --draft --base master --head codex/engineering-intelligence-dashboard --title "feat: build MergeLens engineering intelligence dashboard" --body-file .github/pull_request_body.md
```

Create `.github/pull_request_body.md` before the final command with the verified summary, local quality commands, data provenance, model result, screenshot, and remaining limitations. Do not rewrite history.

- [ ] **Step 5: Verify remote CI**

Wait for the GitHub Actions workflow. It must report Ruff lint, Ruff format, and pytest/coverage success before the README claims CI is green.

- [ ] **Step 6: Deploy on Streamlit Community Cloud**

Deploy `streamlit_app.py` from the public repository. Record the resulting `https://*.streamlit.app` URL in `README.md`, open it in a clean browser session, and verify that it loads from the committed snapshot without `GITHUB_TOKEN`.

- [ ] **Step 7: Commit and push the verified publication evidence**

```bash
git add README.md docs/images/dashboard.png docs/quality-evidence.md
git commit -m "docs: add verified demo and publication evidence"
git push
```

- [ ] **Step 8: Final completion audit**

Check every Global Constraint against current files, local command output, remote CI, the deployed URL, and the rendered screenshot. Any missing or indirect evidence remains incomplete.

