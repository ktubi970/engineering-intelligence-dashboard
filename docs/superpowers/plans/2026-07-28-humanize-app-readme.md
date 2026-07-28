# Humanize the App and README Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make MergeLens immediately understandable to recruiters and engineering managers while
keeping a mathematically precise prediction-model section for technical readers.

**Architecture:** Change presentation only. Keep all metrics, model code, snapshot data, and
historical evidence artifacts unchanged; rewrite the Streamlit and Plotly copy in place, then
replace the README with a product-first document that links to the existing specialist records.

**Tech Stack:** Python 3.13, Streamlit, Plotly, pytest, Ruff, Markdown, GitHub math notation.

## Global Constraints

- Keep the application and README in English.
- Recruiters and engineering managers are the primary audience; developers are secondary.
- Do not change metrics, model features, model parameters, snapshot data, or calculations.
- Do not refresh `data/snapshots` or edit snapshot-derived model values.
- Do not edit `docs/evidence/final-publication.json`, `docs/quality-evidence.md`, or
  `.github/pull_request_body.md`; they are dated evidence for the previously published release.
- Do not deploy, push, or claim new CI or live evidence.
- Keep privacy, non-causality, merged-only target, and no-developer-scoring safeguards visible.
- Keep the README's model-quality values rounded to one decimal and link exact
  environment-specific evidence instead of repeating it.
- Leave `docs/images/dashboard.png` unchanged and describe it as part of the dated public check;
  it records the previously verified release.
- Follow TDD: capture a focused RED result, make the smallest presentation change, then capture
  GREEN before running broader gates.

---

### Task 1: Make the dashboard journey product-first

**Files:**
- Modify: `tests/test_dashboard.py:54-107`
- Modify: `src/engineering_intelligence/dashboard.py:27-69,113-231`
- Modify: `tests/test_charts.py:20-105`
- Modify: `src/engineering_intelligence/charts.py:18-129`

**Interfaces:**
- Consumes: `render_dashboard(data_dir: Path) -> None` and the four existing Plotly figure
  functions.
- Produces: the same public function signatures with three product-focused tabs and
  plain-English chart labels.

- [ ] **Step 1: Replace the dashboard navigation and overview assertions**

In `tests/test_dashboard.py`, set the warning constant and core contract to:

```python
WARNING = (
    "Experimental estimate — not a delivery promise or an explanation of cause. "
    "Never use it to score developers."
)


def test_dashboard_loads_snapshot_and_shows_exact_core_sections(
    snapshot_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EID_DATA_DIR", str(snapshot_dir))

    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)

    assert not app.exception
    assert [title.value for title in app.title] == ["MergeLens"]
    assert [tab.label for tab in app.tabs] == [
        "Delivery overview",
        "Where work slows down",
        "Merge-time estimate",
    ]
    assert [metric.label for metric in app.metric] == [
        "PRs merged",
        "Typical merge time",
        "90% merged within",
        "Successful workflows",
    ]
    assert [subheader.value for subheader in app.subheader] == [
        "Merge time by week",
        "Patterns worth exploring",
        "Model evaluation",
        "What-if forecast",
    ]
    assert [warning.value for warning in app.warning] == [WARNING]


def test_dashboard_copy_is_product_first_and_hides_the_technical_stack(
    snapshot_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EID_DATA_DIR", str(snapshot_dir))

    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)

    visible_text = "\n".join(
        element.value
        for collection in (app.title, app.subheader, app.markdown, app.caption, app.info)
        for element in collection
    )
    assert "Typical is the median." in visible_text
    assert "past data" in visible_text
    for implementation_detail in (
        "Technical stack",
        "Streamlit",
        "pandas",
        "Plotly",
        "scikit-learn",
        "pytest",
    ):
        assert implementation_detail not in visible_text
```

Delete `test_technical_stack_view_exposes_the_runtime_layers`; the replacement proves that
implementation details are no longer in the main journey.

- [ ] **Step 2: Replace the chart-label assertions**

In `tests/test_charts.py`, change the visible-copy constants and expectations to:

