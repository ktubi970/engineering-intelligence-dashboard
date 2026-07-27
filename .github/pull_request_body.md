# MergeLens engineering intelligence dashboard

## Verified summary

- Loads offline from the committed, privacy-minimized snapshot.
- Live demo: https://engineering-intelligence-dashboard-jq9xccatzgwy9y9hcrwmor.streamlit.app/
- The initial deployment on `f987033` anonymously loaded 300 merged pull requests with no visible
  traceback; its deployed tabs were Delivery pulse, Bottlenecks, and Forecast & trust.
- This branch locally presents Overview, Drivers & retrospective patterns, and Forecast & trust.
- Repository/date filters, readable empty states, Plotly hover, forecast safeguards, and desktop
  and narrow overflow behavior were exercised in a real local Playwright browser.
- The local browser console reported 0 errors after the required interactions.
- The initial GitHub Actions quality check passed in 57s on `f987033`:
  https://github.com/ktubi970/engineering-intelligence-dashboard/actions/runs/30259194189/job/89954838617

## Local quality commands

```powershell
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
.venv\Scripts\python.exe -m pytest --cov=engineering_intelligence --cov-report=term-missing --cov-fail-under=85
```

Earlier local results on Python 3.13.9 recorded Ruff lint passing, Ruff format reporting 31 files
already formatted, and pytest passing 96 tests with 96.10% coverage (85% required). That evidence
predates the time-safe evaluation correction; the coordinator must record a fresh integrated gate
after the concurrent scopes are combined.

## Public data provenance

The committed snapshot contains 300 merged pull requests and 199 completed workflow runs from
`pandas-dev/pandas` and `streamlit/streamlit`. It was produced from the GitHub public REST API and
stores repository-scoped delivery fields rather than developer identities or credentials.

## Honest model result

- As-of cutoff: 2026-07-20T18:48:28+00:00
- Time-safe training rows: 223
- Chronological test rows: 60
- Purged unavailable labels: 17
- Training-median estimate: 18.235 hours
- Random-forest MAE: 17.499891193309 hours
- Training-median baseline MAE: 20.535763888889 hours
- Winner: random forest, by 3.035872695580 hours

The random forest has lower MAE than the baseline on this fixed snapshot. Both estimates remain
visible because one holdout does not establish future superiority. The displayed target is
estimated merge time among pull requests that eventually merge. The forecast is experimental,
non-causal, and never a developer performance score.

## Screenshot

![MergeLens dashboard overview](https://github.com/ktubi970/engineering-intelligence-dashboard/blob/ce303f2a4b5d81e98a478ec542542698e0f991b1/docs/images/dashboard.png?raw=true)

The screenshot is a genuine 1440x1000 viewport capture from the local running application after
restoring both repositories and the full date range.

## Limitations

- Remote browser and CI evidence is scoped to initial SHA `f987033`. Its deployed first two tab
  labels differ from the locally verified branch labels recorded above.
- The anonymous Streamlit shell logged account/API 403/404 responses while the application iframe
  loaded normally with no visible traceback and no horizontal iframe overflow.
- Initial PR: https://github.com/ktubi970/engineering-intelligence-dashboard/pull/1
- The recent point-in-time snapshot covers two public repositories and only merged pull requests,
  so it includes selection and survivorship bias.
- The fixed chronological holdout is one local evaluation; repository or time-window changes can
  change which estimate wins.
- Retrospective patterns and feature importance describe associations, not causes.
- Future repository process or data changes can shift metrics and forecast error.
