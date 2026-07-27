# MergeLens

`engineering-intelligence-dashboard` is a tested portfolio project that turns a small,
privacy-minimized public GitHub snapshot into delivery metrics, retrospective bottleneck views,
and an honestly evaluated merge-time forecast.

## Problem

Delivery data is easy to collect and easy to overclaim. Teams need a compact way to inspect flow
without exposing developer identities, confusing correlation with causation, or presenting a
model as better than a simple baseline when it is not.

## 30-second value

Open one local Streamlit app to compare repository delivery signals, explore recent merge-time
patterns, and test an opening-time forecast. The committed demo works offline after installation:
300 merged pull requests and 199 completed workflow runs from two public repositories are already
included. The forecast is evaluated chronologically; on this snapshot, the simpler baseline wins.

## Features

- Delivery pulse: merged pull-request count, median and P90 merge time, workflow success, and
  weekly trends with shared repository/date filters.
- Bottleneck exploration: high-contrast Plotly views of change size, merge delay, and repository
  medians, labeled as retrospective and non-causal.
- Forecast and trust: an opening-time-only random-forest forecast shown beside its train-median
  baseline, test-row count, feature importance, and explicit use warning.

## Live demo

[Open the verified public Streamlit dashboard](https://engineering-intelligence-dashboard-jq9xccatzgwy9y9hcrwmor.streamlit.app/).
Anonymous verification on 2026-07-27 confirmed that the initial published revision `f987033`
loaded the committed snapshot with 300 merged pull requests and no visible traceback.

The initial GitHub Actions quality check [passed in 57s](https://github.com/ktubi970/engineering-intelligence-dashboard/actions/runs/30259194189/job/89954838617)
on `f987033`. That hosted result is scoped to the initial published revision; the local test results
below cover the documentation and tab-label changes in this evidence commit.

![MergeLens dashboard overview](docs/images/dashboard.png)

The screenshot is a genuine 1440x1000 capture from the locally running application.

## Metric definitions

- **Merged pull requests:** rows with a positive duration from UTC creation to UTC merge time.
- **Median merge time:** the middle `merge_hours` value; **P90 merge time** is the 90th percentile
  using linear interpolation.
- **Average weekly throughput:** the mean merged-PR count across observed UTC Monday-based weekly
  buckets.
- **Workflow success:** successful conclusions divided by completed workflow runs with a recorded
  conclusion.
- **MAE:** mean absolute error in hours on the newest chronological test rows. Lower is better.

## Architecture

GitHub collection is separate from the offline app: public API responses are normalized with
pandas, written as validated local CSV/JSON snapshot files, then loaded by metrics, model, Plotly,
and Streamlit layers. See [Architecture](docs/architecture.md) for the flow, contracts,
dependencies, and failure modes.

## Installation

Python 3.13 is the CI runtime. From a checked-out repository:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

On macOS or Linux, activate with `source .venv/bin/activate`.

## Offline demo

The app reads only `data/snapshots` by default and makes no network request:

```powershell
streamlit run streamlit_app.py
```

Use the sidebar to filter repositories and an inclusive UTC date range. The forecast remains
available only when at least 80 pull-request rows are selected.

## Optional data refresh

Refreshing is explicit and is the only normal path that calls GitHub. It accepts public
`owner/repository` slugs, rejects private repositories before collection, and can use an optional
`GITHUB_TOKEN` environment variable without storing or printing it.

```powershell
python scripts/refresh_data.py
```

Use `--repo owner/repository` repeatedly and `--limit-per-repo N` to choose sources and bounds.
Review generated data before committing it.

## Tests

The local and CI quality contract is:

```powershell
python -m ruff check .
python -m ruff format --check .
python -m pytest --cov=engineering_intelligence --cov-report=term-missing --cov-fail-under=85
```

Tests use fixtures or committed local data and make no network calls. Exact current local results
are recorded in [Quality evidence](docs/quality-evidence.md); a workflow definition is not itself
proof that GitHub Actions has passed.

## Model results

The committed 300-row pull-request snapshot is sorted by `created_at`; the oldest 80% trains the
model and the newest 20% (60 rows) is held out for evaluation.

- Random-forest MAE: **26.624744394610 hours**
- Training-median baseline MAE: **21.071861111111 hours**
- Winner: **baseline**, by **5.552883283499 hours**

The model underperforms the baseline on this snapshot. That result is not hidden or reframed.
Inputs are only repository, pull-request number, and UTC calendar features derived from creation
time. This is an experimental, non-causal estimate and never a developer score. See the
[Model card](docs/model-card.md).

## Limitations

The snapshot is recent, point-in-time, and limited to two public open-source repositories. It
contains merged pull requests rather than every opened pull request, so it has selection and
survivorship bias. Repository process changes and future data may shift results. Feature
importance and the size/delay plot describe patterns; neither identifies causes.

## Privacy

The committed snapshot excludes developer names, logins, email addresses, avatars, pull titles,
pull bodies, comments, revision hashes, and credentials. It keeps public repository slugs,
repository-scoped numeric identifiers, aggregate lengths/counts, timestamps, status categories,
and a non-identifying author-association category. See the [Data card](docs/data-card.md).

## License

MergeLens is available under the [MIT License](LICENSE).
