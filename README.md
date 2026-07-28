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

MergeLens estimates the number of hours from opening to merge for pull requests that eventually merge.

For pull request $i$, the target is simply its merge time, measured in hours:

$$
Y_i = \text{time from opening to merge for pull request } i,
\qquad Y_i \ge 0.
$$

For example, if a pull request merges 9 hours and 30 minutes after it opens, then $Y_i = 9.5$.

At opening time, the model knows the repository $r_i$, pull-request number $n_i$, and UTC
opening time $t_i$. It derives:

$$
X_i =
\left(
r_i,\ n_i,\ \mathrm{year}(t_i),\ \mathrm{month}(t_i),\ \mathrm{day}(t_i),\
\mathrm{weekday}(t_i),\ \mathrm{hour}(t_i)
\right).
$$

No developer identity, pull-request content, change size, merge outcome, or other future
information appears in $X_i$.

Let $\phi(X_i)$ represent one-hot encoding for the repository plus missing-value imputation. The
model is a 200-tree random forest trained on $\log(1+Y_i)$:

$$
\widehat{Y}_i = f(X_i) =
\max\left(
\exp\left(
\frac{1}{200}\sum_{b=1}^{200}T_b(\phi(X_i))
\right)-1,\ 0
\right).
$$

Each $T_b$ is one regression tree. Trees use maximum depth 8 and at least 3 training samples per leaf.

The newest 20% (180 rows) is the chronological test set. An older row can train the model only if
its merge result was already known before the first test pull request opened; otherwise it is
excluded. Accuracy is measured on the test set with mean absolute error:

$$
\mathrm{MAE} =
\frac{1}{m}\sum_{i=1}^{m}
\left|Y_i-\widehat{Y}_i\right|.
$$

Lower MAE is better. The comparison benchmark predicts the median merge time from the training set for every test row.

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
