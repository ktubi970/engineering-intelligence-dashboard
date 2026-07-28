from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engineering_intelligence.model import (
    InsufficientTrainingDataError,
    ModelResult,
    chronological_split,
    train_merge_time_model,
)
from engineering_intelligence.pipeline import load_snapshot


@pytest.fixture(scope="module")
def model_frame() -> pd.DataFrame:
    row_number = pd.Series(range(100), dtype="int64")
    created_at = pd.date_range("2025-01-01", periods=100, freq="6h", tz="UTC")
    merge_hours = pd.Series([12.0, 30.0, 48.0, 66.0] * 25, dtype="float64")
    return pd.DataFrame(
        {
            "repository": ["example/service"] * 100,
            "number": 1_001 + row_number,
            "created_at": created_at,
            "merged_at": created_at + pd.to_timedelta(merge_hours, unit="h"),
            "merge_hours": merge_hours,
            "title_length": [20.0] * 100,
            "body_length": [100.0] * 100,
            "author_association": ["CONTRIBUTOR"] * 100,
            "labels_count": [1.0] * 100,
            "additions": [100.0] * 100,
            "deletions": [20.0] * 100,
            "change_size": [120.0] * 100,
            "changed_files": [4.0] * 100,
            "commits": [2.0] * 100,
            "opened_weekday": created_at.weekday,
            "opened_hour": created_at.hour,
        }
    )


@pytest.fixture(scope="module")
def trained_result(model_frame: pd.DataFrame) -> ModelResult:
    return train_merge_time_model(model_frame, min_samples=80)


def test_chronological_split_keeps_future_rows_out_of_training(
    model_frame: pd.DataFrame,
) -> None:
    shuffled = model_frame.sample(frac=1.0, random_state=7)

    train, test = chronological_split(shuffled, test_fraction=0.2)

    cutoff = test["created_at"].min()
    assert train["merged_at"].max() < cutoff <= test["created_at"].min()
    assert (len(train), len(test)) == (74, 20)


def test_chronological_split_preserves_input_order_for_equal_timestamps() -> None:
    frame = pd.DataFrame(
        {
            "created_at": pd.to_datetime(
                [
                    "2026-01-02T00:00:00Z",
                    "2026-01-01T00:00:00Z",
                    "2026-01-01T00:00:00Z",
                    "2026-01-03T00:00:00Z",
                ],
                utc=True,
            ),
            "merged_at": pd.to_datetime(
                [
                    "2026-01-02T01:00:00Z",
                    "2026-01-01T01:00:00Z",
                    "2026-01-01T02:00:00Z",
                    "2026-01-04T00:00:00Z",
                ],
                utc=True,
            ),
            "row_id": ["later", "first tie", "second tie", "latest"],
        }
    )

    train, test = chronological_split(frame, test_fraction=0.25)

    assert train["row_id"].tolist() == ["first tie", "second tie", "later"]
    assert test["row_id"].tolist() == ["latest"]


def test_chronological_split_rejects_fewer_than_two_rows(model_frame: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="at least two rows"):
        chronological_split(model_frame.head(1))


def test_trained_model_beats_median_baseline_on_predictable_data(
    trained_result: ModelResult,
) -> None:
    assert trained_result.cutoff == pd.Timestamp("2025-01-21T00:00:00Z")
    assert trained_result.train_rows == 74
    assert trained_result.test_rows == 20
    assert trained_result.purged_rows == 6
    assert trained_result.mae_hours < trained_result.baseline_mae_hours
    assert trained_result.feature_importance["opened_hour"] > 0
    assert set(trained_result.feature_importance) == {
        "repository",
        "number",
        "opened_year",
        "opened_month",
        "opened_day",
        "opened_weekday",
        "opened_hour",
    }
    assert sum(trained_result.feature_importance.values()) == pytest.approx(1.0)


