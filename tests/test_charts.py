from __future__ import annotations

import pandas as pd

from engineering_intelligence.charts import (
    feature_importance_figure,
    merge_time_trend_figure,
    repository_comparison_figure,
    size_delay_figure,
)

SAFE_COLORS = {
    "#0072B2",
    "#D55E00",
    "#009E73",
    "#CC79A7",
    "#E69F00",
    "#56B4E9",
}
EMPTY_MESSAGE = "Nothing to show for these filters."


def _pull_request_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "repository": ["alpha/api", "alpha/api", "beta/web", "beta/web"],
            "number": [101, 102, 201, 202],
            "merged_at": pd.to_datetime(
                [
                    "2026-01-05T12:00:00Z",
                    "2026-01-07T12:00:00Z",
                    "2026-01-12T12:00:00Z",
                    "2026-01-14T12:00:00Z",
                ],
                utc=True,
            ),
            "merge_hours": [12.0, 36.0, 24.0, 48.0],
            "change_size": [10, 100, 30, 300],
        }
    )


def test_merge_time_trend_has_accessible_labels_and_repository_hover() -> None:
    figure = merge_time_trend_figure(_pull_request_frame())

    assert figure.layout.title.text == "Typical merge time each week"
    assert figure.layout.xaxis.title.text == "Week"
    assert figure.layout.yaxis.title.text == "Hours to merge"
    assert {trace.name for trace in figure.data} == {"alpha/api", "beta/web"}
    assert all("Repository: %{fullData.name}" in trace.hovertemplate for trace in figure.data)
    assert all("Typical merge time: %{y:.1f} hours" in trace.hovertemplate for trace in figure.data)
    assert {trace.line.color for trace in figure.data}.issubset(SAFE_COLORS)


def test_size_delay_chart_is_explicitly_retrospective_and_has_value_hover() -> None:
    figure = size_delay_figure(_pull_request_frame())

    assert figure.layout.title.text == "Do larger changes take longer to merge?"
    assert figure.layout.xaxis.title.text == "Lines changed (added + deleted)"
    assert figure.layout.yaxis.title.text == "Hours to merge"
    assert {trace.name for trace in figure.data} == {"alpha/api", "beta/web"}
    assert all("Repository: %{fullData.name}" in trace.hovertemplate for trace in figure.data)
    assert all("Lines changed: %{x}" in trace.hovertemplate for trace in figure.data)
    assert all("Time to merge: %{y:.1f} hours" in trace.hovertemplate for trace in figure.data)
    assert {trace.marker.color for trace in figure.data}.issubset(SAFE_COLORS)


def test_repository_comparison_has_labels_and_repository_value_hover() -> None:
    figure = repository_comparison_figure(_pull_request_frame())

    assert figure.layout.title.text == "Typical merge time by repository"
    assert figure.layout.xaxis.title.text == "Repository"
    assert figure.layout.yaxis.title.text == "Hours to merge"
    assert len(figure.data) == 1
    assert figure.data[0].x.tolist() == ["alpha/api", "beta/web"]
    assert figure.data[0].y.tolist() == [24.0, 36.0]
    assert "Repository: %{x}" in figure.data[0].hovertemplate
    assert "Typical merge time: %{y:.1f} hours" in figure.data[0].hovertemplate
    assert set(figure.data[0].marker.color).issubset(SAFE_COLORS)


def test_feature_importance_has_labels_and_feature_value_hover() -> None:
    importance = pd.DataFrame(
        {
            "feature": ["repository", "opened_hour", "number"],
            "importance": [0.2, 0.5, 0.3],
        }
    )

    figure = feature_importance_figure(importance)

    assert figure.layout.title.text == "What the estimate relies on most"
    assert figure.layout.xaxis.title.text == "Relative influence"
    assert figure.layout.yaxis.title.text == "Input"
    assert len(figure.data) == 1
    assert figure.data[0].y.tolist() == ["repository", "number", "opened_hour"]
    assert "Input: %{y}" in figure.data[0].hovertemplate
    assert "Relative influence: %{x:.3f}" in figure.data[0].hovertemplate
    assert set(figure.data[0].marker.color).issubset(SAFE_COLORS)


def test_all_charts_show_a_readable_empty_state() -> None:
    empty_pulls = _pull_request_frame().head(0)
    empty_importance = pd.DataFrame(columns=["feature", "importance"])

    figures = [
        merge_time_trend_figure(empty_pulls),
        size_delay_figure(empty_pulls),
        repository_comparison_figure(empty_pulls),
        feature_importance_figure(empty_importance),
    ]

    for figure in figures:
        assert len(figure.data) == 0
        assert [annotation.text for annotation in figure.layout.annotations] == [EMPTY_MESSAGE]


def test_every_rendered_palette_color_has_three_to_one_contrast_on_white() -> None:
    repositories = [f"example/repository-{index}" for index in range(6)]
    frame = pd.DataFrame(
        {
            "repository": repositories,
            "merge_hours": [12.0, 18.0, 24.0, 30.0, 36.0, 42.0],
        }
    )

    figure = repository_comparison_figure(frame)
    rendered_colors = figure.data[0].marker.color

    assert len(rendered_colors) == 6
    assert all(_contrast_against_white(color) >= 3.0 for color in rendered_colors)


def _contrast_against_white(hex_color: str) -> float:
    red, green, blue = (int(hex_color[index : index + 2], 16) / 255 for index in (1, 3, 5))
    luminance = (
        0.2126 * _linear_channel(red)
        + 0.7152 * _linear_channel(green)
        + 0.0722 * _linear_channel(blue)
    )
    return 1.05 / (luminance + 0.05)


def _linear_channel(channel: float) -> float:
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4
