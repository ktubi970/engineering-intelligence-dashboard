import csv
import hashlib
import json
from pathlib import Path

import pytest
from conftest import FakeGitHubClient

from engineering_intelligence.domain import DataContractError, RepositoryRef
from engineering_intelligence.pipeline import load_snapshot, refresh_snapshot
from engineering_intelligence.transform import PULL_REQUEST_COLUMNS, WORKFLOW_COLUMNS


def _manifest_for_snapshot(
    data_dir: Path,
    *,
    repositories: list[str] | None = None,
    pull_request_rows: int = 2,
    workflow_run_rows: int = 2,
    limit_per_repository: int = 2,
) -> dict[str, object]:
    return {
        "schema_version": 2,
        "generated_at_utc": "2026-07-27T08:04:05.882089Z",
        "source": {
            "provider": "github",
            "visibility": "public",
            "api": "rest",
            "api_version": "2022-11-28",
        },
        "repositories": (repositories if repositories is not None else ["pandas-dev/pandas"]),
        "row_counts": {
            "pull_requests": pull_request_rows,
            "workflow_runs": workflow_run_rows,
        },
        "collection": {
            "pull_requests": {
                "selection": "merged",
                "limit_per_repository": limit_per_repository,
                "order": "api_default",
            },
            "workflow_runs": {
                "selection": "completed",
                "limit_per_repository": limit_per_repository,
                "order": "api_default",
            },
        },
        "files": {
            filename: {
                "sha256": hashlib.sha256((data_dir / filename).read_bytes()).hexdigest(),
            }
            for filename in ("pull_requests.csv", "workflow_runs.csv")
        },
    }


