from dataclasses import asdict, dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class DeliveryMetrics:
    merged_pull_requests: int
    median_merge_hours: float | None
    p90_merge_hours: float | None
    average_weekly_throughput: float
    workflow_success_rate: float | None


def calculate_delivery_metrics(pulls: pd.DataFrame, workflows: pd.DataFrame) -> DeliveryMetrics:
    trend = weekly_delivery_trend(pulls)
    completed_workflows = _completed_workflows(workflows)

    return DeliveryMetrics(
        merged_pull_requests=len(pulls),
        median_merge_hours=(float(pulls["merge_hours"].median()) if not pulls.empty else None),
        p90_merge_hours=(
            float(pulls["merge_hours"].quantile(0.9, interpolation="linear"))
            if not pulls.empty
            else None
        ),
        average_weekly_throughput=(
            float(trend["merged_pull_requests"].mean()) if not trend.empty else 0.0
        ),
        workflow_success_rate=(
            float((completed_workflows["conclusion"] == "success").mean())
            if not completed_workflows.empty
            else None
        ),
    )


def weekly_delivery_trend(pulls: pd.DataFrame) -> pd.DataFrame:
    if pulls.empty:
        return pd.DataFrame(
            {
                "week_start": pd.Series(dtype="datetime64[ns, UTC]"),
                "merged_pull_requests": pd.Series(dtype="int64"),
                "median_merge_hours": pd.Series(dtype="float64"),
            }
        )

    return (
        pulls.assign(week_start=_week_start(pulls["merged_at"]))
        .groupby("week_start", as_index=False)
        .agg(
            merged_pull_requests=("merge_hours", "size"),
            median_merge_hours=("merge_hours", "median"),
        )
        .sort_values("week_start", ignore_index=True)
    )


def repository_summary(pulls: pd.DataFrame, workflows: pd.DataFrame) -> pd.DataFrame:
    repositories = sorted(set(pulls["repository"]) | set(workflows["repository"]))
    rows: list[dict[str, object]] = []
    for repository in repositories:
        metrics = calculate_delivery_metrics(
            pulls.loc[pulls["repository"] == repository],
            workflows.loc[workflows["repository"] == repository],
        )
        rows.append({"repository": repository, **asdict(metrics)})
    return pd.DataFrame(rows, columns=["repository", *DeliveryMetrics.__dataclass_fields__])


def _week_start(timestamps: pd.Series) -> pd.Series:
    return timestamps.dt.normalize() - pd.to_timedelta(timestamps.dt.weekday, unit="D")


def _completed_workflows(workflows: pd.DataFrame) -> pd.DataFrame:
    completed = workflows.loc[workflows["conclusion"].notna()]
    if "status" in completed:
        completed = completed.loc[completed["status"] == "completed"]
    return completed
