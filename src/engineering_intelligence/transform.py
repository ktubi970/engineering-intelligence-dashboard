import math
from collections.abc import Iterable, Mapping

import pandas as pd
from pandas.api.types import is_bool_dtype, is_integer_dtype, is_numeric_dtype

from engineering_intelligence.domain import DataContractError, RepositoryRef

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

AUTHOR_ASSOCIATIONS = frozenset(
    {
        "COLLABORATOR",
        "CONTRIBUTOR",
        "FIRST_TIMER",
        "FIRST_TIME_CONTRIBUTOR",
        "MANNEQUIN",
        "MEMBER",
        "NONE",
        "OWNER",
    }
)
WORKFLOW_CONCLUSIONS = frozenset(
    {
        "action_required",
        "cancelled",
        "failure",
        "neutral",
        "skipped",
        "stale",
        "startup_failure",
        "success",
        "timed_out",
    }
)
DERIVED_RELATIVE_TOLERANCE = 1e-9
DERIVED_ABSOLUTE_TOLERANCE = 1e-9


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
        if record.get("status") != "completed":
            continue

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
    _validate_repository_column(frame, "Pull request")
    _validate_positive_integer(frame, "number", "Pull request")
    _validate_finite_numeric(frame, "merge_hours", "Pull request")
    for column in (
        "title_length",
        "body_length",
        "labels_count",
        "additions",
        "deletions",
        "change_size",
        "changed_files",
    ):
        _validate_non_negative_integer(frame, column, "Pull request")
    _validate_positive_integer(frame, "commits", "Pull request")
    _validate_bounded_integer(frame, "opened_weekday", 0, 6, "Pull request")
    _validate_bounded_integer(frame, "opened_hour", 0, 23, "Pull request")
    _validate_enum_column(
        frame,
        "author_association",
        AUTHOR_ASSOCIATIONS,
        "Pull request",
    )

    if (frame["merged_at"] <= frame["created_at"]).any():
        raise DataContractError(
            "Pull request frame merged_at must be after created_at.",
        )
    if (frame["merge_hours"] <= 0).any():
        raise DataContractError("Pull request frame merge_hours must be positive.")

    expected_merge_hours = (frame["merged_at"] - frame["created_at"]).dt.total_seconds() / 3600
    _validate_derived_float(
        frame["merge_hours"],
        expected_merge_hours,
        "Pull request frame merge_hours must equal merged_at minus created_at.",
    )
    if not frame["change_size"].eq(frame["additions"] + frame["deletions"]).all():
        raise DataContractError(
            "Pull request frame change_size must equal additions plus deletions.",
        )
    if not frame["opened_weekday"].eq(frame["created_at"].dt.weekday).all():
        raise DataContractError(
            "Pull request frame opened_weekday must match created_at in UTC.",
        )
    if not frame["opened_hour"].eq(frame["created_at"].dt.hour).all():
        raise DataContractError(
            "Pull request frame opened_hour must match created_at in UTC.",
        )


def validate_workflow_frame(frame: pd.DataFrame) -> None:
    _validate_frame(
        frame,
        columns=WORKFLOW_COLUMNS,
        identifier_columns=("repository", "run_id"),
        timestamp_columns=("created_at", "updated_at"),
        frame_name="Workflow",
    )
    _validate_repository_column(frame, "Workflow")
    _validate_positive_integer(frame, "run_id", "Workflow")
    _validate_non_empty_string(frame, "workflow_name", "Workflow")
    _validate_enum_column(frame, "status", frozenset({"completed"}), "Workflow")
    _validate_enum_column(
        frame,
        "conclusion",
        WORKFLOW_CONCLUSIONS,
        "Workflow",
    )
    _validate_finite_numeric(frame, "duration_minutes", "Workflow")

    if (frame["updated_at"] < frame["created_at"]).any():
        raise DataContractError(
            "Workflow frame updated_at cannot be before created_at.",
        )
    if (frame["duration_minutes"] < 0).any():
        raise DataContractError(
            "Workflow frame duration_minutes must be non-negative.",
        )

    expected_duration_minutes = (frame["updated_at"] - frame["created_at"]).dt.total_seconds() / 60
    _validate_derived_float(
        frame["duration_minutes"],
        expected_duration_minutes,
        "Workflow frame duration_minutes must equal updated_at minus created_at.",
    )


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