def _write_manifest(data_dir: Path, manifest: dict[str, object]) -> None:
    (data_dir / "metadata.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )


def _replace_first_csv_value(
    data_dir: Path,
    filename: str,
    column: str,
    value: str,
) -> None:
    path = data_dir / filename
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames
    assert rows
    assert fieldnames is not None
    rows[0][column] = value
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


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
    assert len(workflows) == metadata.workflow_run_rows == 2
    assert pulls["change_size"].tolist() == [140, 40]
    assert list(pulls.columns) == list(PULL_REQUEST_COLUMNS)
    assert list(workflows.columns) == list(WORKFLOW_COLUMNS)
    expected_metadata = _manifest_for_snapshot(tmp_path)
    expected_metadata["generated_at_utc"] = metadata.generated_at_utc
    assert stored_metadata == expected_metadata
    assert metadata.generated_at_utc.endswith("Z")
    assert {path.name for path in tmp_path.iterdir()} == {
        "pull_requests.csv",
        "workflow_runs.csv",
        "metadata.json",
    }


def test_refresh_snapshot_rejects_private_repository_before_collection(
    tmp_path: Path,
    fake_github_client: FakeGitHubClient,
) -> None:
    fake_github_client.repository_metadata = {
        "id": 42,
        "full_name": "private-owner/private-repository",
        "private": True,
    }

    with pytest.raises(DataContractError, match="must be public"):
        refresh_snapshot(
            fake_github_client,
            [RepositoryRef.parse("private-owner/private-repository")],
            tmp_path,
            pr_limit=2,
        )

    assert fake_github_client.collection_requests == []
    assert list(tmp_path.iterdir()) == []


def test_snapshot_files_never_persist_private_or_free_text(
    tmp_path: Path,
    fake_github_client: FakeGitHubClient,
) -> None:
    refresh_snapshot(
        fake_github_client,
        [RepositoryRef.parse("pandas-dev/pandas")],
        tmp_path,
        pr_limit=2,
    )

    persisted = "\n".join(path.read_text(encoding="utf-8") for path in tmp_path.iterdir())
    for private_value in (
        "sanitized-user",
        "second-private-login",
        "second-private@example.invalid",
        "https://example.invalid/avatar",
        "https://example.invalid/second-avatar",
        "1111111111111111111111111111111111111111",
        "second-private-head-sha",
        "Improve merge metrics",
        "Ship fixtures safely",
        "Adds a public merge-time summary.",
        "No identity persists.",
    ):
        assert private_value not in persisted


def test_refresh_snapshot_validates_before_replacing_final_files(
    tmp_path: Path,
    fake_github_client: FakeGitHubClient,
) -> None:
    sentinel_files = {
        "pull_requests.csv": "old pulls",
        "workflow_runs.csv": "old workflows",
        "metadata.json": "old metadata",
    }
    for filename, contents in sentinel_files.items():
        (tmp_path / filename).write_text(contents, encoding="utf-8")
    fake_github_client.pull_details[99] = {
        **fake_github_client.pull_details[99],
        "number": 101,
    }

    with pytest.raises(DataContractError, match="duplicate"):
        refresh_snapshot(
            fake_github_client,
            [RepositoryRef.parse("pandas-dev/pandas")],
            tmp_path,
            pr_limit=2,
        )

    assert {
        filename: (tmp_path / filename).read_text(encoding="utf-8") for filename in sentinel_files
    } == sentinel_files
    assert list(tmp_path.glob("*.tmp")) == []


def test_load_snapshot_rejects_tampered_schema(
    tmp_path: Path,
    fake_github_client: FakeGitHubClient,
) -> None:
    refresh_snapshot(
        fake_github_client,
        [RepositoryRef.parse("pandas-dev/pandas")],
        tmp_path,
        pr_limit=2,
    )
    pull_path = tmp_path / "pull_requests.csv"
    rows = pull_path.read_text(encoding="utf-8").splitlines()
    rows[0] += ",author_login"
    rows[1:] = [f"{row},private-login" for row in rows[1:]]
    pull_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    _write_manifest(tmp_path, _manifest_for_snapshot(tmp_path))

    with pytest.raises(DataContractError, match="exact columns"):
        load_snapshot(tmp_path)


def test_load_snapshot_rejects_corrupt_content_hash(
    tmp_path: Path,
    fake_github_client: FakeGitHubClient,
) -> None:
    refresh_snapshot(
        fake_github_client,
        [RepositoryRef.parse("pandas-dev/pandas")],
        tmp_path,
        pr_limit=2,
    )
    manifest = _manifest_for_snapshot(tmp_path)
    manifest["files"]["pull_requests.csv"]["sha256"] = "0" * 64
    _write_manifest(tmp_path, manifest)

    with pytest.raises(DataContractError, match="SHA-256"):
        load_snapshot(tmp_path)


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("extra key", "exact keys"),
        ("missing key", "exact keys"),
        ("schema version", "schema_version"),
        ("schema type", "schema_version"),
        ("generated time", "generated_at_utc"),
        ("source type", "source"),
        ("source enum", "source.visibility"),
        ("repositories", "repositories"),
        ("row count", "row_counts.pull_requests"),
        ("selection enum", "collection.pull_requests.selection"),
        ("order enum", "collection.workflow_runs.order"),
        ("limit range", "collection.workflow_runs.limit_per_repository"),
    ],
)
def test_load_snapshot_rejects_invalid_manifest(
    tmp_path: Path,
    fake_github_client: FakeGitHubClient,
    case: str,
    message: str,
) -> None:
    refresh_snapshot(
        fake_github_client,
        [RepositoryRef.parse("pandas-dev/pandas")],
        tmp_path,
        pr_limit=2,
    )
    manifest = _manifest_for_snapshot(tmp_path)
    if case == "extra key":
        manifest["unexpected"] = True
    elif case == "missing key":
        manifest.pop("files")
    elif case == "schema version":
        manifest["schema_version"] = 1
    elif case == "schema type":
        manifest["schema_version"] = True
    elif case == "generated time":
        manifest["generated_at_utc"] = "2026-07-27T10:04:05+02:00"
    elif case == "source type":
        manifest["source"] = "GitHub public REST API"
    elif case == "source enum":
        manifest["source"] = {
            "provider": "github",
            "visibility": "private",
            "api": "rest",
            "api_version": "2022-11-28",
        }
    elif case == "repositories":
        manifest["repositories"] = ["other/repository"]
    elif case == "row count":
        manifest["row_counts"] = {
            "pull_requests": 3,
            "workflow_runs": 2,
        }
    elif case == "selection enum":
        manifest["collection"] = {
            "pull_requests": {
                "selection": "closed",
                "limit_per_repository": 2,
                "order": "api_default",
            },
            "workflow_runs": {
                "selection": "completed",
                "limit_per_repository": 2,
                "order": "api_default",
            },
        }
    elif case == "order enum":
        manifest["collection"] = {
            "pull_requests": {
                "selection": "merged",
                "limit_per_repository": 2,
                "order": "api_default",
            },
            "workflow_runs": {
                "selection": "completed",
                "limit_per_repository": 2,
                "order": "created_desc",
            },
        }
    else:
        assert case == "limit range"
        manifest["collection"] = {
            "pull_requests": {
                "selection": "merged",
                "limit_per_repository": 2,
                "order": "api_default",
            },
            "workflow_runs": {
                "selection": "completed",
                "limit_per_repository": 0,
                "order": "api_default",
            },
        }
    _write_manifest(tmp_path, manifest)

    with pytest.raises(DataContractError, match=message):
        load_snapshot(tmp_path)