```python
EMPTY_MESSAGE = "Nothing to show for these filters."


def test_merge_time_trend_has_accessible_labels_and_repository_hover() -> None:
    figure = merge_time_trend_figure(_pull_request_frame())

    assert figure.layout.title.text == "Typical merge time each week"
    assert figure.layout.xaxis.title.text == "Week"
    assert figure.layout.yaxis.title.text == "Hours to merge"
    assert {trace.name for trace in figure.data} == {"alpha/api", "beta/web"}
    assert all("Repository: %{fullData.name}" in trace.hovertemplate for trace in figure.data)
    assert all("Typical merge time: %{y:.1f} hours" in trace.hovertemplate for trace in figure.data)


def test_size_delay_chart_is_explicitly_retrospective_and_has_value_hover() -> None:
    figure = size_delay_figure(_pull_request_frame())

    assert figure.layout.title.text == "Do larger changes take longer to merge?"
    assert figure.layout.xaxis.title.text == "Lines changed (added + deleted)"
    assert figure.layout.yaxis.title.text == "Hours to merge"
    assert all("Lines changed: %{x}" in trace.hovertemplate for trace in figure.data)
    assert all("Time to merge: %{y:.1f} hours" in trace.hovertemplate for trace in figure.data)


def test_repository_comparison_has_labels_and_repository_value_hover() -> None:
    figure = repository_comparison_figure(_pull_request_frame())

    assert figure.layout.title.text == "Typical merge time by repository"
    assert figure.layout.xaxis.title.text == "Repository"
    assert figure.layout.yaxis.title.text == "Hours to merge"
    assert figure.data[0].x.tolist() == ["alpha/api", "beta/web"]
    assert figure.data[0].y.tolist() == [24.0, 36.0]
    assert "Typical merge time: %{y:.1f} hours" in figure.data[0].hovertemplate


def test_feature_importance_has_labels_and_feature_value_hover() -> None:
    importance = pd.DataFrame(
        {
            "feature": ["repository", "opened_hour", "number"],
            "importance": [0.2, 0.5, 0.3],
        }
    )

    figure = feature_importance_figure(importance)

    assert figure.layout.title.text == "What the estimate relies on most"
    assert figure.layout.xaxis.title.text == "Relative influence"
    assert figure.layout.yaxis.title.text == "Input"
    assert "Input: %{y}" in figure.data[0].hovertemplate
    assert "Relative influence: %{x:.3f}" in figure.data[0].hovertemplate
```

Keep the existing repository-name, data-order, color-accessibility, and empty-state assertions.

- [ ] **Step 3: Run the focused tests and capture RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_dashboard.py::test_dashboard_loads_snapshot_and_shows_exact_core_sections tests/test_dashboard.py::test_dashboard_copy_is_product_first_and_hides_the_technical_stack tests/test_charts.py -q
```

Expected: failures show the old four-tab navigation, old metric and chart labels, and visible
technical-stack content.

- [ ] **Step 4: Implement the three-tab journey and remove the technical-stack view**

In `src/engineering_intelligence/dashboard.py`, use:

```python
FORECAST_WARNING = (
    "Experimental estimate — not a delivery promise or an explanation of cause. "
    "Never use it to score developers."
)


def render_dashboard(data_dir: Path) -> None:
    st.set_page_config(page_title="MergeLens", page_icon="◈", layout="wide")
    st.title("MergeLens")
    st.caption(
        "Explore how pull requests move through public repositories—"
        "without tracking individual developers."
    )

    try:
        pulls, workflows, metadata = load_snapshot(data_dir)
    except (DataContractError, OSError, ValueError) as error:
        st.error(
            "MergeLens couldn't load its local data. "
            f"Check the snapshot files and try again. Details: {error}"
        )
        return

    st.sidebar.header("Filter the view")
    filtered_pulls, filtered_workflows = _render_filters(pulls, workflows)
    generated_at = metadata.get("generated_at_utc", "unknown")
    st.sidebar.caption(f"Snapshot updated: {generated_at}")

    delivery_tab, bottlenecks_tab, forecast_tab = st.tabs(
        [
            "Delivery overview",
            "Where work slows down",
            "Merge-time estimate",
        ]
    )
    with delivery_tab:
        _render_delivery_pulse(filtered_pulls, filtered_workflows)
    with bottlenecks_tab:
        _render_bottlenecks(filtered_pulls)
    with forecast_tab:
        _render_forecast(filtered_pulls)
