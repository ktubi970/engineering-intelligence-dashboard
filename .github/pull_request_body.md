# MergeLens engineering intelligence dashboard

## Verified summary

- Loads offline from the committed, privacy-minimized snapshot.
- Deployment URL: https://engineering-intelligence-dashboard-jq9xccatzgwy9y9hcrwmor.streamlit.app/
  On 2026-07-28, a fresh anonymous browser session opened it without sign-in, loaded 900 merged
  pull requests from all six repositories, and rendered `Overview`,
  `Drivers & retrospective patterns`, `Forecast & trust`, and `Technical stack`.
- The interactive forecast returned a visible estimate. The model panel showed 9.7 hours MAE
  versus 12.5 hours for the baseline, with no application traceback or horizontal overflow at
  the tested desktop and narrow viewports.
- GitHub Actions passed lint, format, and **173 passed** with **94.68%** coverage:
  https://github.com/ktubi970/engineering-intelligence-dashboard/actions/runs/30346530403
  on merged-master commit `a051ffe5198506a79f9be66112320cac47d0de3f`.
- Machine-readable source: `docs/evidence/final-publication.json`.

## Local quality commands

```powershell
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
.venv\Scripts\python.exe -m pytest --cov=engineering_intelligence --cov-report=term-missing --cov-fail-under=85
```

The final pre-merge local gate ran on Windows with Python 3.13.9 at commit
`abaebd6115685e049dcad37599709a67f9ec2647`. Ruff lint passed, Ruff format reported
33 files already formatted, pytest reported 173 passed with 94.68% coverage, and
`git diff --check` completed without output.

## Public data provenance

The current committed snapshot contains 900 merged pull requests and 560 completed workflow runs
from `pandas-dev/pandas`, `streamlit/streamlit`, `microsoft/vscode`, `tensorflow/tensorflow`,
`rust-lang/rust`, and `ruby/ruby`. It was produced from the GitHub public REST API and stores
repository-scoped delivery fields rather than developer identities or credentials.

## Honest model result

- As-of cutoff: 2026-07-24T08:38:56+00:00
- Time-safe training rows: 622
- Chronological test rows: 180
- Purged unavailable labels: 98
- Training-median estimate: 9.463611111111 hours
- Random-forest MAE: 9.7 hours (rounded)
- Training-median baseline MAE: 12.5 hours (rounded)
- Winner: random forest, with about 22% lower MAE

The random forest has lower MAE than the baseline on this fixed snapshot. Both estimates remain
visible because one holdout does not establish future superiority. The displayed target is
estimated merge time among pull requests that eventually merge. The forecast is experimental,
non-causal, and never a developer performance score.

Public model-quality values are rounded to one decimal because exact tree-ensemble results can
vary slightly across execution environments even with the same direct dependency pins and a fixed
seed. The observed Windows/Linux difference does not isolate a single causal factor. Exact
environment-specific outputs remain in `docs/quality-evidence.md`.

## Screenshot

![MergeLens dashboard overview](https://github.com/ktubi970/engineering-intelligence-dashboard/blob/b9e4db677d6d29d0354061d9b86fdc8033a490a9/docs/images/dashboard.png?raw=true)

The screenshot is a genuine 1440x1000 viewport capture (PNG, 91,844 bytes) from the local running
application after restoring all six repositories and the full date range.

## Limitations

- The public deployment was verified anonymously on 2026-07-28 against the same application tree
  merged into `master`. This point-in-time check is not an uptime guarantee.
- Streamlit was configured to `codex/engineering-intelligence-dashboard` at
  `abaebd6115685e049dcad37599709a67f9ec2647` during verification. The committed screenshot remains
  local evidence; the fresh anonymous browser session is the source for the public-deployment
  claims.
- Initial PR: https://github.com/ktubi970/engineering-intelligence-dashboard/pull/1
- The current point-in-time snapshot covers six public repositories and only merged pull requests,
  so it includes selection and survivorship bias.
- The fixed chronological holdout is one local evaluation; repository or time-window changes can
  change which estimate wins.
- Retrospective patterns and feature importance describe associations, not causes.
- Future repository process or data changes can shift metrics and forecast error.
