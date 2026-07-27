from __future__ import annotations

from itertools import cycle

import pandas as pd
import plotly.graph_objects as go

from engineering_intelligence.metrics import weekly_delivery_trend

COLORBLIND_PALETTE = (
    "#0072B2",
    "#D55E00",
    "#009E73",
    "#CC79A7",
    "#A66F00",
    "#2A7FA8",
)
EMPTY_MESSAGE = "No data available for the selected filters."

HIGH_CONTRAST_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        colorway=list(COLORBLIND_PALETTE),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font={"color": "#17223B"},
        hoverlabel={"bgcolor": "#17223B", "font": {"color": "#FFFFFF"}},
        xaxis={"gridcolor": "#D9E0EA", "linecolor": "#5B6472"},
        yaxis={"gridcolor": "#D9E0EA", "linecolor": "#5B6472"},
    )
)


def merge_time_trend_figure(frame: pd.DataFrame) -> go.Figure:
    figure = _base_figure("Weekly merge time", "Week", "Median hours")
    if frame.empty:
        return _with_empty_state(figure)

    colors = cycle(COLORBLIND_PALETTE)
    for repository in sorted(frame["repository"].unique()):
        repository_frame = frame.loc[frame["repository"] == repository]
        trend = weekly_delivery_trend(repository_frame)
        figure.add_trace(
            go.Scatter(
                x=trend["week_start"],
                y=trend["median_merge_hours"],
                name=repository,
                mode="lines+markers",
                line={"color": next(colors), "width": 3},
                hovertemplate=(
                    "Repository: %{fullData.name}<br>"
                    "Week: %{x|%Y-%m-%d}<br>"
                    "Median merge time: %{y:.1f} hours<extra></extra>"
                ),
            )
        )
    return figure


def size_delay_figure(frame: pd.DataFrame) -> go.Figure:
    figure = _base_figure(
        "Change size and merge delay — retrospective only",
        "Change size (additions + deletions)",
        "Merge hours",
    )
    if frame.empty:
        return _with_empty_state(figure)

    colors = cycle(COLORBLIND_PALETTE)
    for repository in sorted(frame["repository"].unique()):
        repository_frame = frame.loc[frame["repository"] == repository]
        figure.add_trace(
            go.Scatter(
                x=repository_frame["change_size"],
                y=repository_frame["merge_hours"],
                customdata=repository_frame[["number"]],
                name=repository,
                mode="markers",
                marker={"color": next(colors), "size": 10, "opacity": 0.8},
                hovertemplate=(
                    "Repository: %{fullData.name}<br>"
                    "Pull request: #%{customdata[0]}<br>"
                    "Change size: %{x}<br>"
                    "Merge delay: %{y:.1f} hours<extra></extra>"
                ),
            )
        )
    return figure


def repository_comparison_figure(frame: pd.DataFrame) -> go.Figure:
    figure = _base_figure(
        "Median merge time by repository",
        "Repository",
        "Median hours",
    )
    if frame.empty:
        return _with_empty_state(figure)

    summary = (
        frame.groupby("repository", as_index=False)
        .agg(median_merge_hours=("merge_hours", "median"))
        .sort_values("repository", ignore_index=True)
    )
    colors = [COLORBLIND_PALETTE[index % len(COLORBLIND_PALETTE)] for index in range(len(summary))]
    figure.add_trace(
        go.Bar(
            x=summary["repository"],
            y=summary["median_merge_hours"],
            marker={"color": colors},
            hovertemplate=("Repository: %{x}<br>Median merge time: %{y:.1f} hours<extra></extra>"),
        )
    )
    return figure


def feature_importance_figure(frame: pd.DataFrame) -> go.Figure:
    figure = _base_figure("Global feature importance", "Importance", "Feature")
    if frame.empty:
        return _with_empty_state(figure)

    ordered = frame.sort_values("importance", ignore_index=True)
    colors = [COLORBLIND_PALETTE[index % len(COLORBLIND_PALETTE)] for index in range(len(ordered))]
    figure.add_trace(
        go.Bar(
            x=ordered["importance"],
            y=ordered["feature"],
            orientation="h",
            marker={"color": colors},
            hovertemplate="Feature: %{y}<br>Importance: %{x:.3f}<extra></extra>",
        )
    )
    return figure


def _base_figure(title: str, xaxis_title: str, yaxis_title: str) -> go.Figure:
    figure = go.Figure()
    figure.update_layout(
        template=HIGH_CONTRAST_TEMPLATE,
        title={"text": title},
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title,
        legend_title_text="Repository",
        margin={"l": 50, "r": 30, "t": 70, "b": 50},
    )
    return figure


def _with_empty_state(figure: go.Figure) -> go.Figure:
    figure.add_annotation(
        text=EMPTY_MESSAGE,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": 16, "color": "#17223B"},
    )
    return figure