```

Delete `_render_technical_stack`. In `_render_filters`, change `Repository` to `Repositories`,
`Merge date range` to `Merged between`, and the no-data caption to:

```python
st.sidebar.caption("No delivery records are available for this snapshot.")
```

Change the overview and retrospective sections to:

```python
def _render_delivery_pulse(pulls: pd.DataFrame, workflows: pd.DataFrame) -> None:
    metrics = calculate_delivery_metrics(pulls, workflows)
    columns = st.columns(4)
    columns[0].metric("PRs merged", f"{metrics.merged_pull_requests:,}")
    columns[1].metric("Typical merge time", _format_hours(metrics.median_merge_hours))
    columns[2].metric("90% merged within", _format_hours(metrics.p90_merge_hours))
    columns[3].metric("Successful workflows", _format_rate(metrics.workflow_success_rate))
    st.caption(
        "Typical is the median. “90% merged within” is the P90: "
        "nine out of ten PRs merged in that time or less."
    )

    if pulls.empty:
        st.info(
            "No pull requests match these filters. Try a wider date range or another repository."
        )
    st.subheader("Merge time by week")
    st.plotly_chart(merge_time_trend_figure(pulls), width="stretch")


def _render_bottlenecks(pulls: pd.DataFrame) -> None:
    st.subheader("Patterns worth exploring")
    st.caption(
        "These charts show patterns in past data. They do not prove why a pull request took longer."
    )
    st.plotly_chart(size_delay_figure(pulls), width="stretch")
    st.plotly_chart(repository_comparison_figure(pulls), width="stretch")
```

- [ ] **Step 5: Implement the chart copy**

In `src/engineering_intelligence/charts.py`, set:

```python
EMPTY_MESSAGE = "Nothing to show for these filters."
```

Use these `_base_figure` calls and hover fragments without changing the traces or calculations:

```python
# merge_time_trend_figure
figure = _base_figure("Typical merge time each week", "Week", "Hours to merge")
"Typical merge time: %{y:.1f} hours"

# size_delay_figure
figure = _base_figure(
    "Do larger changes take longer to merge?",
    "Lines changed (added + deleted)",
    "Hours to merge",
)
"Lines changed: %{x}"
"Time to merge: %{y:.1f} hours"

# repository_comparison_figure
figure = _base_figure(
    "Typical merge time by repository",
    "Repository",
    "Hours to merge",
)
"Typical merge time: %{y:.1f} hours"

# feature_importance_figure
figure = _base_figure(
    "What the estimate relies on most",
    "Relative influence",
    "Input",
)
"Input: %{y}<br>Relative influence: %{x:.3f}<extra></extra>"
```

- [ ] **Step 6: Run focused tests and capture GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_dashboard.py::test_dashboard_loads_snapshot_and_shows_exact_core_sections tests/test_dashboard.py::test_dashboard_copy_is_product_first_and_hides_the_technical_stack tests/test_charts.py -q
```

Expected: all selected tests pass.

- [ ] **Step 7: Commit the product-first journey**

```powershell
git add -- src/engineering_intelligence/dashboard.py src/engineering_intelligence/charts.py tests/test_dashboard.py tests/test_charts.py
git commit -m "feat: simplify the dashboard journey"
```

---

### Task 2: Explain the forecast in human terms

**Files:**
- Modify: `tests/test_dashboard.py:109-215,316-350`
- Modify: `src/engineering_intelligence/dashboard.py:82-111,233-322`

**Interfaces:**
- Consumes: unchanged `ModelResult`, `opening_feature_frame`, and `preferred_forecast`.
- Produces: unchanged forecast behavior with plain-language labels, comparison messages, and
  insufficient-data states.

- [ ] **Step 1: Write the forecast-copy contract**

Update `test_forecast_form_accepts_only_opening_time_features` to require:

```python
assert {
    "Repository",
    "Pull request number",
    "Opening date (UTC)",
    "Opening time (UTC)",
}.issubset(widget_labels)
```