def _validate_repository_column(frame: pd.DataFrame, frame_name: str) -> None:
    for value in frame["repository"]:
        if not isinstance(value, str):
            raise DataContractError(
                f"{frame_name} frame repository must use the owner/repository form.",
            )
        try:
            repository = RepositoryRef.parse(value)
        except DataContractError as error:
            raise DataContractError(
                f"{frame_name} frame repository must use the owner/repository form.",
            ) from error
        if repository.slug != value:
            raise DataContractError(
                f"{frame_name} frame repository must use the owner/repository form.",
            )


def _validate_positive_integer(
    frame: pd.DataFrame,
    column: str,
    frame_name: str,
) -> None:
    _validate_integer_dtype(frame, column, frame_name)
    if not frame.empty and (frame[column] <= 0).any():
        raise DataContractError(
            f"{frame_name} frame column {column} must contain positive integers.",
        )


def _validate_non_negative_integer(
    frame: pd.DataFrame,
    column: str,
    frame_name: str,
) -> None:
    _validate_integer_dtype(frame, column, frame_name)
    if not frame.empty and (frame[column] < 0).any():
        raise DataContractError(
            f"{frame_name} frame column {column} must contain non-negative integers.",
        )


def _validate_bounded_integer(
    frame: pd.DataFrame,
    column: str,
    minimum: int,
    maximum: int,
    frame_name: str,
) -> None:
    _validate_integer_dtype(frame, column, frame_name)
    if not frame.empty and not frame[column].between(minimum, maximum).all():
        raise DataContractError(
            f"{frame_name} frame column {column} must be between {minimum} and {maximum}.",
        )


def _validate_integer_dtype(
    frame: pd.DataFrame,
    column: str,
    frame_name: str,
) -> None:
    if frame.empty:
        return
    dtype = frame[column].dtype
    if is_bool_dtype(dtype) or not is_integer_dtype(dtype):
        raise DataContractError(
            f"{frame_name} frame column {column} must contain integers.",
        )


def _validate_finite_numeric(
    frame: pd.DataFrame,
    column: str,
    frame_name: str,
) -> None:
    if frame.empty:
        return
    dtype = frame[column].dtype
    if is_bool_dtype(dtype) or not is_numeric_dtype(dtype):
        raise DataContractError(
            f"{frame_name} frame column {column} must contain numeric values.",
        )
    if not frame[column].map(lambda value: math.isfinite(float(value))).all():
        raise DataContractError(
            f"{frame_name} frame column {column} must contain finite numeric values.",
        )


def _validate_non_empty_string(
    frame: pd.DataFrame,
    column: str,
    frame_name: str,
) -> None:
    if (
        not frame[column]
        .map(
            lambda value: isinstance(value, str) and bool(value.strip()),
        )
        .all()
    ):
        raise DataContractError(
            f"{frame_name} frame column {column} must contain non-empty strings.",
        )


def _validate_enum_column(
    frame: pd.DataFrame,
    column: str,
    allowed: frozenset[str],
    frame_name: str,
) -> None:
    _validate_non_empty_string(frame, column, frame_name)
    if not frame[column].isin(allowed).all():
        expected = ", ".join(sorted(allowed))
        raise DataContractError(
            f"{frame_name} frame column {column} must contain one of: {expected}.",
        )


def _validate_derived_float(
    actual: pd.Series,
    expected: pd.Series,
    message: str,
) -> None:
    matches = (
        math.isclose(
            float(actual_value),
            float(expected_value),
            rel_tol=DERIVED_RELATIVE_TOLERANCE,
            abs_tol=DERIVED_ABSOLUTE_TOLERANCE,
        )
        for actual_value, expected_value in zip(actual, expected, strict=True)
    )
    if not all(matches):
        raise DataContractError(message)
