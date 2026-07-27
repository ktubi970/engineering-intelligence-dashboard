import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, cast

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
SCHEMA_VERSION = 2
GITHUB_API_VERSION = "2022-11-28"
SOURCE_PROVIDER = "github"
SOURCE_VISIBILITY = "public"
SOURCE_API = "rest"
COLLECTION_ORDER = "api_default"
PULL_REQUEST_SELECTION = "merged"
WORKFLOW_SELECTION = "completed"

_TOP_LEVEL_KEYS = (
    "schema_version",
    "generated_at_utc",
    "source",
    "repositories",
    "row_counts",
    "collection",
    "files",
)
_SOURCE_KEYS = ("provider", "visibility", "api", "api_version")
_ROW_COUNT_KEYS = ("pull_requests", "workflow_runs")
_COLLECTION_KEYS = ("pull_requests", "workflow_runs")
_COLLECTION_ENTRY_KEYS = ("selection", "limit_per_repository", "order")
_FILE_KEYS = (PULL_REQUEST_FILENAME, WORKFLOW_FILENAME)
_FILE_ENTRY_KEYS = ("sha256",)
_UTC_TIMESTAMP_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z",
)
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


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
class SnapshotSource:
    provider: str
    visibility: str
    api: str
    api_version: str


@dataclass(frozen=True, slots=True)
class SnapshotRowCounts:
    pull_requests: int
    workflow_runs: int


@dataclass(frozen=True, slots=True)
class SnapshotCollectionEntry:
    selection: str
    limit_per_repository: int
    order: str


@dataclass(frozen=True, slots=True)
class SnapshotCollection:
    pull_requests: SnapshotCollectionEntry
    workflow_runs: SnapshotCollectionEntry


@dataclass(frozen=True, slots=True)
class SnapshotFile:
    sha256: str


@dataclass(frozen=True, slots=True)
class SnapshotMetadata:
    schema_version: int
    generated_at_utc: str
    source: SnapshotSource
    repositories: list[str]
    row_counts: SnapshotRowCounts
    collection: SnapshotCollection
    files: dict[str, SnapshotFile]

    @property
    def pull_request_rows(self) -> int:
        return self.row_counts.pull_requests

    @property
    def workflow_run_rows(self) -> int:
        return self.row_counts.workflow_runs


def refresh_snapshot(
    client: GitHubDataSource,
    repositories: Sequence[RepositoryRef],
    output_dir: Path,
    pr_limit: int = 150,
) -> SnapshotMetadata:
    if isinstance(pr_limit, bool) or not isinstance(pr_limit, int) or pr_limit <= 0:
        raise DataContractError("Snapshot collection limit_per_repository must be positive.")
    repository_slugs = [repository.slug for repository in repositories]
    if not repository_slugs:
        raise DataContractError("Snapshot collection requires at least one repository.")
    if len(repository_slugs) != len(set(repository_slugs)):
        raise DataContractError("Snapshot collection repositories must be unique.")

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

    return _write_snapshot_atomically(
        output_dir,
        pulls,
        workflows,
        repositories=repository_slugs,
        limit_per_repository=pr_limit,
    )


def load_snapshot(
    data_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    metadata = _read_metadata(data_dir / METADATA_FILENAME)
    _validate_metadata_document(metadata)

    snapshot_paths = {
        PULL_REQUEST_FILENAME: data_dir / PULL_REQUEST_FILENAME,
        WORKFLOW_FILENAME: data_dir / WORKFLOW_FILENAME,
    }
    _validate_file_hashes(metadata, snapshot_paths)

    pulls = _read_snapshot_frame(
        snapshot_paths[PULL_REQUEST_FILENAME],
        columns=PULL_REQUEST_COLUMNS,
        timestamp_columns=("created_at", "merged_at"),
        frame_name="Pull request",
    )
    workflows = _read_snapshot_frame(
        snapshot_paths[WORKFLOW_FILENAME],
        columns=WORKFLOW_COLUMNS,
        timestamp_columns=("created_at", "updated_at"),
        frame_name="Workflow",
    )
    validate_pull_request_frame(pulls)
    validate_workflow_frame(workflows)
    _validate_metadata_against_frames(metadata, pulls, workflows)
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
    *,
    repositories: list[str],
    limit_per_repository: int,
) -> SnapshotMetadata:
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

        metadata = SnapshotMetadata(
            schema_version=SCHEMA_VERSION,
            generated_at_utc=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            source=SnapshotSource(
                provider=SOURCE_PROVIDER,
                visibility=SOURCE_VISIBILITY,
                api=SOURCE_API,
                api_version=GITHUB_API_VERSION,
            ),
            repositories=repositories,
            row_counts=SnapshotRowCounts(
                pull_requests=len(pulls),
                workflow_runs=len(workflows),
            ),
            collection=SnapshotCollection(
                pull_requests=SnapshotCollectionEntry(
                    selection=PULL_REQUEST_SELECTION,
                    limit_per_repository=limit_per_repository,
                    order=COLLECTION_ORDER,
                ),
                workflow_runs=SnapshotCollectionEntry(
                    selection=WORKFLOW_SELECTION,
                    limit_per_repository=limit_per_repository,
                    order=COLLECTION_ORDER,
                ),
            ),
            files={
                PULL_REQUEST_FILENAME: SnapshotFile(
                    sha256=_sha256(temporary_paths[0]),
                ),
                WORKFLOW_FILENAME: SnapshotFile(
                    sha256=_sha256(temporary_paths[1]),
                ),
            },
        )
        metadata_document = cast(dict[str, object], asdict(metadata))
        _validate_metadata_document(metadata_document)
        _validate_metadata_against_frames(metadata_document, pulls, workflows)
        _validate_file_hashes(
            metadata_document,
            {
                PULL_REQUEST_FILENAME: temporary_paths[0],
                WORKFLOW_FILENAME: temporary_paths[1],
            },
        )
        temporary_paths[2].write_text(
            json.dumps(metadata_document, indent=2) + "\n",
            encoding="utf-8",
        )
        for temporary, final in zip(temporary_paths, final_paths, strict=True):
            temporary.replace(final)
        return metadata
    finally:
        for temporary in temporary_paths:
            temporary.unlink(missing_ok=True)


