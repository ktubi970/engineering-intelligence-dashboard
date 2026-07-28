# MergeLens model card

## Intended use

MergeLens provides an experimental estimate of hours from pull-request creation to merge among
pull requests that eventually merge. It is a portfolio demonstration of an honest predictive
workflow: a time-safe future holdout, a simple baseline, visible limitations, and a strict
opening-time feature boundary.

It is not a planning promise, service-level objective, causal analysis, or author/developer
performance score.

## Opening-time feature boundary

The predictive feature interface requires only:

- `repository`
- pull-request `number`
- UTC `created_at`

From `created_at`, the model derives opening year, month, day of month, weekday, and hour. It
does not fit on merge outcome, merge timestamp, title/body lengths, association, labels,
additions, deletions, change size, changed files, commits, precomputed calendar columns, future
outcomes, or score-like fields. Training additionally uses `merge_hours` as the target and
`merged_at` only to establish whether that target was available at the evaluation cutoff; neither
is a predictive feature. This preserves the explicit human decision recorded as Option 1.

## Training and evaluation

Rows are stable-sorted by UTC creation time. The newest 20% is the fixed chronological test
candidate set, and its earliest `created_at` is the as-of cutoff. An earlier candidate can train
the pipeline only when its `merged_at` is strictly before that cutoff.
With 300 committed rows, that produces 240 earlier candidates and 60 chronological test rows.
At the fixed cutoff, 17 unavailable labels are purged, leaving 223 training rows.

The resulting boundary is checked directly: maximum training `merged_at` is earlier than the
cutoff, which is at or before minimum test `created_at`. Evaluation never fits on test targets.

The target is `merge_hours`. Training applies `log1p` to the target; prediction applies `expm1`
and clamps values to zero or above. Numeric values use median imputation. Repository uses
most-frequent imputation and one-hot encoding with unknown repositories ignored.

The estimator is:

```text
RandomForestRegressor(
    n_estimators=200,
    max_depth=8,
    min_samples_leaf=3,
    random_state=42,
    n_jobs=-1,
)
```

The comparison baseline predicts the training-set median merge time for every test row. MAE is
calculated only on the chronological test rows. The displayed target is
estimated merge time among pull requests that eventually merge.

## Actual committed-snapshot results

These values were computed through `load_snapshot(Path("data/snapshots"))` followed by
`train_merge_time_model(pulls)`:

| Measure | Result |
| --- | ---: |
| As-of cutoff | 2026-07-20T18:48:28+00:00 |
| Training rows | 223 |
| Test rows | 60 |
| Purged unavailable labels | 17 |
| Training-median estimate | 18.235 hours |
| Random-forest MAE | 17.499891193309 hours |
| Train-median baseline MAE | 20.535763888889 hours |
| Difference | model is 3.035872695580 hours better |
| Honest result | random forest wins |

The random forest has lower MAE on this fixed committed-snapshot holdout. That is local evidence
for this split, not a claim of real-world or future superiority. Synthetic tests prove mechanics,
not general model quality.

## Interpretation and limitations

- MAE is an average absolute miss in hours; it does not show tail behavior or calibration.
- Pull-request number and calendar context may encode repository process changes but do not
  explain them. Global feature importance is non-causal.
- Random forests do not extrapolate reliably outside observed feature ranges.
- The two repositories, recent sample, and merged-only selection create substantial distribution,
  survivorship, and repository bias.
- The dashboard retrains on the selected local rows and disables evaluation below 80 rows. Filtered
  results can differ from this full-snapshot result.
- No identity field is consumed, but the output still must never be used for developer scoring,
  ranking, compensation, or individual performance decisions.

The baseline remains visible even though the random forest wins this holdout. Broader
representative data and repeated future evaluation are still required; one split must not be
generalized into a planning guarantee.
