from collections.abc import Iterable, Mapping

import pandas as pd

from engineering_intelligence.domain import DataContractError

PULL_REQUEST_COLUMNS = (
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
)

WORKFLOW_COLUMNS = (
    "repository",
    "run_id",
    "workflow_name",
    "status",
    "conclusion",
    "created_at",
    "updated_at",
    "duration_minutes",
)


def normalize_pull_requests(
    records: Iterable[Mapping[str, object]],
    repository: str,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for record in records:
        if record.get("merged_at") is None:
            continue

        created_at = pd.to_datetime(record.get("created_at"), utc=True)
        merged_at = pd.to_datetime(record.get("merged_at"), utc=True)
        merge_hours = (merged_at - created_at).total_seconds() / 3600
        if merge_hours <= 0:
            raise DataContractError("Pull requests must have a positive merge duration.")

        additions = record.get("additions")
        deletions = record.get("deletions")
        if not isinstance(additions, int) or not isinstance(deletions, int):
            raise DataContractError("Pull request additions and deletions must be integers.")

        title = record.get("title")
        body = record.get("body")
        labels = record.get("labels")
        rows.append(
            {
                "repository": repository,
                "number": record.get("number"),
                "created_at": created_at,
                "merged_at": merged_at,
                "merge_hours": merge_hours,
                "title_length": len(title) if isinstance(title, str) else 0,
                "body_length": len(body) if isinstance(body, str) else 0,
                "author_association": record.get("author_association"),
                "labels_count": len(labels) if isinstance(labels, list) else 0,
                "additions": additions,
                "deletions": deletions,
                "change_size": additions + deletions,
                "changed_files": record.get("changed_files"),
                "commits": record.get("commits"),
                "opened_weekday": created_at.weekday(),
                "opened_hour": created_at.hour,
            }
        )

    frame = _frame_with_utc_columns(rows, PULL_REQUEST_COLUMNS, ("created_at", "merged_at"))
    validate_pull_request_frame(frame)
    return frame


def normalize_workflow_runs(
    records: Iterable[Mapping[str, object]],
    repository: str,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for record in records:
        created_at = pd.to_datetime(record.get("created_at"), utc=True)
        updated_at = pd.to_datetime(record.get("updated_at"), utc=True)
        duration_minutes = (updated_at - created_at).total_seconds() / 60
        if duration_minutes < 0:
            raise DataContractError("Workflow runs cannot have a negative workflow duration.")

        rows.append(
            {
                "repository": repository,
                "run_id": record.get("id"),
                "workflow_name": record.get("name"),
                "status": record.get("status"),
                "conclusion": record.get("conclusion"),
                "created_at": created_at,
                "updated_at": updated_at,
                "duration_minutes": duration_minutes,
            }
        )

    frame = _frame_with_utc_columns(
        rows,
        WORKFLOW_COLUMNS,
        ("created_at", "updated_at"),
    )
    validate_workflow_frame(frame)
    return frame


def validate_pull_request_frame(frame: pd.DataFrame) -> None:
    _validate_frame(
        frame,
        columns=PULL_REQUEST_COLUMNS,
        identifier_columns=("repository", "number"),
        timestamp_columns=("created_at", "merged_at"),
        frame_name="Pull request",
    )
    if (frame["merge_hours"] <= 0).any():
        raise DataContractError("Pull requests must have a positive merge duration.")


def validate_workflow_frame(frame: pd.DataFrame) -> None:
    _validate_frame(
        frame,
        columns=WORKFLOW_COLUMNS,
        identifier_columns=("repository", "run_id"),
        timestamp_columns=("created_at", "updated_at"),
        frame_name="Workflow",
    )
    if (frame["duration_minutes"] < 0).any():
        raise DataContractError("Workflow runs cannot have a negative workflow duration.")


def _frame_with_utc_columns(
    rows: list[dict[str, object]],
    columns: tuple[str, ...],
    timestamp_columns: tuple[str, ...],
) -> pd.DataFrame:
    frame = pd.DataFrame(rows, columns=columns)
    for column in timestamp_columns:
        frame[column] = pd.to_datetime(frame[column], utc=True)
    return frame


def _validate_frame(
    frame: pd.DataFrame,
    *,
    columns: tuple[str, ...],
    identifier_columns: tuple[str, ...],
    timestamp_columns: tuple[str, ...],
    frame_name: str,
) -> None:
    if tuple(frame.columns) != columns:
        raise DataContractError(f"{frame_name} frame must contain the exact columns in order.")

    null_columns = frame.columns[frame.isna().any()].tolist()
    if null_columns:
        joined = ", ".join(null_columns)
        raise DataContractError(f"{frame_name} frame contains null values in columns: {joined}.")

    if frame.duplicated(list(identifier_columns)).any():
        raise DataContractError(f"{frame_name} frame contains duplicate repository identifiers.")

    for column in timestamp_columns:
        dtype = frame[column].dtype
        if not isinstance(dtype, pd.DatetimeTZDtype) or str(dtype.tz) != "UTC":
            raise DataContractError(f"{frame_name} frame column {column} must use UTC timestamps.")
