from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, time
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import engineering_intelligence.dashboard as dashboard
from engineering_intelligence.dashboard import (
    evaluation_summary,
    opening_feature_frame,
    resolve_data_dir,
)
from engineering_intelligence.transform import PULL_REQUEST_COLUMNS, WORKFLOW_COLUMNS

WARNING = (
    "Experimental estimate — not a delivery promise or an explanation of cause. "
    "Never use it to score developers."
)
APP_PATH = Path(__file__).parents[1] / "streamlit_app.py"


def _logical_csv_sha256(path: Path) -> str:
    content = path.read_bytes()
    canonical_content = content.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(canonical_content).hexdigest()


@pytest.fixture
def snapshot_dir(tmp_path: Path) -> Path:
    _write_snapshot(tmp_path, pull_request_rows=100)
    return tmp_path


@pytest.fixture
def small_snapshot_dir(tmp_path: Path) -> Path:
    _write_snapshot(tmp_path, pull_request_rows=12)
    return tmp_path


@pytest.fixture
def unavailable_labels_snapshot_dir(tmp_path: Path) -> Path:
    _write_snapshot(tmp_path, pull_request_rows=80, defer_training_labels=True)
    return tmp_path


@pytest.fixture
def filter_snapshot_dir(tmp_path: Path) -> Path:
    _write_filter_snapshot(tmp_path)
    return tmp_path


def test_dashboard_loads_snapshot_and_shows_exact_core_sections(
    snapshot_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EID_DATA_DIR", str(snapshot_dir))

    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)

    assert not app.exception
    assert [title.value for title in app.title] == ["MergeLens"]
    assert [tab.label for tab in app.tabs] == [
        "Delivery overview",
        "Where work slows down",
        "Merge-time estimate",
    ]
    assert [metric.label for metric in app.metric] == [
        "PRs merged",
        "Typical merge time",
        "90% merged within",
        "Successful workflows",
    ]
    assert [subheader.value for subheader in app.subheader] == [
        "Merge time by week",
        "Patterns worth exploring",
        "How accurate is the estimate?",
        "Try an estimate",
    ]
    assert [warning.value for warning in app.warning] == [WARNING]


def test_dashboard_copy_is_product_first_and_hides_the_technical_stack(
    snapshot_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EID_DATA_DIR", str(snapshot_dir))

    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)

    visible_text = "\n".join(
        element.value
        for collection in (app.title, app.subheader, app.markdown, app.caption, app.info)
        for element in collection
    )
    assert "Typical is the median." in visible_text
    assert "past data" in visible_text
    for implementation_detail in (
        "Technical stack",
        "Streamlit",
        "pandas",
        "Plotly",
        "scikit-learn",
        "pytest",
    ):
        assert implementation_detail not in visible_text


def test_forecast_form_accepts_only_opening_time_features(
    snapshot_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EID_DATA_DIR", str(snapshot_dir))

    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)

    widget_labels = {
        widget.label
        for collection in (
            app.selectbox,
            app.number_input,
            app.date_input,
            app.time_input,
            app.text_input,
        )
        for widget in collection
    }
    assert {
        "Repository",
        "Pull request number",
        "Opening date (UTC)",
        "Opening time (UTC)",
    }.issubset(widget_labels)
    assert widget_labels.isdisjoint(
        {
            "Author association",
            "Title length",
            "Body length",
            "Labels",
            "Additions",
            "Deletions",
            "Change size",
            "Changed files",
            "Commits",
            "Target",
            "Merge time",
        }
    )


def test_forecast_submission_shows_both_estimates_and_highlights_recommended_winner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EID_DATA_DIR", str(APP_PATH.parent / "data" / "snapshots"))

    app = AppTest.from_file(APP_PATH)
    app.run(timeout=30)
    app.button[0].click()
    app.run(timeout=30)

    assert not app.exception
    success_estimates = [
        message.value for message in app.success if "estimate" in message.value.lower()
    ]
    info_estimates = [message.value for message in app.info if "estimate" in message.value.lower()]
    assert len(success_estimates) == 1
    assert "Recommended — Model estimate" in success_estimates[0]
    assert any("Simple benchmark" in value for value in info_estimates)

    estimate_cards = success_estimates + info_estimates
    assert len(estimate_cards) == 2
    assert all("Average error on recent test data" in value for value in estimate_cards)
    assert all("not a guaranteed range" in value for value in estimate_cards)

    visible_text = "\n".join(
        element.value
        for collection in (app.caption, app.info, app.success, app.markdown)
        for element in collection
    )
    assert "pull requests that eventually merge" in visible_text
    assert "MAE is the average number of hours" in visible_text


def test_small_snapshot_has_readable_forecast_state_without_exception(
    small_snapshot_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EID_DATA_DIR", str(small_snapshot_dir))

    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)

    assert not app.exception
    assert any("Choose at least 80 pull requests" in info.value for info in app.info)
    assert [warning.value for warning in app.warning] == [WARNING]