@pytest.mark.parametrize(
    ("filename", "column", "value", "message"),
    [
        ("pull_requests.csv", "merge_hours", "49.0", "merge_hours"),
        (
            "pull_requests.csv",
            "merged_at",
            "2025-12-31T10:00:00Z",
            "merged_at",
        ),
        ("pull_requests.csv", "change_size", "141", "change_size"),
        ("pull_requests.csv", "opened_hour", "24", "opened_hour"),
        ("workflow_runs.csv", "duration_minutes", "13.0", "duration_minutes"),
        ("workflow_runs.csv", "status", "queued", "status"),
    ],
)
def test_load_snapshot_rejects_schema_correct_tampering(
    tmp_path: Path,
    fake_github_client: FakeGitHubClient,
    filename: str,
    column: str,
    value: str,
    message: str,
) -> None:
    refresh_snapshot(
        fake_github_client,
        [RepositoryRef.parse("pandas-dev/pandas")],
        tmp_path,
        pr_limit=2,
    )
    _replace_first_csv_value(tmp_path, filename, column, value)
    _write_manifest(tmp_path, _manifest_for_snapshot(tmp_path))

    with pytest.raises(DataContractError, match=message):
        load_snapshot(tmp_path)


def test_metadata_json_contains_only_documented_provenance_keys(
    tmp_path: Path,
    fake_github_client: FakeGitHubClient,
) -> None:
    refresh_snapshot(
        fake_github_client,
        [RepositoryRef.parse("pandas-dev/pandas")],
        tmp_path,
        pr_limit=1,
    )

    metadata = json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8"))
    assert list(metadata) == [
        "schema_version",
        "generated_at_utc",
        "source",
        "repositories",
        "row_counts",
        "collection",
        "files",
    ]


def test_committed_snapshot_meets_portfolio_contract() -> None:
    pulls, workflows, metadata = load_snapshot(Path("data/snapshots"))
    assert len(pulls) >= 300
    assert pulls["repository"].nunique() >= 2
    assert len(workflows) > 0
    assert metadata["row_counts"] == {
        "pull_requests": len(pulls),
        "workflow_runs": len(workflows),
    }
    assert list(pulls.columns) == [
        "repository",
        "number",
        "created_at",
        "merged_at",
        "merge_hours",
        "title_length",
        "body_length",
        "author_association",
        "labels_count",
        "additions",
        "deletions",
        "change_size",
        "changed_files",
        "commits",
        "opened_weekday",
        "opened_hour",
    ]
    assert list(workflows.columns) == [
        "repository",
        "run_id",
        "workflow_name",
        "status",
        "conclusion",
        "created_at",
        "updated_at",
        "duration_minutes",
    ]


def test_load_snapshot_compares_repository_sets_independent_of_row_order(
    tmp_path: Path,
    fake_github_client: FakeGitHubClient,
) -> None:
    repositories = [
        RepositoryRef.parse("pandas-dev/pandas"),
        RepositoryRef.parse("streamlit/streamlit"),
    ]
    refresh_snapshot(
        fake_github_client,
        repositories,
        tmp_path,
        pr_limit=2,
    )

    pull_path = tmp_path / "pull_requests.csv"
    with pull_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames
    assert fieldnames is not None
    rows.reverse()
    with pull_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    _write_manifest(
        tmp_path,
        _manifest_for_snapshot(
            tmp_path,
            repositories=["pandas-dev/pandas", "streamlit/streamlit"],
            pull_request_rows=4,
            workflow_run_rows=4,
            limit_per_repository=2,
        ),
    )

    pulls, workflows, metadata = load_snapshot(tmp_path)

    assert len(pulls) == len(workflows) == 4
