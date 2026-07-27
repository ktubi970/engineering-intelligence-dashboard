# MergeLens data card

## Dataset summary and provenance

The committed demo snapshot was generated on `2026-07-27T08:04:05.882089Z` through the project's
authenticated public GitHub REST path. The token existed only in that refresh process and was not
printed or persisted.

| Item | Committed value |
| --- | --- |
| Source | GitHub public REST API |
| Public repositories | `pandas-dev/pandas`, `streamlit/streamlit` |
| Merged pull-request rows | 300 |
| Completed workflow-run rows | 199 |
| Pull creation to merge range | 2026-07-02 17:16:26 UTC to 2026-07-27 07:02:30 UTC |
| Workflow observation range | 2026-07-26 17:41:16 UTC to 2026-07-27 07:57:42 UTC |
| Schema version | 1 |

The refresh bound was 150 pull requests and 150 workflow runs per repository. Only merged pull
requests and completed workflow runs survive normalization, so output row counts need not match
every requested limit.

## Schema

Pull-request table:

| Field | Meaning |
| --- | --- |
| `repository`, `number` | public repository slug and repository-scoped PR number |
| `created_at`, `merged_at`, `merge_hours` | UTC lifecycle timestamps and derived positive duration |
| `title_length`, `body_length` | character counts; original free text is discarded |
| `author_association` | GitHub relationship category, not an author identity |
| `labels_count` | number of labels; label text is discarded |
| `additions`, `deletions`, `change_size` | numeric change totals, with size equal to additions plus deletions |
| `changed_files`, `commits` | aggregate counts |
| `opened_weekday`, `opened_hour` | UTC calendar values derived from creation time |

Workflow table:

| Field | Meaning |
| --- | --- |
| `repository`, `run_id`, `workflow_name` | public repository slug, repository-scoped run ID, workflow name |
| `status`, `conclusion` | completed execution state and outcome |
| `created_at`, `updated_at`, `duration_minutes` | UTC timestamps and non-negative derived duration |

Metadata contains only schema version, UTC generation time, source label, repositories, and exact
row counts for both tables.

## Privacy

Normalization uses exact allowlists. The committed files do not store developer names, logins,
emails, avatars, pull titles or bodies, comments, label text, revision hashes, authentication
headers, tokens, or private-repository flags. Public repository slugs, workflow names, numeric
identifiers, timestamps, counts, statuses, and the author-association category remain because the
product needs repository-level analysis. This is privacy minimization, not anonymization.

## Refresh and validation

The offline dashboard reads the committed files and does not refresh automatically. An explicit
refresh uses:

```powershell
python scripts/refresh_data.py
```

The pipeline checks that repositories are public before collection, validates exact schemas,
non-null values, scoped uniqueness, UTC timestamps, and valid durations, then writes the three
snapshot files. Review diffs and rerun the complete quality gate before committing refreshed data.

## Limitations and bias

- Two large Python open-source repositories are not representative of all teams, languages,
  company sizes, or delivery practices.
- Only merged pull requests are present. Abandoned, rejected, or still-open work is excluded,
  creating survivorship and selection bias.
- The API limit emphasizes recent records and the two data types cover different time windows.
- Completed workflow runs exclude queued and in-progress work; workflow conclusions reflect each
  repository's own automation definitions.
- Public repository processes can change after the snapshot. The data is a point-in-time sample,
  not a live operational source of truth.
- Association categories and repository/process patterns can still act as indirect context. They
  must not be used to score people.