def test_unavailable_training_labels_have_readable_forecast_state(
    unavailable_labels_snapshot_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EID_DATA_DIR", str(unavailable_labels_snapshot_dir))

    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)

    assert not app.exception
    assert any(
        "Choose at least 80 pull requests"
        in info.value
        for info in app.info
    )


def test_empty_repository_filter_has_readable_state_without_exception(
    snapshot_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EID_DATA_DIR", str(snapshot_dir))
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)

    app.sidebar.multiselect[0].set_value([])
    app.run(timeout=20)

    assert not app.exception
    assert any(
        "No pull requests match these filters."
        in info.value
        for info in app.info
    )


def test_repository_filter_includes_and_handles_workflow_only_repository(
    filter_snapshot_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EID_DATA_DIR", str(filter_snapshot_dir))
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)

    repository_filter = app.sidebar.multiselect[0]
    assert repository_filter.options == ["alpha/api", "beta/web", "ops/infra"]

    repository_filter.set_value(["ops/infra"])
    app.run(timeout=20)

    assert not app.exception
    assert app.metric[0].value == "0"
    assert app.metric[3].value == "100.0%"


def test_merge_date_filter_applies_same_inclusive_utc_window_to_workflows(
    filter_snapshot_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EID_DATA_DIR", str(filter_snapshot_dir))
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=20)

    app.sidebar.date_input[0].set_value(
        (
            date(2025, 1, 1),
            date(2025, 1, 1),
        )
    )
    app.run(timeout=20)

    assert not app.exception
    assert app.metric[3].value == "100.0%"


def test_data_dir_defaults_to_the_committed_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("EID_DATA_DIR", raising=False)

    assert resolve_data_dir() == APP_PATH.parent / "data" / "snapshots"


def test_committed_snapshot_exposes_all_six_repository_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("EID_DATA_DIR", raising=False)

    app = AppTest.from_file(APP_PATH)
    app.run(timeout=30)

    assert not app.exception
    assert app.sidebar.multiselect[0].options == [
        "microsoft/vscode",
        "pandas-dev/pandas",
        "ruby/ruby",
        "rust-lang/rust",
        "streamlit/streamlit",
        "tensorflow/tensorflow",
    ]


def test_opening_feature_frame_contains_only_the_three_utc_model_inputs() -> None:
    features = opening_feature_frame(
        "alpha/api",
        1_234,
        date(2026, 7, 27),
        time(14, 30),
    )

    assert features.columns.tolist() == ["repository", "number", "created_at"]
    assert features.loc[0, "repository"] == "alpha/api"
    assert features.loc[0, "number"] == 1_234
    assert (
        features.loc[0, "created_at"].to_pydatetime()
        == pd.Timestamp("2026-07-27T14:30:00Z").to_pydatetime()
    )
    assert features.loc[0, "created_at"].tzinfo == UTC


@pytest.mark.parametrize(
    ("model_mae", "baseline_mae", "expected_level", "expected_winner"),
    [
        (8.0, 12.0, "success", "The model was more accurate"),
        (12.0, 8.0, "info", "The simple benchmark was more accurate"),
        (8.0, 8.0, "info", "The model and simple benchmark were equally accurate"),
    ],
)
def test_evaluation_summary_names_the_actual_lower_mae(
    model_mae: float,
    baseline_mae: float,
    expected_level: str,
    expected_winner: str,
) -> None:
    level, message = evaluation_summary(model_mae, baseline_mae)

    assert level == expected_level
    assert message.startswith(expected_winner)
    assert "8.0" in message


@pytest.mark.parametrize(
    ("model_mae", "baseline_mae", "expected"),
    [
        (8.0, 12.0, "random forest"),
        (12.0, 8.0, "train-median baseline"),
        (8.0, 8.0, "train-median baseline"),
    ],
)
def test_preferred_forecast_uses_lower_mae_and_defaults_ties_to_baseline(
    model_mae: float,
    baseline_mae: float,
    expected: str,
) -> None:
    assert dashboard.preferred_forecast(model_mae, baseline_mae) == expected


