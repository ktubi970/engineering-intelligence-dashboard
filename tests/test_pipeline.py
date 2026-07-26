import json
from pathlib import Path

import pytest
from conftest import FakeGitHubClient

from engineering_intelligence.domain import DataContractError, RepositoryRef
from engineering_intelligence.pipeline import load_snapshot, refresh_snapshot
from engineering_intelligence.transform import PULL_REQUEST_COLUMNS, WORKFLOW_COLUMNS


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
    assert stored_metadata == {
        "schema_version": 1,
        "generated_at_utc": metadata.generated_at_utc,
        "source": "GitHub public REST API",
        "repositories": ["pandas-dev/pandas"],
        "pull_request_rows": 2,
        "workflow_run_rows": 2,
    }
    assert metadata.generated_at_utc.endswith("Z")
    assert {path.name for path in tmp_path.iterdir()} == {
        "pull_requests.csv",
        "workflow_runs.csv",
        "metadata.json",
    }


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

    with pytest.raises(DataContractError, match="exact columns"):
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
        "pull_request_rows",
        "workflow_run_rows",
    ]