In `test_dashboard_loads_snapshot_and_shows_exact_core_sections`, update the final two subheader
expectations to:

```python
("How accurate is the estimate?",)
("Try an estimate",)
```

Replace the submission assertions with:

```python
assert len(success_estimates) == 1
assert "Recommended — Model estimate" in success_estimates[0]
assert any("Simple benchmark" in value for value in info_estimates)

estimate_cards = success_estimates + info_estimates
assert len(estimate_cards) == 2
assert all("Average error on recent test data" in value for value in estimate_cards)
assert all("not a guaranteed range" in value for value in estimate_cards)

visible_text = "\n".join(
    element.value
    for collection in (app.caption, app.info, app.success, app.markdown)
    for element in collection
)
assert "pull requests that eventually merge" in visible_text
assert "MAE is the average number of hours" in visible_text
```

Update the readable-state assertions to require:

```python
assert any("Choose at least 80 pull requests" in info.value for info in app.info)
```

Change the empty-filter assertion to:

```python
assert any("No pull requests match these filters." in info.value for info in app.info)
```

Replace the evaluation-summary parameterization with:

```python
@pytest.mark.parametrize(
    ("model_mae", "baseline_mae", "expected_level", "expected_winner"),
    [
        (8.0, 12.0, "success", "The model was more accurate"),
        (12.0, 8.0, "info", "The simple benchmark was more accurate"),
        (8.0, 8.0, "info", "The model and simple benchmark were equally accurate"),
    ],
)
```

- [ ] **Step 2: Run forecast tests and capture RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_dashboard.py -q
```

Expected: failures identify the old `Forecast repository`, `Held-out MAE`, `Validated default`,
and chronological-evaluation wording.

- [ ] **Step 3: Rewrite the evaluation summary without changing its decision rule**

In `src/engineering_intelligence/dashboard.py`, replace `evaluation_summary` with:

```python
def evaluation_summary(
    model_mae: float,
    baseline_mae: float,
) -> tuple[str, str]:
    if model_mae < baseline_mae:
        return (
            "success",
            "The model was more accurate on recent test data "
            f"(average error: {model_mae:.1f} vs {baseline_mae:.1f} hours).",
        )
    if baseline_mae < model_mae:
        return (
            "info",
            "The simple benchmark was more accurate on recent test data "
            f"(average error: {baseline_mae:.1f} vs {model_mae:.1f} hours).",
        )
    return (
        "info",
        "The model and simple benchmark were equally accurate on recent test data "
        f"({model_mae:.1f} hours of average error).",
    )
```

Keep `preferred_forecast` unchanged so a tie still chooses the simpler baseline.

- [ ] **Step 4: Rewrite the forecast panel and result cards**

Use the following user-facing copy in `_render_forecast`:

```python
st.warning(FORECAST_WARNING)
st.subheader("How accurate is the estimate?")
```

For `InsufficientTrainingDataError`, show:

```python
st.info(
    "Choose at least 80 pull requests to test this estimate honestly "
    "against newer data. The estimate is unavailable for this selection."
)
```

Rename the second section and its form:

```python
st.subheader("Try an estimate")
st.caption(
    "Enter only what is known when a pull request opens. "
    "The result estimates time to merge for pull requests that eventually merge."
)

repository = st.selectbox("Repository", repositories)
# Keep the remaining inputs and their UTC behavior unchanged.
submitted = st.form_submit_button("Estimate merge time")
```

Build the result messages as:

```python
baseline_message = (
    f"Simple benchmark estimate: {result.baseline_hours:.1f} hours\n\n"
    f"Average error on recent test data: {result.baseline_mae_hours:.1f} hours. "
    "This is context, not a guaranteed range."
)
model_message = (
    f"Model estimate: {model_prediction:.1f} hours\n\n"
    f"Average error on recent test data: {result.mae_hours:.1f} hours. "
    "This is context, not a guaranteed range."
)
```

Keep the existing lower-MAE selection logic, but prefix the highlighted card with
`Recommended — ` rather than `Validated default — `.

- [ ] **Step 5: Rewrite the evaluation cards and define MAE in place**

In `_render_evaluation`, use:

```python
columns = st.columns(4)
columns[0].markdown(f"**Model: average error**\n\n{result.mae_hours:.1f} hours")
columns[1].markdown(f"**Simple benchmark: average error**\n\n{result.baseline_mae_hours:.1f} hours")
columns[2].markdown(f"**Past examples used**\n\n{result.train_rows:,}")
columns[3].markdown(f"**Recent examples tested**\n\n{result.test_rows:,}")
st.caption(
    "MAE is the average number of hours each estimate missed by on recent test data; "
    "lower is better. "
    f"Testing starts {result.cutoff.date().isoformat()}. "
    f"{result.purged_rows:,} earlier PRs were left out because their outcomes "
    "were not yet known."
)
```

Keep the call to `evaluation_summary` and its success/info rendering unchanged.

- [ ] **Step 6: Run the dashboard suite and capture GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_dashboard.py -q
```

