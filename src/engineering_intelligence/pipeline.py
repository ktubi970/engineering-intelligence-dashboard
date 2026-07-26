import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

import pandas as pd

from engineering_intelligence.domain import DataContractError, RepositoryRef
from engineering_intelligence.transform import (
    PULL_REQUEST_COLUMNS,
    WORKFLOW_COLUMNS,
    normalize_pull_requests,
    normalize_workflow_runs,
    validate_pull_request_frame,
    validate_workflow_frame,
)

PULL_REQUEST_FILENAME = "pull_requests.csv"
WORKFLOW_FILENAME = "workflow_runs.csv"
METADATA_FILENAME = "metadata.json"
SCHEMA_VERSION = 1
SOURCE = "GitHub public REST API"


class GitHubDataSource(Protocol):
    def get_repository(self, repository: RepositoryRef) -> dict[str, object]: ...

    def list_merged_pull_requests(
        self,
        repository: RepositoryRef,
        limit: int,
    ) -> list[dict[str, object]]: ...

    def get_pull_request(
        self,
        repository: RepositoryRef,
        number: int,
    ) -> dict[str, object]: ...

    def list_workflow_runs(
        self,
        repository: RepositoryRef,
        limit: int,
    ) -> list[dict[str, object]]: ...


@dataclass(frozen=True, slots=True)
class SnapshotMetadata:
    schema_version: int
    generated_at_utc: str
    source: str
    repositories: list[str]
    pull_request_rows: int
    workflow_run_rows: int


def refresh_snapshot(
    client: GitHubDataSource,
    repositories: Sequence[RepositoryRef],
    output_dir: Path,
    pr_limit: int = 150,
) -> SnapshotMetadata:
    pull_frames: list[pd.DataFrame] = []
    workflow_frames: list[pd.DataFrame] = []
    for repository in repositories:
        metadata = client.get_repository(repository)
        if metadata.get("private") is not False:
            raise DataContractError(f"Repository {repository.slug} must be public.")

        summaries = client.list_merged_pull_requests(repository, pr_limit)
        details = [
            client.get_pull_request(repository, _pull_number(summary)) for summary in summaries
        ]
        pull_frames.append(normalize_pull_requests(details, repository.slug))
        workflow_frames.append(
            normalize_workflow_runs(
                client.list_workflow_runs(repository, pr_limit),
                repository.slug,
            )
        )

    pulls = _combine_frames(
        pull_frames,
        PULL_REQUEST_COLUMNS,
        ("created_at", "merged_at"),
    )
    workflows = _combine_frames(
        workflow_frames,
        WORKFLOW_COLUMNS,
        ("created_at", "updated_at"),
    )
    validate_pull_request_frame(pulls)
    validate_workflow_frame(workflows)

    metadata = SnapshotMetadata(
        schema_version=SCHEMA_VERSION,
        generated_at_utc=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        source=SOURCE,
        repositories=[repository.slug for repository in repositories],
        pull_request_rows=len(pulls),
        workflow_run_rows=len(workflows),
    )
    _write_snapshot_atomically(output_dir, pulls, workflows, metadata)
    return metadata


def load_snapshot(
    data_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    pulls = pd.read_csv(data_dir / PULL_REQUEST_FILENAME)
    workflows = pd.read_csv(data_dir / WORKFLOW_FILENAME)
    for column in ("created_at", "merged_at"):
        pulls[column] = pd.to_datetime(pulls[column], utc=True)
    for column in ("created_at", "updated_at"):
        workflows[column] = pd.to_datetime(workflows[column], utc=True)
    validate_pull_request_frame(pulls)
    validate_workflow_frame(workflows)

    metadata = json.loads((data_dir / METADATA_FILENAME).read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        raise DataContractError("Snapshot metadata must be a JSON object.")
    return pulls, workflows, metadata


def _pull_number(summary: dict[str, object]) -> int:
    number = summary.get("number")
    if not isinstance(number, int):
        raise DataContractError("Pull request summary must contain an integer number.")
    return number


def _combine_frames(
    frames: list[pd.DataFrame],
    columns: tuple[str, ...],
    timestamp_columns: tuple[str, ...],
) -> pd.DataFrame:
    if frames:
        return pd.concat(frames, ignore_index=True)
    frame = pd.DataFrame(columns=columns)
    for column in timestamp_columns:
        frame[column] = pd.to_datetime(frame[column], utc=True)
    return frame


def _write_snapshot_atomically(
    output_dir: Path,
    pulls: pd.DataFrame,
    workflows: pd.DataFrame,
    metadata: SnapshotMetadata,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    final_paths = (
        output_dir / PULL_REQUEST_FILENAME,
        output_dir / WORKFLOW_FILENAME,
        output_dir / METADATA_FILENAME,
    )
    temporary_paths = tuple(path.with_name(f"{path.name}.tmp") for path in final_paths)
    try:
        pulls.to_csv(temporary_paths[0], index=False, date_format="%Y-%m-%dT%H:%M:%SZ")
        workflows.to_csv(temporary_paths[1], index=False, date_format="%Y-%m-%dT%H:%M:%SZ")
        temporary_paths[2].write_text(
            json.dumps(asdict(metadata), indent=2) + "\n",
            encoding="utf-8",
        )
        for temporary, final in zip(temporary_paths, final_paths, strict=True):
            temporary.replace(final)
    finally:
        for temporary in temporary_paths:
            temporary.unlink(missing_ok=True)