def _write_filter_snapshot(data_dir: Path) -> None:
    _write_snapshot(data_dir, pull_request_rows=12)
    workflows = pd.DataFrame(
        {
            "repository": ["alpha/api", "alpha/api", "ops/infra"],
            "run_id": [3_001, 3_002, 3_003],
            "workflow_name": ["CI", "CI", "Deploy"],
            "status": ["completed", "completed", "completed"],
            "conclusion": ["success", "failure", "success"],
            "created_at": pd.to_datetime(
                [
                    "2025-01-01T12:00:00Z",
                    "2025-01-04T12:00:00Z",
                    "2025-01-01T18:00:00Z",
                ],
                utc=True,
            ),
            "updated_at": pd.to_datetime(
                [
                    "2025-01-01T12:10:00Z",
                    "2025-01-04T12:10:00Z",
                    "2025-01-01T18:10:00Z",
                ],
                utc=True,
            ),
            "duration_minutes": [10.0, 10.0, 10.0],
        },
        columns=WORKFLOW_COLUMNS,
    )
    workflows.to_csv(
        data_dir / "workflow_runs.csv",
        index=False,
        date_format="%Y-%m-%dT%H:%M:%SZ",
    )
    metadata_path = data_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["repositories"] = ["alpha/api", "beta/web", "ops/infra"]
    metadata["row_counts"]["workflow_runs"] = 3
    metadata["files"]["workflow_runs.csv"]["sha256"] = _logical_csv_sha256(
        data_dir / "workflow_runs.csv"
    )
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def _write_snapshot(
    data_dir: Path,
    pull_request_rows: int,
    *,
    defer_training_labels: bool = False,
) -> None:
    row_number = pd.Series(range(pull_request_rows), dtype="int64")
    created_at = pd.date_range(
        "2025-01-01",
        periods=pull_request_rows,
        freq="6h",
        tz="UTC",
    )
    merge_hours = pd.Series(
        [12.0, 30.0, 48.0, 66.0] * ((pull_request_rows + 3) // 4),
        dtype="float64",
    ).head(pull_request_rows)
    repositories = [
        "alpha/api" if index % 2 == 0 else "beta/web" for index in range(pull_request_rows)
    ]
    pulls = pd.DataFrame(
        {
            "repository": repositories,
            "number": 1_001 + row_number,
            "created_at": created_at,
            "merged_at": created_at + pd.to_timedelta(merge_hours, unit="h"),
            "merge_hours": merge_hours,
            "title_length": 20,
            "body_length": 100,
            "author_association": "CONTRIBUTOR",
            "labels_count": 1,
            "additions": 100 + row_number,
            "deletions": 20,
            "change_size": 120 + row_number,
            "changed_files": 4,
            "commits": 2,
            "opened_weekday": created_at.weekday,
            "opened_hour": created_at.hour,
        },
        columns=PULL_REQUEST_COLUMNS,
    )
    if defer_training_labels:
        candidate_indexes = pulls.index[:64]
        cutoff = created_at[64]
        pulls.loc[candidate_indexes, "merged_at"] = cutoff + pd.Timedelta(hours=1)
        pulls.loc[candidate_indexes, "merge_hours"] = (
            pulls.loc[candidate_indexes, "merged_at"] - pulls.loc[candidate_indexes, "created_at"]
        ).dt.total_seconds() / 3_600

    workflow_count = max(pull_request_rows, 1)
    workflow_created_at = pd.date_range(
        "2025-01-01",
        periods=workflow_count,
        freq="6h",
        tz="UTC",
    )
    workflows = pd.DataFrame(
        {
            "repository": [
                "alpha/api" if index % 2 == 0 else "beta/web" for index in range(workflow_count)
            ],
            "run_id": range(2_001, 2_001 + workflow_count),
            "workflow_name": "CI",
            "status": "completed",
            "conclusion": [
                "success" if index % 4 else "failure" for index in range(workflow_count)
            ],
            "created_at": workflow_created_at,
            "updated_at": workflow_created_at + pd.Timedelta(minutes=10),
            "duration_minutes": 10.0,
        },
        columns=WORKFLOW_COLUMNS,
    )
    pull_path = data_dir / "pull_requests.csv"
    workflow_path = data_dir / "workflow_runs.csv"
    pulls.to_csv(pull_path, index=False, date_format="%Y-%m-%dT%H:%M:%SZ")
    workflows.to_csv(
        workflow_path,
        index=False,
        date_format="%Y-%m-%dT%H:%M:%SZ",
    )
    (data_dir / "metadata.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "generated_at_utc": "2026-07-26T00:00:00Z",
                "source": {
                    "provider": "github",
                    "visibility": "public",
                    "api": "rest",
                    "api_version": "2022-11-28",
                },
                "repositories": ["alpha/api", "beta/web"],
                "row_counts": {
                    "pull_requests": pull_request_rows,
                    "workflow_runs": workflow_count,
                },
                "collection": {
                    "pull_requests": {
                        "selection": "merged",
                        "limit_per_repository": 150,
                        "order": "api_default",
                    },
                    "workflow_runs": {
                        "selection": "completed",
                        "limit_per_repository": 150,
                        "order": "api_default",
                    },
                },
                "files": {
                    "pull_requests.csv": {
                        "sha256": _logical_csv_sha256(pull_path),
                    },
                    "workflow_runs.csv": {
                        "sha256": _logical_csv_sha256(workflow_path),
                    },
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
