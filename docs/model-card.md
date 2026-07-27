# MergeLens model card

## Intended use

MergeLens provides an experimental estimate of hours from pull-request creation to merge. It is a
portfolio demonstration of an honest predictive workflow: a future holdout, a simple baseline,
visible limitations, and a strict opening-time feature boundary.

It is not a planning promise, service-level objective, causal analysis, or author/developer
performance score.

## Opening-time feature boundary

The public training and prediction interface requires only:

- `repository`
- pull-request `number`
- UTC `created_at`

From `created_at`, the model derives opening year, month, day of month, weekday, and hour. It
ignores merge outcome, merge timestamp, title/body lengths, association, labels, additions,
deletions, change size, changed files, commits, precomputed calendar columns, future outcomes,
and score-like fields. This was the explicit human decision recorded as Option 1.

## Training and evaluation

Rows are stable-sorted by UTC creation time. The oldest 80% trains the pipeline and the newest 20%
is the chronological test set. With 900 committed rows, that produces 720 training rows and 180
test rows. Evaluation never fits on test targets.

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
calculated only on the chronological test rows.

## Actual committed-snapshot results

These values were computed through `load_snapshot(Path("data/snapshots"))` followed by
`train_merge_time_model(pulls)`:

| Measure | Result |
| --- | ---: |
| Test rows | 180 |
| Random-forest MAE | 8.738738922687 hours |
| Train-median baseline MAE | 14.394064814815 hours |
| Difference | model is 5.655325892127 hours better |
| Honest result | model wins |

The model outperforms the baseline on the committed snapshot. Synthetic tests prove mechanics,
not real-world superiority.

## Interpretation and limitations

- MAE is an average absolute miss in hours; it does not show tail behavior or calibration.
- Pull-request number and calendar context may encode repository process changes but do not
  explain them. Global feature importance is non-causal.
- Random forests do not extrapolate reliably outside observed feature ranges.
- The six repositories, recent sample, and merged-only selection create substantial distribution,
  survivorship, and repository bias.
- The dashboard retrains on the selected local rows and disables evaluation below 80 rows. Filtered
  results can differ from this full-snapshot result.
- No identity field is consumed, but the output still must never be used for developer scoring,
  ranking, compensation, or individual performance decisions.

The proper response to baseline superiority is to keep the baseline visible, gather broader
representative data, and revisit the problem boundary?not to relabel the result as a model win.