def _read_metadata(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise DataContractError("Snapshot metadata must be readable UTF-8 JSON.") from error
    if not isinstance(value, dict):
        raise DataContractError("Snapshot metadata must be a JSON object.")
    return cast(dict[str, object], value)


def _read_snapshot_frame(
    path: Path,
    *,
    columns: tuple[str, ...],
    timestamp_columns: tuple[str, ...],
    frame_name: str,
) -> pd.DataFrame:
    try:
        frame = pd.read_csv(path)
    except (OSError, UnicodeError, pd.errors.ParserError) as error:
        raise DataContractError(f"{frame_name} snapshot file must be readable CSV.") from error
    if tuple(frame.columns) != columns:
        raise DataContractError(f"{frame_name} frame must contain the exact columns in order.")
    for column in timestamp_columns:
        try:
            frame[column] = pd.to_datetime(frame[column], utc=True, errors="raise")
        except (TypeError, ValueError, OverflowError) as error:
            raise DataContractError(
                f"{frame_name} frame column {column} must contain valid timestamps.",
            ) from error
    return frame


def _validate_metadata_document(metadata: dict[str, object]) -> None:
    _require_exact_keys(metadata, _TOP_LEVEL_KEYS, "Snapshot metadata")

    schema_version = metadata["schema_version"]
    if (
        isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
        or schema_version != SCHEMA_VERSION
    ):
        raise DataContractError(
            f"Snapshot metadata schema_version must be integer {SCHEMA_VERSION}.",
        )
    _validate_generated_timestamp(metadata["generated_at_utc"])

    source = _require_object(metadata["source"], "Snapshot metadata source")
    _require_exact_keys(source, _SOURCE_KEYS, "Snapshot metadata source")
    _require_exact_value(
        source["provider"],
        SOURCE_PROVIDER,
        "Snapshot metadata source.provider",
    )
    _require_exact_value(
        source["visibility"],
        SOURCE_VISIBILITY,
        "Snapshot metadata source.visibility",
    )
    _require_exact_value(source["api"], SOURCE_API, "Snapshot metadata source.api")
    _require_exact_value(
        source["api_version"],
        GITHUB_API_VERSION,
        "Snapshot metadata source.api_version",
    )

    _validate_repositories(metadata["repositories"])

    row_counts = _require_object(metadata["row_counts"], "Snapshot metadata row_counts")
    _require_exact_keys(row_counts, _ROW_COUNT_KEYS, "Snapshot metadata row_counts")
    for name in _ROW_COUNT_KEYS:
        _require_non_negative_integer(
            row_counts[name],
            f"Snapshot metadata row_counts.{name}",
        )

    collection = _require_object(
        metadata["collection"],
        "Snapshot metadata collection",
    )
    _require_exact_keys(collection, _COLLECTION_KEYS, "Snapshot metadata collection")
    _validate_collection_entry(
        collection["pull_requests"],
        path="Snapshot metadata collection.pull_requests",
        selection=PULL_REQUEST_SELECTION,
    )
    _validate_collection_entry(
        collection["workflow_runs"],
        path="Snapshot metadata collection.workflow_runs",
        selection=WORKFLOW_SELECTION,
    )

    files = _require_object(metadata["files"], "Snapshot metadata files")
    _require_exact_keys(files, _FILE_KEYS, "Snapshot metadata files")
    for filename in _FILE_KEYS:
        entry = _require_object(
            files[filename],
            f"Snapshot metadata files.{filename}",
        )
        _require_exact_keys(
            entry,
            _FILE_ENTRY_KEYS,
            f"Snapshot metadata files.{filename}",
        )
        digest = entry["sha256"]
        if not isinstance(digest, str) or _SHA256_PATTERN.fullmatch(digest) is None:
            raise DataContractError(
                f"Snapshot metadata files.{filename}.sha256 must be a lowercase SHA-256 digest.",
            )


def _validate_generated_timestamp(value: object) -> None:
    if not isinstance(value, str) or _UTC_TIMESTAMP_PATTERN.fullmatch(value) is None:
        raise DataContractError(
            "Snapshot metadata generated_at_utc must be an RFC 3339 UTC timestamp ending in Z.",
        )
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise DataContractError(
            "Snapshot metadata generated_at_utc must be a valid UTC timestamp.",
        ) from error
    if parsed.tzinfo != UTC:
        raise DataContractError("Snapshot metadata generated_at_utc must use UTC.")


def _validate_repositories(value: object) -> None:
    if not isinstance(value, list) or not value:
        raise DataContractError(
            "Snapshot metadata repositories must be a non-empty JSON array.",
        )
    repositories: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise DataContractError(
                "Snapshot metadata repositories must contain owner/repository strings.",
            )
        try:
            repository = RepositoryRef.parse(item)
        except DataContractError as error:
            raise DataContractError(
                "Snapshot metadata repositories must contain owner/repository strings.",
            ) from error
        if repository.slug != item:
            raise DataContractError(
                "Snapshot metadata repositories must contain owner/repository strings.",
            )
        repositories.append(item)
    if len(repositories) != len(set(repositories)):
        raise DataContractError("Snapshot metadata repositories must be unique.")


def _validate_collection_entry(
    value: object,
    *,
    path: str,
    selection: str,
) -> None:
    entry = _require_object(value, path)
    _require_exact_keys(entry, _COLLECTION_ENTRY_KEYS, path)
    _require_exact_value(entry["selection"], selection, f"{path}.selection")
    _require_positive_integer(
        entry["limit_per_repository"],
        f"{path}.limit_per_repository",
    )
    _require_exact_value(entry["order"], COLLECTION_ORDER, f"{path}.order")


def _validate_file_hashes(
    metadata: dict[str, object],
    paths: Mapping[str, Path],
) -> None:
    files = _require_object(metadata["files"], "Snapshot metadata files")
    for filename in _FILE_KEYS:
        entry = _require_object(
            files[filename],
            f"Snapshot metadata files.{filename}",
        )
        expected = cast(str, entry["sha256"])
        try:
            actual = _sha256(paths[filename])
        except OSError as error:
            raise DataContractError(
                f"Snapshot file {filename} must be readable for SHA-256 validation.",
            ) from error
        if actual != expected:
            raise DataContractError(
                f"Snapshot file {filename} SHA-256 does not match metadata.",
            )


def _validate_metadata_against_frames(
    metadata: dict[str, object],
    pulls: pd.DataFrame,
    workflows: pd.DataFrame,
) -> None:
    row_counts = _require_object(metadata["row_counts"], "Snapshot metadata row_counts")
    expected_pull_rows = cast(int, row_counts["pull_requests"])
    expected_workflow_rows = cast(int, row_counts["workflow_runs"])
    if expected_pull_rows != len(pulls):
        raise DataContractError(
            "Snapshot metadata row_counts.pull_requests must equal "
            f"the CSV row count {len(pulls)}.",
        )
    if expected_workflow_rows != len(workflows):
        raise DataContractError(
            "Snapshot metadata row_counts.workflow_runs must equal "
            f"the CSV row count {len(workflows)}.",
        )

    expected_repositories = cast(list[str], metadata["repositories"])
    observed_repositories = set(pulls["repository"]) | set(workflows["repository"])
    if set(expected_repositories) != observed_repositories:
        raise DataContractError(
            "Snapshot metadata repositories must exactly match the repository "
            "set present in the CSV files.",
        )

    collection = _require_object(
        metadata["collection"],
        "Snapshot metadata collection",
    )
    pull_collection = _require_object(
        collection["pull_requests"],
        "Snapshot metadata collection.pull_requests",
    )
    workflow_collection = _require_object(
        collection["workflow_runs"],
        "Snapshot metadata collection.workflow_runs",
    )
    maximum_pull_rows = cast(int, pull_collection["limit_per_repository"]) * len(
        expected_repositories
    )
    maximum_workflow_rows = cast(
        int,
        workflow_collection["limit_per_repository"],
    ) * len(expected_repositories)
    if len(pulls) > maximum_pull_rows:
        raise DataContractError(
            "Snapshot metadata row_counts.pull_requests exceeds the declared collection limit.",
        )
    if len(workflows) > maximum_workflow_rows:
        raise DataContractError(
            "Snapshot metadata row_counts.workflow_runs exceeds the declared collection limit.",
        )


def _require_object(value: object, path: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise DataContractError(f"{path} must be a JSON object.")
    return cast(dict[str, object], value)


def _require_exact_keys(
    value: Mapping[str, object],
    expected: tuple[str, ...],
    path: str,
) -> None:
    if set(value) != set(expected):
        joined = ", ".join(expected)
        raise DataContractError(f"{path} must contain the exact keys: {joined}.")


def _require_exact_value(value: object, expected: str, path: str) -> None:
    if not isinstance(value, str) or value != expected:
        raise DataContractError(f"{path} must equal {expected!r}.")


def _require_non_negative_integer(value: object, path: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise DataContractError(f"{path} must be a non-negative integer.")


def _require_positive_integer(value: object, path: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise DataContractError(f"{path} must be a positive integer.")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