def test_metrics_are_calculated_only_on_the_chronological_test_set(
    model_frame: pd.DataFrame,
    trained_result: ModelResult,
) -> None:
    _, test = chronological_split(model_frame, test_fraction=0.2)
    predictions = trained_result.model.predict_hours(test)
    expected_test_mae = float(np.abs(test["merge_hours"].to_numpy() - predictions).mean())

    assert trained_result.mae_hours == pytest.approx(expected_test_mae)
    assert trained_result.baseline_mae_hours == pytest.approx(18.0)


def test_training_rejects_too_few_rows(model_frame: pd.DataFrame) -> None:
    with pytest.raises(InsufficientTrainingDataError, match="80"):
        train_merge_time_model(model_frame.head(79), min_samples=80)


def test_training_requires_64_labels_known_by_cutoff_for_80_selected_rows(
    model_frame: pd.DataFrame,
) -> None:
    frame = model_frame.head(80).copy()
    candidate_indexes = frame.index[:64]
    cutoff = frame.iloc[64]["created_at"]
    frame.loc[candidate_indexes, "merged_at"] = frame.loc[
        candidate_indexes, "created_at"
    ] + pd.Timedelta(hours=1)
    frame.loc[candidate_indexes, "merge_hours"] = 1.0
    last_candidate = candidate_indexes[-1]
    frame.loc[last_candidate, "merged_at"] = cutoff + pd.Timedelta(hours=1)
    frame.loc[last_candidate, "merge_hours"] = 7.0

    with pytest.raises(
        InsufficientTrainingDataError,
        match="80 selected rows exist but too few labels were known by the cutoff",
    ) as captured:
        train_merge_time_model(frame, min_samples=80)

    assert (
        "63 time-safe training rows and 16 test rows are available; "
        "at least 64 training rows and 16 test rows are required"
    ) in str(captured.value)


def test_training_does_not_mutate_input(model_frame: pd.DataFrame) -> None:
    shuffled = model_frame.sample(frac=1.0, random_state=11)
    original = shuffled.copy(deep=True)

    train_merge_time_model(shuffled, min_samples=80)

    pd.testing.assert_frame_equal(shuffled, original)


def test_unknown_repository_and_missing_number_produce_non_negative_predictions(
    model_frame: pd.DataFrame,
    trained_result: ModelResult,
) -> None:
    features = model_frame.tail(1).copy()
    features["repository"] = "unseen/project"
    features["number"] = np.nan

    predictions = trained_result.model.predict_hours(features)

    assert predictions.shape == (1,)
    assert predictions[0] >= 0.0


def test_forbidden_fields_cannot_change_opening_time_predictions(
    model_frame: pd.DataFrame,
    trained_result: ModelResult,
) -> None:
    features = model_frame.tail(4).copy()
    expected = trained_result.model.predict_hours(features)
    probed = features.assign(
        merge_hours=[999_999.0, -999_999.0, 500_000.0, -500_000.0],
        title_length=[999_999.0, 1.0, 888_888.0, 2.0],
        body_length=[1.0, 999_999.0, 2.0, 888_888.0],
        author_association=["OWNER", "MEMBER", "NONE", "FIRST_TIMER"],
        labels_count=[999.0, 0.0, 888.0, 1.0],
        additions=[999_999.0, 0.0, 888_888.0, 1.0],
        deletions=[0.0, 999_999.0, 1.0, 888_888.0],
        change_size=[1.0, 2.0, 999_999.0, 888_888.0],
        changed_files=[999.0, 1.0, 888.0, 2.0],
        commits=[999.0, 1.0, 888.0, 2.0],
        opened_weekday=[6, 6, 6, 6],
        opened_hour=[1, 2, 3, 4],
        merged_at=pd.to_datetime(
            [
                "2035-01-01T00:00:00Z",
                "2036-01-01T00:00:00Z",
                "2037-01-01T00:00:00Z",
                "2038-01-01T00:00:00Z",
            ]
        ),
        future_outcome=[-1_000_000.0, 1_000_000.0, -2_000_000.0, 2_000_000.0],
        developer_performance_score=[-10.0, 10.0, -20.0, 20.0],
    )

    actual = trained_result.model.predict_hours(probed)

    np.testing.assert_allclose(actual, expected, rtol=0.0, atol=1e-12)