Expected: every dashboard test passes; feature construction and winner selection remain
unchanged.

- [ ] **Step 7: Commit the human forecast copy**

```powershell
git add -- src/engineering_intelligence/dashboard.py tests/test_dashboard.py
git commit -m "feat: explain merge estimates in plain English"
```

---

### Task 3: Replace the README with progressive disclosure and mathematical model detail

**Files:**
- Modify: `tests/test_project_contract.py:14-35,154-204,225-303,463-545,675-748`
- Modify: `README.md:1-end`

**Interfaces:**
- Consumes: the existing published snapshot values from `load_snapshot` and
  `train_merge_time_model`.
- Produces: a concise recruiter-facing README whose technical layer defines \(Y\), \(X\), \(f\),
  the chronological split, MAE, and the median baseline.

- [ ] **Step 1: Replace the README structure contract**

In `test_recruiter_readme_and_supporting_documents_publish_the_core_contract`, require:

```python
for anchor in (
    "# MergeLens",
    "engineering-intelligence-dashboard",
    "## See it in action",
    "## What you can explore",
    "## Run it locally",
    "## Prediction model",
    "## How it works",
    "## Trust and limits",
    "## Project details",
    "## License",
    "streamlit run streamlit_app.py",
    "python scripts/refresh_data.py",
    "python -m ruff check .",
    "python -m ruff format --check .",
    "python -m pytest --cov=engineering_intelligence --cov-report=term-missing --cov-fail-under=85",
):
    assert anchor in readme

assert len(readme.split()) < 1_000
for removed_heading in (
    "## Agentic engineering with Codex, Sol, and Ultra reasoning",
    "## Metric definitions",
    "## Architecture",
    "## Installation",
    "## Offline demo",
    "## Optional data refresh",
    "## Tests",
    "## Model results",
    "## Limitations",
    "## Privacy",
):
    assert removed_heading not in readme
```

Keep the existing supporting-document anchors. They prove that the deeper material remains
available after it leaves the main README flow.

- [ ] **Step 2: Add the mathematical-model contract**

Add:

```python
def test_readme_defines_the_prediction_mathematically() -> None:
    readme = _artifact("README.md")

    for mathematical_anchor in (
        r"Y_i =",
        r"\mathrm{merged\_at}_i-\mathrm{created\_at}_i",
        r"X_i =",
        r"\mathrm{year}(t_i)",
        r"\mathrm{weekday}(t_i)",
        r"\widehat{Y}_i = f(X_i)",
        r"\phi(X_i)",
        r"\sum_{b=1}^{200}T_b",
        r"\mathrm{MAE}",
        r"\left|Y_i-\widehat{Y}_i\right|",
    ):
        assert mathematical_anchor in readme

    for model_contract in (
        "pull requests that eventually merge",
        "No developer identity",
        "200-tree random forest",
        "maximum depth 8",
        "at least 3 training samples per leaf",
        "newest 20%",
        "median merge time from the training set",
    ):
        assert model_contract in readme
```

- [ ] **Step 3: Simplify snapshot-result and evidence assertions**

In `test_published_portfolio_claims_match_verified_snapshot_and_evaluation`, replace the README
claim list with:

```python
for claim in (
    "900 merged pull requests and 560 completed workflow runs",
    "The newest 20% (180 rows) is the chronological test set.",
    "622",
    "180",
    "98",
    "2026-07-24T08:38:56+00:00",
    f"{model_mae_display} hours",
    f"{baseline_mae_display} hours",
    f"about {relative_reduction_display} lower average error",
    "estimates the number of hours",
    "pull requests that eventually merge",
):
    assert claim in readme
```

Apply the environment-variance wording contract only to `docs/model-card.md` and
`.github/pull_request_body.md`:

```python
for document in (model_card, pull_request_body):
    assert "rounded to one decimal" in document
    assert "execution environments" in document
    assert "does not isolate a single causal factor" in document
```

Keep the exact-value prohibition for all three documents:

```python
for document in (readme, model_card, pull_request_body):
    assert "9.734692264131" not in document
    assert "2.749469772906" not in document
```

Delete `README_LIVE_DEMO_SHA256`. Read the renamed section with:

```python
readme_live_demo = _markdown_section(readme, "## See it in action")
```

Remove `readme_live_demo` from `evidence_section_contracts`, then verify its concise semantic
contract separately:

```python
normalized_readme_live_demo = _normalized(readme_live_demo)
for claim in (
    PUBLIC_DEPLOYMENT_URL,
    "July 28, 2026",
    "without sign-in",
    "all six repositories",
    "point-in-time check",
    PUBLICATION_MANIFEST_PATH,
    "docs/quality-evidence.md",
):
    assert claim in normalized_readme_live_demo

for internal_evidence_detail in (
    EVIDENCE_COMMIT,
    EVIDENCE_TEST_RESULT,
    EVIDENCE_COVERAGE,
    "Technical stack",
):
    assert internal_evidence_detail not in normalized_readme_live_demo
```

Leave the digest-pinned PR body, local-gate, CI, final-public, manifest, and screenshot evidence
contracts unchanged.

- [ ] **Step 4: Replace obsolete README-specific tests**

Replace `test_readme_uses_exact_current_public_tab_names` with:

```python
def test_readme_names_the_current_product_views() -> None:
    readme = _artifact("README.md")

    for view_name in (
        "Delivery overview",
        "Where work slows down",
        "Merge-time estimate",
    ):
        assert view_name in readme

    for old_view_name in (
        "Drivers & retrospective patterns",
        "Forecast & trust",
        "Technical stack",
    ):
        assert old_view_name not in readme
```

Replace `test_readme_explains_the_codex_sol_ultra_engineering_workflow` with:

```python
def test_readme_links_to_deeper_engineering_records_without_repeating_them() -> None:
    readme = _artifact("README.md")

    for link in (
        "[Architecture](docs/architecture.md)",
        "[Data card](docs/data-card.md)",
        "[Model card](docs/model-card.md)",
        "[Quality evidence](docs/quality-evidence.md)",
        "[Agentic development](docs/agentic-development.md)",
        "[Repository guardrails](AGENTS.md)",
    ):
        assert link in readme

    assert "Codex + Sol + Ultra" not in readme
    assert "read-only independent review agents" not in readme
    assert "1 failed, 7 passed" not in readme
```

- [ ] **Step 5: Run the documentation contract and capture RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_project_contract.py -q
```

Expected: the new headings, concise evidence section, current view names, mathematical anchors,
and word-count limit fail against the old README.

- [ ] **Step 6: Replace `README.md` with the approved product-first copy**

Use the following complete document:

````markdown
# MergeLens

MergeLens helps teams see where pull requests slow down and explore a careful estimate of merge
time—without ranking individual developers.

This portfolio project, `engineering-intelligence-dashboard`, runs from a privacy-minimized
snapshot of 900 merged pull requests and 560 completed workflow runs across six public
open-source repositories.

## See it in action

[Open the public dashboard](https://engineering-intelligence-dashboard-jq9xccatzgwy9y9hcrwmor.streamlit.app/).

![MergeLens dashboard overview](docs/images/dashboard.png)

The public app was last checked on **July 28, 2026**. A fresh anonymous browser session opened it
without sign-in and showed all six repositories. This is a point-in-time check, not an uptime
guarantee. See the [publication evidence](docs/evidence/final-publication.json) and
[quality evidence](docs/quality-evidence.md).

## What you can explore

- **Delivery overview** — see how many pull requests merged, how long they typically took, the
  slower end of the distribution, and workflow success.
- **Where work slows down** — compare repositories and explore whether larger changes tend to
  spend longer waiting to merge.
- **Merge-time estimate** — enter information available when a pull request opens and compare the
  model with a simple benchmark.

These views describe repositories and past patterns. They do not explain causes or measure
individual performance.

## Run it locally

MergeLens uses Python 3.13. From a checked-out repository:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
streamlit run streamlit_app.py
```

