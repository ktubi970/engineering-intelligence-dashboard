from __future__ import annotations

import os
from datetime import UTC, date, datetime, time
from pathlib import Path

import pandas as pd
import streamlit as st

from engineering_intelligence.charts import (
    feature_importance_figure,
    merge_time_trend_figure,
    repository_comparison_figure,
    size_delay_figure,
)
from engineering_intelligence.domain import DataContractError
from engineering_intelligence.metrics import calculate_delivery_metrics
from engineering_intelligence.model import (
    InsufficientTrainingDataError,
    ModelResult,
    train_merge_time_model,
)
from engineering_intelligence.pipeline import load_snapshot

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "snapshots"
FORECAST_WARNING = (
    "Experimental estimate — not a delivery promise or an explanation of cause. "
    "Never use it to score developers."
)


def resolve_data_dir() -> Path:
    return Path(os.environ.get("EID_DATA_DIR", DEFAULT_DATA_DIR))


def render_dashboard(data_dir: Path) -> None:
    st.set_page_config(page_title="MergeLens", page_icon="◈", layout="wide")
    st.title("MergeLens")
    st.caption(
        "Explore how pull requests move through public repositories—"
        "without tracking individual developers."
    )

    try:
        pulls, workflows, metadata = load_snapshot(data_dir)
    except (DataContractError, OSError, ValueError) as error:
        st.error(
            "MergeLens couldn't load its local data. "
            f"Check the snapshot files and try again. Details: {error}"
        )
        return

    st.sidebar.header("Filter the view")
    filtered_pulls, filtered_workflows = _render_filters(pulls, workflows)
    generated_at = metadata.get("generated_at_utc", "unknown")
    st.sidebar.caption(f"Snapshot updated: {generated_at}")

    delivery_tab, bottlenecks_tab, forecast_tab = st.tabs(
        [
            "Delivery overview",
            "Where work slows down",
            "Merge-time estimate",
        ]
    )
    with delivery_tab:
        _render_delivery_pulse(filtered_pulls, filtered_workflows)
    with bottlenecks_tab:
        _render_bottlenecks(filtered_pulls)
    with forecast_tab:
        _render_forecast(filtered_pulls)


def opening_feature_frame(
    repository: str,
    pull_request_number: int,
    opening_date: date,
    opening_time: time,
) -> pd.DataFrame:
    created_at = datetime.combine(opening_date, opening_time, tzinfo=UTC)
    return pd.DataFrame(
        {
            "repository": [repository],
            "number": [pull_request_number],
            "created_at": [created_at],
        }
    )


def evaluation_summary(
    model_mae: float,
    baseline_mae: float,
) -> tuple[str, str]:
    if model_mae < baseline_mae:
        return (
            "success",
            "Model wins: its MAE is lower than the train-median baseline "
            f"({model_mae:.1f} vs {baseline_mae:.1f} hours).",
        )
    if baseline_mae < model_mae:
        return (
            "info",
            "Train-median baseline wins: its MAE is lower than the model "
            f"({baseline_mae:.1f} vs {model_mae:.1f} hours).",
        )
    return (
        "info",
        f"Tie: model and train-median baseline MAE are equal at {model_mae:.1f} hours.",
    )


def preferred_forecast(model_mae: float, baseline_mae: float) -> str:
    """Choose the lower-error estimate, defaulting a tie to the simpler baseline."""
    return "random forest" if model_mae < baseline_mae else "train-median baseline"


