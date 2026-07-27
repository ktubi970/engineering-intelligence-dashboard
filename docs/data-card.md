# MergeLens data card

## Dataset summary and provenance

The committed demo snapshot was generated on `2026-07-27T08:04:05.882089Z` through the project's
authenticated public GitHub REST path. The token existed only in that refresh process and was not
printed or persisted.

| Item | Committed value |
| --- | --- |
| Source | GitHub public REST API |
| GitHub REST API version | `2022-11-28` |
| Public repositories | `pandas-dev/pandas`, `streamlit/streamlit` |
| Merged pull-request rows | 300 |
| Completed workflow-run rows | 199 |
| Pull creation to merge range | 2026-07-02 17:16:26 UTC to 2026-07-27 07:02:30 UTC |
| Workflow observation range | 2026-07-26 17:41:16 UTC to 2026-07-27 07:57:42 UTC |
| Schema version | 2 |

The refresh requested a limit of 150 pull requests and 150 workflow runs per repository. Pull
request collection selects merged records; workflow normalization selects completed runs. Both
collectors used the GitHub endpoint's default ordering because the refresh did not send an explicit
sort or direction. Output row counts need not equal every requested limit.

`generated_at_utc` records when the local CSV byte streams had been serialized and the manifest
was generated. It is not a server-side API cutoff or a claim that every upstream record was
unchanged at that instant.

## Snapshot manifest

`metadata.json` is an exact schema-versioned manifest. It records:

- the UTC generation timestamp and GitHub source, visibility, REST API kind, and API version;
- repository collection order, exact row counts, selection, requested limits, and ordering
  semantics for both tables; and
- lowercase SHA-256 digests of the exact bytes in `pull_requests.csv` and `workflow_runs.csv`.

The committed digests are:

| File | SHA-256 |
| --- | --- |
| `pull_requests.csv` | `044f3b9cf23651224b07d4c683738b9edc64cf0856ff3e6303ce0d7ed84bc602` |
| `workflow_runs.csv` | `f255774e67f9b17caf401f7f59d53da9a38d1cc67b536691d45368829c023af0` |

## Schema

Pull-request table:

| Field | Meaning |
| --- | --- |
| `repository`, `number` | public repository slug and repository-scoped positive PR number |
| `created_at`, `merged_at`, `merge_hours` | UTC lifecycle timestamps and recomputed positive duration |
| `title_length`, `body_length` | non-negative character counts; original free text is discarded |
| `author_association` | validated GitHub relationship category, not an author identity |
| `labels_count` | non-negative number of labels; label text is discarded |
| `additions`, `deletions`, `change_size` | non-negative change totals, with size equal to additions plus deletions |
| `changed_files`, `commits` | aggregate counts; commits is positive |
| `opened_weekday`, `opened_hour` | bounded UTC calendar values recomputed from creation time |

Workflow table:

| Field | Meaning |
| --- | --- |
| `repository`, `run_id`, `workflow_name` | public repository slug, positive repository-scoped run ID, and non-empty workflow name |
| `status`, `conclusion` | completed execution state and validated GitHub outcome |
| `created_at`, `updated_at`, `duration_minutes` | ordered UTC timestamps and recomputed non-negative duration |

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

The pipeline checks that repositories are public before collection and validates exact table
schemas, non-null values, scoped uniqueness, repository form, numeric types and ranges, enum
values, UTC timestamp ordering, and every stored derived value. It serializes both temporary CSVs,
hashes those exact bytes, creates the manifest, and replaces `metadata.json` last.

Loading validates the manifest's exact keys, types, schema/source enums, UTC timestamp, collection
settings, row counts, repository set, and both SHA-256 digests before returning revalidated
frames. A file edit is rejected even if its columns still match. Review diffs and rerun the
complete quality gate before committing refreshed data.

## Limitations and bias

- Two large Python open-source repositories are not representative of all teams, languages,
  company sizes, or delivery practices.
- Only merged pull requests are present. Abandoned, rejected, or still-open work is excluded,
  creating survivorship and selection bias.
- The requested API limit emphasizes records returned by GitHub's default order; no explicit
  sort/direction or server-side as-of cutoff was requested.
- Completed workflow runs exclude queued and in-progress work; workflow conclusions reflect each
  repository's own automation definitions.
- Public repository processes can change after the snapshot. The data is a point-in-time sample,
  not a live operational source of truth.
- Association categories and repository/process patterns can still act as indirect context. They
  must not be used to score people.