On macOS or Linux, activate the environment with `source .venv/bin/activate`.

The included snapshot works offline; the app makes no network requests. Refreshing public GitHub
data is optional and explicit:

```powershell
python scripts/refresh_data.py
```

The refresh command accepts repeated `--repo owner/repository` values and an optional
`GITHUB_TOKEN`. It rejects private repositories and never stores or prints the token.

## Prediction model

MergeLens estimates the number of hours from opening to merge for pull requests that eventually
merge.

For pull request \(i\), the target is:

$$
Y_i =
\frac{\mathrm{merged\_at}_i-\mathrm{created\_at}_i}
     {1\ \mathrm{hour}},
\qquad Y_i \ge 0.
$$

At opening time, the model knows the repository \(r_i\), pull-request number \(n_i\), and UTC
opening time \(t_i\). It derives:

$$
X_i =
\left(
r_i,\ n_i,\ \mathrm{year}(t_i),\ \mathrm{month}(t_i),\ \mathrm{day}(t_i),\
\mathrm{weekday}(t_i),\ \mathrm{hour}(t_i)
\right).
$$

No developer identity, pull-request content, change size, merge outcome, or other future
information appears in \(X_i\).

Let \(\phi(X_i)\) represent one-hot encoding for the repository plus missing-value imputation. The
model is a 200-tree random forest trained on \(\log(1+Y_i)\):

$$
\widehat{Y}_i = f(X_i) =
\max\left(
\exp\left(
\frac{1}{200}\sum_{b=1}^{200}T_b(\phi(X_i))
\right)-1,\ 0
\right).
$$

Each \(T_b\) is one regression tree. Trees use maximum depth 8 and at least 3 training samples per
leaf.

The newest 20% (180 rows) is the chronological test set. An older row can train the model only if
its merge result was already known before the first test pull request opened; otherwise it is
excluded. Accuracy is measured on the test set with mean absolute error:

$$
\mathrm{MAE} =
\frac{1}{m}\sum_{i=1}^{m}
\left|Y_i-\widehat{Y}_i\right|.
$$

Lower MAE is better. The comparison benchmark predicts the median merge time from the training
set for every test row.

| Current snapshot result | Value |
| --- | ---: |
| Time-safe training rows | 622 |
| Chronological test rows | 180 |
| Earlier rows excluded because their outcomes were not yet known | 98 |
| Test cutoff | 2026-07-24T08:38:56+00:00 |
| Training-median estimate | 9.5 hours |
| Random-forest MAE | 9.7 hours |
| Training-median benchmark MAE | 12.5 hours |
| Comparison | Random forest, about 22% lower average error |

Results are rounded to one decimal. This one snapshot does not establish future performance, and
the estimate is not a promise or a causal explanation. See the [Model card](docs/model-card.md)
for the full training contract and [Quality evidence](docs/quality-evidence.md) for exact
environment-specific results.

## How it works

1. An explicit refresh collects public pull-request and workflow events through the GitHub REST
   API.
2. The pipeline removes identity and content fields, validates the remaining records, and stores
   local CSV and JSON files.
3. pandas calculates delivery measures, while scikit-learn trains and evaluates the merge-time
   estimate.
4. Streamlit and Plotly present the local results as filters, measures, and charts.

The application is intentionally local-first: browsing the committed snapshot requires no
credentials or network access. See [Architecture](docs/architecture.md) for the data flow and
failure boundaries.

## Trust and limits

- The recent snapshot covers six large public projects and only pull requests that eventually
  merged. It therefore has selection, survivorship, repository, and time-period bias.
