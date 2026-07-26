import pandas as pd
import pytest

from engineering_intelligence.metrics import (
    calculate_delivery_metrics,
    repository_summary,
    weekly_delivery_trend,
)


def test_calculate_delivery_metrics_uses_literal_expected_values() -> None:
    pulls = pd.DataFrame(
        {
            "merge_hours": [12.0, 24.0, 36.0, 48.0],
            "merged_at": pd.to_datetime(
                [
                    "2026-01-05T00:00:00Z",
                    "2026-01-06T00:00:00Z",
                    "2026-01-12T00:00:00Z",
                    "2026-01-13T00:00:00Z",
                ],
                utc=True,
            ),
        }
    )
    workflows = pd.DataFrame({"conclusion": ["success", "failure", "success"]})

    metrics = calculate_delivery_metrics(pulls, workflows)

    assert metrics.merged_pull_requests == 4
    assert metrics.median_merge_hours == 30.0
    assert metrics.p90_merge_hours == pytest.approx(44.4)
    assert metrics.average_weekly_throughput == 2.0
    assert metrics.workflow_success_rate == pytest.approx(2 / 3)


def test_calculate_delivery_metrics_handles_empty_data_without_division_by_zero() -> None:
    pulls = pd.DataFrame(
        {
            "merge_hours": pd.Series(dtype="float64"),
            "merged_at": pd.to_datetime([], utc=True),
        }
    )
    workflows = pd.DataFrame({"conclusion": pd.Series(dtype="object")})

    metrics = calculate_delivery_metrics(pulls, workflows)

    assert metrics.merged_pull_requests == 0
    assert metrics.median_merge_hours is None
    assert metrics.p90_merge_hours is None
    assert metrics.average_weekly_throughput == 0.0
    assert metrics.workflow_success_rate is None


def test_calculate_delivery_metrics_excludes_incomplete_or_unconcluded_workflows() -> None:
    pulls = pd.DataFrame(
        {
            "merge_hours": [12.0],
            "merged_at": pd.to_datetime(["2026-01-05T00:00:00Z"], utc=True),
        }
    )
    workflows = pd.DataFrame(
        {
            "status": ["completed", "completed", "completed", "in_progress"],
            "conclusion": ["success", "failure", None, "success"],
        }
    )

    metrics = calculate_delivery_metrics(pulls, workflows)

    assert metrics.workflow_success_rate == 0.5


def test_weekly_delivery_trend_uses_utc_monday_week_boundaries() -> None:
    pulls = pd.DataFrame(
        {
            "merge_hours": [10.0, 30.0, 50.0],
            "merged_at": pd.to_datetime(
                [
                    "2026-01-11T23:59:00Z",
                    "2026-01-12T00:00:00Z",
                    "2026-01-18T23:59:00Z",
                ],
                utc=True,
            ),
        }
    )

    trend = weekly_delivery_trend(pulls)

    assert trend["week_start"].tolist() == [
        pd.Timestamp("2026-01-05T00:00:00Z"),
        pd.Timestamp("2026-01-12T00:00:00Z"),
    ]
    assert trend["merged_pull_requests"].tolist() == [1, 2]
    assert trend["median_merge_hours"].tolist() == [10.0, 40.0]


def test_repository_summary_groups_pull_and_workflow_metrics_by_repository() -> None:
    pulls = pd.DataFrame(
        {
            "repository": ["alpha/api", "alpha/api", "beta/web"],
            "merge_hours": [12.0, 36.0, 48.0],
            "merged_at": pd.to_datetime(
                [
                    "2026-01-05T00:00:00Z",
                    "2026-01-06T00:00:00Z",
                    "2026-01-12T00:00:00Z",
                ],
                utc=True,
            ),
        }
    )
    workflows = pd.DataFrame(
        {
            "repository": ["alpha/api", "alpha/api", "beta/web"],
            "status": ["completed", "completed", "completed"],
            "conclusion": ["success", "failure", "success"],
        }
    )

    summary = repository_summary(pulls, workflows)

    assert summary["repository"].tolist() == ["alpha/api", "beta/web"]
    assert summary["merged_pull_requests"].tolist() == [2, 1]
    assert summary["median_merge_hours"].tolist() == [24.0, 48.0]
    assert summary["p90_merge_hours"].tolist() == pytest.approx([33.6, 48.0])
    assert summary["average_weekly_throughput"].tolist() == [2.0, 1.0]
    assert summary["workflow_success_rate"].tolist() == [0.5, 1.0]
