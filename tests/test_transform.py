import pandas as pd
import pytest

from engineering_intelligence.domain import DataContractError
from engineering_intelligence.transform import (
    PULL_REQUEST_COLUMNS,
    WORKFLOW_COLUMNS,
    normalize_pull_requests,
    normalize_workflow_runs,
    validate_pull_request_frame,
    validate_workflow_frame,
)


def test_normalize_pull_requests_derives_hours_and_removes_identity(
    raw_pull_details: list[dict[str, object]],
) -> None:
    frame = normalize_pull_requests(raw_pull_details, "pandas-dev/pandas")

    assert frame.loc[0, "merge_hours"] == pytest.approx(48.0)
    assert frame.loc[0, "change_size"] == 140
    assert frame.loc[0, "title_length"] == 18
    assert frame.loc[0, "body_length"] == 17
    assert frame.loc[0, "opened_weekday"] == 3
    assert frame.loc[0, "opened_hour"] == 10
    assert "user" not in frame.columns
    assert "author_login" not in frame.columns


def test_normalize_pull_requests_uses_exact_privacy_safe_schema(
    raw_pull_details: list[dict[str, object]],
) -> None:
    frame = normalize_pull_requests(raw_pull_details, "pandas-dev/pandas")

    assert (
        list(frame.columns)
        == list(PULL_REQUEST_COLUMNS)
        == [
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
    )
    serialized = frame.to_csv(index=False)
    for private_value in (
        "private-login",
        "private@example.invalid",
        "https://example.invalid/avatar",
        "private-head-sha",
        "Merge metrics fast",
        "A public summary.",
    ):
        assert private_value not in serialized
    assert isinstance(frame.loc[0, "created_at"], pd.Timestamp)
    assert str(frame["created_at"].dt.tz) == "UTC"


def test_normalize_pull_requests_removes_unmerged_records(
    raw_pull_details: list[dict[str, object]],
) -> None:
    unmerged = {
        **raw_pull_details[0],
        "number": 102,
        "merged_at": None,
        "user": {"login": "another-private-login"},
    }

    frame = normalize_pull_requests(
        [unmerged, *raw_pull_details],
        "pandas-dev/pandas",
    )

    assert frame["number"].tolist() == [101]
    assert "another-private-login" not in frame.to_csv(index=False)


@pytest.mark.parametrize(
    ("created_at", "merged_at"),
    [
        ("2026-01-03T10:00:00Z", "2026-01-03T10:00:00Z"),
        ("2026-01-04T10:00:00Z", "2026-01-03T10:00:00Z"),
    ],
)
def test_normalize_pull_requests_rejects_non_positive_merge_duration(
    raw_pull_details: list[dict[str, object]],
    created_at: str,
    merged_at: str,
) -> None:
    invalid = {
        **raw_pull_details[0],
        "created_at": created_at,
        "merged_at": merged_at,
    }

    with pytest.raises(DataContractError, match="positive merge duration"):
        normalize_pull_requests([invalid], "pandas-dev/pandas")


def test_normalize_workflow_runs_derives_duration_and_removes_head_sha(
    raw_workflow_runs: list[dict[str, object]],
) -> None:
    frame = normalize_workflow_runs(raw_workflow_runs, "pandas-dev/pandas")

    assert frame.loc[0, "duration_minutes"] == pytest.approx(12.0)
    assert frame.loc[1, "duration_minutes"] == pytest.approx(5.0)
    assert "head_sha" not in frame.columns
    assert "1111111111111111111111111111111111111111" not in frame.to_csv(index=False)


def test_normalize_workflow_runs_uses_exact_schema(
    raw_workflow_runs: list[dict[str, object]],
) -> None:
    frame = normalize_workflow_runs(raw_workflow_runs, "pandas-dev/pandas")

    assert (
        list(frame.columns)
        == list(WORKFLOW_COLUMNS)
        == [
            "repository",
            "run_id",
            "workflow_name",
            "status",
            "conclusion",
            "created_at",
            "updated_at",
            "duration_minutes",
        ]
    )
    assert str(frame["created_at"].dt.tz) == "UTC"
    assert str(frame["updated_at"].dt.tz) == "UTC"


def test_normalize_workflow_runs_keeps_only_completed_runs(
    raw_workflow_runs: list[dict[str, object]],
) -> None:
    queued = {
        **raw_workflow_runs[0],
        "id": 9003,
        "status": "queued",
        "conclusion": None,
        "updated_at": "2026-01-02T11:00:00Z",
    }
    in_progress = {
        **raw_workflow_runs[0],
        "id": 9002,
        "status": "in_progress",
        "conclusion": None,
        "updated_at": "2026-01-02T11:06:00Z",
    }
    completed = raw_workflow_runs[0]

    frame = normalize_workflow_runs(
        [queued, completed, in_progress],
        "pandas-dev/pandas",
    )

    assert frame["run_id"].tolist() == [9001]
    assert frame["status"].tolist() == ["completed"]
    assert frame["conclusion"].tolist() == ["success"]


def test_normalize_workflow_runs_rejects_negative_duration(
    raw_workflow_runs: list[dict[str, object]],
) -> None:
    invalid = {
        **raw_workflow_runs[0],
        "updated_at": "2026-01-02T10:59:00Z",
    }

    with pytest.raises(DataContractError, match="negative workflow duration"):
        normalize_workflow_runs([invalid], "pandas-dev/pandas")


def test_normalizers_return_typed_empty_frames() -> None:
    pulls = normalize_pull_requests([], "pandas-dev/pandas")
    workflows = normalize_workflow_runs([], "pandas-dev/pandas")

    assert list(pulls.columns) == list(PULL_REQUEST_COLUMNS)
    assert list(workflows.columns) == list(WORKFLOW_COLUMNS)
    assert str(pulls["created_at"].dt.tz) == "UTC"
    assert str(pulls["merged_at"].dt.tz) == "UTC"
    assert str(workflows["created_at"].dt.tz) == "UTC"
    assert str(workflows["updated_at"].dt.tz) == "UTC"
    validate_pull_request_frame(pulls)
    validate_workflow_frame(workflows)


@pytest.mark.parametrize(
    ("validator_name", "column"),
    [
        ("pull", "merge_hours"),
        ("workflow", "conclusion"),
    ],
)
def test_validators_reject_null_values(
    raw_pull_details: list[dict[str, object]],
    raw_workflow_runs: list[dict[str, object]],
    validator_name: str,
    column: str,
) -> None:
    if validator_name == "pull":
        frame = normalize_pull_requests(raw_pull_details, "pandas-dev/pandas")
        validator = validate_pull_request_frame
    else:
        frame = normalize_workflow_runs(raw_workflow_runs, "pandas-dev/pandas")
        validator = validate_workflow_frame
    frame.loc[0, column] = None

    with pytest.raises(DataContractError, match=f"null values.*{column}"):
        validator(frame)


@pytest.mark.parametrize("validator_name", ["pull", "workflow"])
def test_validators_reject_duplicate_repository_identifiers(
    raw_pull_details: list[dict[str, object]],
    raw_workflow_runs: list[dict[str, object]],
    validator_name: str,
) -> None:
    if validator_name == "pull":
        frame = normalize_pull_requests(raw_pull_details, "pandas-dev/pandas")
        validator = validate_pull_request_frame
    else:
        normalized = normalize_workflow_runs(raw_workflow_runs, "pandas-dev/pandas")
        frame = normalized.iloc[[0, 0]].reset_index(drop=True)
        validator = validate_workflow_frame
    if validator_name == "pull":
        frame = pd.concat([frame, frame], ignore_index=True)

    with pytest.raises(DataContractError, match="duplicate"):
        validator(frame)


@pytest.mark.parametrize("validator_name", ["pull", "workflow"])
def test_validators_reject_non_utc_timestamps(
    raw_pull_details: list[dict[str, object]],
    raw_workflow_runs: list[dict[str, object]],
    validator_name: str,
) -> None:
    if validator_name == "pull":
        frame = normalize_pull_requests(raw_pull_details, "pandas-dev/pandas")
        frame["created_at"] = frame["created_at"].dt.tz_convert("Europe/Berlin")
        validator = validate_pull_request_frame
    else:
        frame = normalize_workflow_runs(raw_workflow_runs, "pandas-dev/pandas")
        frame["updated_at"] = frame["updated_at"].dt.tz_localize(None)
        validator = validate_workflow_frame

    with pytest.raises(DataContractError, match="UTC"):
        validator(frame)


@pytest.mark.parametrize("validator_name", ["pull", "workflow"])
def test_validators_reject_wrong_schema(
    raw_pull_details: list[dict[str, object]],
    raw_workflow_runs: list[dict[str, object]],
    validator_name: str,
) -> None:
    if validator_name == "pull":
        frame = normalize_pull_requests(raw_pull_details, "pandas-dev/pandas")
        validator = validate_pull_request_frame
    else:
        frame = normalize_workflow_runs(raw_workflow_runs, "pandas-dev/pandas")
        validator = validate_workflow_frame

    with pytest.raises(DataContractError, match="exact columns"):
        validator(frame.assign(author_login="must-not-persist"))


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("repository", "not-a-repository", "owner/repository"),
        ("number", 0, "number.*positive integer"),
        ("number", 1.5, "number.*integer"),
        ("merge_hours", "fast", "merge_hours.*numeric"),
        ("title_length", -1, "title_length.*non-negative"),
        ("body_length", -1, "body_length.*non-negative"),
        ("labels_count", -1, "labels_count.*non-negative"),
        ("additions", -1, "additions.*non-negative"),
        ("deletions", -1, "deletions.*non-negative"),
        ("change_size", -1, "change_size.*non-negative"),
        ("changed_files", -1, "changed_files.*non-negative"),
        ("commits", 0, "commits.*positive integer"),
        ("opened_weekday", 7, "opened_weekday.*0 and 6"),
        ("opened_hour", 24, "opened_hour.*0 and 23"),
        ("author_association", "ADMIN", "author_association"),
    ],
)
def test_pull_validator_rejects_invalid_types_ranges_and_enums(
    raw_pull_details: list[dict[str, object]],
    column: str,
    value: object,
    message: str,
) -> None:
    frame = normalize_pull_requests(raw_pull_details, "pandas-dev/pandas")
    frame[column] = value

    with pytest.raises(DataContractError, match=message):
        validate_pull_request_frame(frame)


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("merge_hours", 47.0),
        ("change_size", 139),
        ("opened_weekday", 4),
        ("opened_hour", 11),
    ],
)
def test_pull_validator_recomputes_derived_values(
    raw_pull_details: list[dict[str, object]],
    column: str,
    value: object,
) -> None:
    frame = normalize_pull_requests(raw_pull_details, "pandas-dev/pandas")
    frame[column] = value

    with pytest.raises(DataContractError, match=column):
        validate_pull_request_frame(frame)