def test_training_is_deterministic_when_forbidden_probes_are_present(
    model_frame: pd.DataFrame,
    trained_result: ModelResult,
) -> None:
    probed = model_frame.assign(
        future_outcome=np.linspace(-1_000_000.0, 1_000_000.0, 100),
    )

    repeated = train_merge_time_model(probed, min_samples=80)
    prediction_features = model_frame.tail(5)

    np.testing.assert_allclose(
        repeated.model.predict_hours(prediction_features),
        trained_result.model.predict_hours(prediction_features),
        rtol=0.0,
        atol=1e-12,
    )
    assert repeated.mae_hours == pytest.approx(trained_result.mae_hours, abs=1e-12)
    assert repeated.baseline_mae_hours == trained_result.baseline_mae_hours
    assert repeated.feature_importance == pytest.approx(
        trained_result.feature_importance, abs=1e-12
    )


def test_mutating_labels_unavailable_at_cutoff_cannot_change_training_result() -> None:
    pulls, _, _ = load_snapshot(Path("data/snapshots"))
    ordered = pulls.sort_values("created_at", kind="mergesort")
    original = train_merge_time_model(pulls)
    split_at = len(pulls) - original.test_rows
    cutoff = ordered.iloc[split_at]["created_at"]
    unavailable = (pulls["created_at"] < cutoff) & (pulls["merged_at"] >= cutoff)
    assert int(unavailable.sum()) == original.purged_rows
    mutated = pulls.copy()
    mutated.loc[unavailable, "merge_hours"] += 1_000_000.0
    repeated = train_merge_time_model(mutated)
    test = ordered.iloc[split_at:]

    np.testing.assert_allclose(
        repeated.model.predict_hours(test),
        original.model.predict_hours(test),
        rtol=0.0,
        atol=1e-12,
    )
    assert repeated.mae_hours == pytest.approx(original.mae_hours, abs=1e-12)
    assert repeated.baseline_mae_hours == pytest.approx(
        original.baseline_mae_hours,
        abs=1e-12,
    )


@pytest.mark.parametrize("missing_column", ["repository", "number", "created_at"])
def test_prediction_rejects_missing_raw_opening_fields(
    model_frame: pd.DataFrame,
    trained_result: ModelResult,
    missing_column: str,
) -> None:
    incomplete = model_frame.tail(1).drop(columns=[missing_column])

    with pytest.raises(ValueError, match=missing_column):
        trained_result.model.predict_hours(incomplete)


def test_training_rejects_missing_raw_opening_fields(
    model_frame: pd.DataFrame,
) -> None:
    missing_number = model_frame.drop(columns=["number"])

    with pytest.raises(ValueError, match="number"):
        train_merge_time_model(missing_number, min_samples=80)


def test_fully_missing_training_repository_keeps_categorical_dimension(
    model_frame: pd.DataFrame,
) -> None:
    frame = model_frame.copy()
    frame.loc[:79, "repository"] = np.nan

    result = train_merge_time_model(frame, min_samples=80)
    predictions = result.model.predict_hours(frame.tail(1))

    assert result.feature_importance["repository"] == 0.0
    assert np.isfinite(predictions).all()


def test_fully_missing_training_number_keeps_numeric_dimension(
    model_frame: pd.DataFrame,
) -> None:
    frame = model_frame.copy()
    frame.loc[:79, "number"] = np.nan

    result = train_merge_time_model(frame, min_samples=80)
    predictions = result.model.predict_hours(frame.tail(1))

    assert result.feature_importance["number"] == 0.0
    assert np.isfinite(predictions).all()