- Chart patterns are descriptive. They do not prove that change size, repository, or timing
  caused a delay.
- The estimate is experimental, is not a service-level objective, and must never be used to score,
  rank, compensate, or evaluate developers.
- The committed data excludes names, logins, email addresses, avatars, titles, bodies, comments,
  revision hashes, and credentials.

See the [Data card](docs/data-card.md) and [Model card](docs/model-card.md) for the complete
boundaries.

## Project details

- [Architecture](docs/architecture.md)
- [Data card](docs/data-card.md)
- [Model card](docs/model-card.md)
- [Quality evidence](docs/quality-evidence.md)
- [Agentic development](docs/agentic-development.md)
- [Repository guardrails](AGENTS.md)

Run the same quality checks used by CI:

```powershell
python -m ruff check .
python -m ruff format --check .
python -m pytest --cov=engineering_intelligence --cov-report=term-missing --cov-fail-under=85
```

Tests use fixtures and committed local data; they make no network calls.

## License

MergeLens is available under the [MIT License](LICENSE).
````

- [ ] **Step 7: Run the documentation contract and capture GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_project_contract.py -q
```

Expected: all project-contract tests pass while the dated manifest, PR body, quality evidence,
and screenshot contracts remain unchanged.

- [ ] **Step 8: Commit the human-centered README**

```powershell
git add -- README.md tests/test_project_contract.py
git commit -m "docs: make MergeLens easier to understand"
```

---

### Task 4: Verify behavior, presentation, and repository scope

**Files:**
- Verify only: `src/engineering_intelligence/dashboard.py`
- Verify only: `src/engineering_intelligence/charts.py`
- Verify only: `README.md`
- Verify only: `tests/test_dashboard.py`
- Verify only: `tests/test_charts.py`
- Verify only: `tests/test_project_contract.py`

**Interfaces:**
- Consumes: the completed presentation commits from Tasks 1–3.
- Produces: current local evidence that the full quality gate and the two target viewport checks
  pass.

- [ ] **Step 1: Run focused presentation tests together**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_dashboard.py tests/test_charts.py tests/test_project_contract.py -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run lint and formatting checks**

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
```

Expected: both commands exit 0 without changing files.

- [ ] **Step 3: Run the complete local quality gate**

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=engineering_intelligence --cov-report=term-missing --cov-fail-under=85
```

Expected: all tests pass and total coverage is at least 85%. Report the observed count and
coverage as local evidence only.

- [ ] **Step 4: Check whitespace and scope**

```powershell
git diff --check HEAD~3..HEAD
git status --short
git diff --stat HEAD~3..HEAD
```

Expected: `git diff --check` exits 0; status is clean; the diff is limited to the six files listed
in this task.

- [ ] **Step 5: Run local visual QA at desktop and narrow widths**

Start the app without opening a visible helper window:

```powershell
$mergeLensProcess = Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "-m","streamlit","run","streamlit_app.py","--server.headless=true","--server.port=8501" -PassThru -WindowStyle Hidden
```

Using Playwright, open `http://localhost:8501`, then verify at 1280×1000 and 390×844:

- the three tabs are `Delivery overview`, `Where work slows down`, and `Merge-time estimate`;
- no `Technical stack` tab is present;
- all four delivery measures fit without horizontal page overflow;
- the P90 explanation is visible near the measures;
- the patterns caption says the charts do not prove cause;
- the forecast warning and MAE explanation are visible;
- submitting the default forecast shows one recommended estimate and one simple benchmark;
- no application traceback appears.

Stop only the process started above:

```powershell
Stop-Process -Id $mergeLensProcess.Id
```

Record the viewport observations as local verification in the handoff message. Do not edit dated
publication evidence and do not imply that the public deployment contains these changes.

- [ ] **Step 6: Review the final diff**

```powershell
git diff HEAD~3..HEAD -- src/engineering_intelligence/dashboard.py src/engineering_intelligence/charts.py README.md tests/test_dashboard.py tests/test_charts.py tests/test_project_contract.py
```

Confirm that every change is presentation or contract copy, historical evidence remains intact,
and no metric, model, snapshot, dependency, or deployment file changed.