def test_pull_validator_rejects_merge_before_creation(
    raw_pull_details: list[dict[str, object]],
) -> None:
    frame = normalize_pull_requests(raw_pull_details, "pandas-dev/pandas")
    frame["merged_at"] = frame["created_at"]

    with pytest.raises(DataContractError, match="merged_at.*after created_at"):
        validate_pull_request_frame(frame)


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("repository", "not-a-repository", "owner/repository"),
        ("run_id", 0, "run_id.*positive integer"),
        ("run_id", 1.5, "run_id.*integer"),
        ("workflow_name", "", "workflow_name.*non-empty"),
        ("status", "queued", "status.*completed"),
        ("conclusion", "pending", "conclusion"),
        ("duration_minutes", "slow", "duration_minutes.*numeric"),
        ("duration_minutes", -1.0, "duration_minutes.*non-negative"),
    ],
)
def test_workflow_validator_rejects_invalid_types_ranges_and_enums(
    raw_workflow_runs: list[dict[str, object]],
    column: str,
    value: object,
    message: str,
) -> None:
    frame = normalize_workflow_runs(raw_workflow_runs, "pandas-dev/pandas")
    if column == "run_id":
        if isinstance(value, float):
            frame[column] = frame[column].astype(float)
        frame.loc[0, column] = value
    else:
        frame[column] = value

    with pytest.raises(DataContractError, match=message):
        validate_workflow_frame(frame)


def test_workflow_validator_recomputes_duration(
    raw_workflow_runs: list[dict[str, object]],
) -> None:
    frame = normalize_workflow_runs(raw_workflow_runs, "pandas-dev/pandas")
    frame["duration_minutes"] = 13.0

    with pytest.raises(DataContractError, match="duration_minutes"):
        validate_workflow_frame(frame)


def test_workflow_validator_rejects_update_before_creation(
    raw_workflow_runs: list[dict[str, object]],
) -> None:
    frame = normalize_workflow_runs(raw_workflow_runs, "pandas-dev/pandas")
    frame["updated_at"] = frame["created_at"] - pd.Timedelta(seconds=1)

    with pytest.raises(DataContractError, match="updated_at.*before created_at"):
        validate_workflow_frame(frame)