def _render_filters(
    pulls: pd.DataFrame,
    workflows: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    repositories = sorted(set(pulls["repository"]) | set(workflows["repository"]))
    selected_repositories = st.sidebar.multiselect(
        "Repositories",
        repositories,
        default=repositories,
    )
    filtered_pulls = pulls.loc[pulls["repository"].isin(selected_repositories)].copy()
    filtered_workflows = workflows.loc[workflows["repository"].isin(selected_repositories)].copy()

    timestamp_bounds = [
        (pulls["merged_at"].min(), pulls["merged_at"].max()) if not pulls.empty else None,
        (
            workflows["created_at"].min(),
            workflows["created_at"].max(),
        )
        if not workflows.empty
        else None,
    ]
    populated_bounds = [bounds for bounds in timestamp_bounds if bounds is not None]
    if not populated_bounds:
        st.sidebar.caption("No delivery records are available for this snapshot.")
        return filtered_pulls, filtered_workflows

    minimum_date = min(bounds[0] for bounds in populated_bounds).date()
    maximum_date = max(bounds[1] for bounds in populated_bounds).date()
    selected_dates = st.sidebar.date_input(
        "Merged between",
        value=(minimum_date, maximum_date),
        min_value=minimum_date,
        max_value=maximum_date,
    )
    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
        start = pd.Timestamp(start_date, tz="UTC")
        end = pd.Timestamp(end_date, tz="UTC") + pd.Timedelta(days=1)
        filtered_pulls = filtered_pulls.loc[
            (filtered_pulls["merged_at"] >= start) & (filtered_pulls["merged_at"] < end)
        ].copy()
        filtered_workflows = filtered_workflows.loc[
            (filtered_workflows["created_at"] >= start) & (filtered_workflows["created_at"] < end)
        ].copy()
    return filtered_pulls, filtered_workflows


def _render_delivery_pulse(pulls: pd.DataFrame, workflows: pd.DataFrame) -> None:
    metrics = calculate_delivery_metrics(pulls, workflows)
    columns = st.columns(4)
    columns[0].metric("PRs merged", f"{metrics.merged_pull_requests:,}")
    columns[1].metric("Typical merge time", _format_hours(metrics.median_merge_hours))
    columns[2].metric("90% merged within", _format_hours(metrics.p90_merge_hours))
    columns[3].metric("Successful workflows", _format_rate(metrics.workflow_success_rate))
    st.caption(
        "Typical is the median. “90% merged within” is the P90: "
        "nine out of ten PRs merged in that time or less."
    )

    if pulls.empty:
        st.info(
            "No pull requests match these filters. "
            "Try a wider date range or another repository."
        )
    st.subheader("Merge time by week")
    st.plotly_chart(merge_time_trend_figure(pulls), width="stretch")


def _render_bottlenecks(pulls: pd.DataFrame) -> None:
    st.subheader("Patterns worth exploring")
    st.caption(
        "These charts show patterns in past data. "
        "They do not prove why a pull request took longer."
    )
    st.plotly_chart(size_delay_figure(pulls), width="stretch")
    st.plotly_chart(repository_comparison_figure(pulls), width="stretch")


def _render_forecast(pulls: pd.DataFrame) -> None:
    st.warning(FORECAST_WARNING)
    st.subheader("Model evaluation")
    try:
        result = train_merge_time_model(pulls)
    except InsufficientTrainingDataError:
        st.info(
            "At least 80 pull requests are required for an honest chronological "
            "model evaluation. Forecasting is unavailable for this selection."
        )
        return

    _render_evaluation(result)
    importance = pd.DataFrame(
        {
            "feature": list(result.feature_importance),
            "importance": list(result.feature_importance.values()),
        }
    )
    st.plotly_chart(feature_importance_figure(importance), width="stretch")

    st.subheader("What-if forecast")
    st.caption(
        "Target: estimated merge time among pull requests that eventually merge. "
        "Inputs are available when the pull request opens."
    )
    repositories = sorted(pulls["repository"].unique())
    latest_opening = pulls["created_at"].max().to_pydatetime()
    with st.form("opening-time-forecast"):
        repository = st.selectbox("Forecast repository", repositories)
        pull_request_number = st.number_input(
            "Pull request number",
            min_value=1,
            value=int(pulls["number"].max()) + 1,
            step=1,
        )
        opening_date = st.date_input("Opening date (UTC)", value=latest_opening.date())
        opening_time = st.time_input(
            "Opening time (UTC)",
            value=latest_opening.time().replace(tzinfo=None),
        )
        submitted = st.form_submit_button("Forecast merge time")

    if submitted:
        features = opening_feature_frame(
            repository,
            int(pull_request_number),
            opening_date,
            opening_time,
        )
        model_prediction = float(result.model.predict_hours(features)[0])
        baseline_message = (
            f"Train-median baseline estimate: {result.baseline_hours:.1f} hours\n\n"
            f"Held-out MAE: {result.baseline_mae_hours:.1f} hours — "
            "empirical error context, not a prediction interval."
        )
        model_message = (
            f"Experimental random-forest estimate: {model_prediction:.1f} hours\n\n"
            f"Held-out MAE: {result.mae_hours:.1f} hours — "
            "empirical error context, not a prediction interval."
        )
        estimate_columns = st.columns(2)
        if (
            preferred_forecast(result.mae_hours, result.baseline_mae_hours)
            == "train-median baseline"
        ):
            estimate_columns[0].success(f"Validated default — {baseline_message}")
            estimate_columns[1].info(model_message)
        else:
            estimate_columns[0].info(baseline_message)
            estimate_columns[1].success(f"Validated default — {model_message}")


def _render_evaluation(result: ModelResult) -> None:
    columns = st.columns(4)
    columns[0].markdown(f"**Model MAE**\n\n{result.mae_hours:.1f} hours")
    columns[1].markdown(f"**Train-median baseline MAE**\n\n{result.baseline_mae_hours:.1f} hours")
    columns[2].markdown(f"**Time-safe training rows**\n\n{result.train_rows:,}")
    columns[3].markdown(f"**Chronological test rows**\n\n{result.test_rows:,}")
    st.caption(
        f"As-of cutoff: {result.cutoff.isoformat()} · "
        f"Purged labels unavailable at cutoff: {result.purged_rows:,}."
    )

    level, message = evaluation_summary(result.mae_hours, result.baseline_mae_hours)
    if level == "success":
        st.success(message)
    else:
        st.info(message)


def _format_hours(value: float | None) -> str:
    return "—" if value is None else f"{value:.1f} h"


def _format_rate(value: float | None) -> str:
    return "—" if value is None else f"{value:.1%}"
