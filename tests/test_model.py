from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from engineering_intelligence.model import (
    InsufficientTrainingDataError,
    ModelResult,
    chronological_split,
    train_merge_time_model,
)


@pytest.fixture(scope="module")
def model_frame() -> pd.DataFrame:
    row_number = pd.Series(range(100), dtype="float64")
    return pd.DataFrame(
        {
            "repository": ["example/service"] * 100,
            "created_at": pd.date_range("2025-01-01", periods=100, tz="UTC"),
            "merge_hours": 6.0 + row_number * 1.5,
            "title_length": 10.0 + row_number,
            "body_length": 50.0 + row_number * 2.0,
            "author_association": ["CONTRIBUTOR"] * 100,
            "labels_count": row_number % 4,
            "additions": 20.0 + row_number * 3.0,
            "deletions": 5.0 + row_number,
            "change_size": 25.0 + row_number * 4.0,
            "changed_files": 1.0 + row_number % 8,
            "commits": 1.0 + row_number % 5,
            "opened_weekday": row_number % 7,
            "opened_hour": row_number % 24,
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

    assert train["created_at"].max() < test["created_at"].min()
    assert (len(train), len(test)) == (80, 20)


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
    assert trained_result.test_rows == 20
    assert trained_result.mae_hours < trained_result.baseline_mae_hours
    assert trained_result.feature_importance["change_size"] > 0
    assert set(trained_result.feature_importance) == {
        "repository",
        "author_association",
        "title_length",
        "body_length",
        "labels_count",
        "additions",
        "deletions",
        "change_size",
        "changed_files",
        "commits",
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
    assert trained_result.baseline_mae_hours == pytest.approx(75.0)


def test_training_rejects_too_few_rows(model_frame: pd.DataFrame) -> None:
    with pytest.raises(InsufficientTrainingDataError, match="80"):
        train_merge_time_model(model_frame.head(79), min_samples=80)


def test_training_does_not_mutate_input(model_frame: pd.DataFrame) -> None:
    shuffled = model_frame.sample(frac=1.0, random_state=11)
    original = shuffled.copy(deep=True)

    train_merge_time_model(shuffled, min_samples=80)

    pd.testing.assert_frame_equal(shuffled, original)


def test_unknown_categories_and_missing_numbers_produce_non_negative_predictions(
    model_frame: pd.DataFrame,
    trained_result: ModelResult,
) -> None:
    features = model_frame.tail(1).copy()
    features["repository"] = "unseen/project"
    features["author_association"] = "UNSEEN_ASSOCIATION"
    features["change_size"] = np.nan

    predictions = trained_result.model.predict_hours(features)

    assert predictions.shape == (1,)
    assert predictions[0] >= 0.0


def test_target_and_post_open_columns_are_excluded_from_predictions(
    model_frame: pd.DataFrame,
    trained_result: ModelResult,
) -> None:
    features = model_frame.tail(2).copy()
    expected = trained_result.model.predict_hours(features)
    probed = features.assign(
        merge_hours=[-999_999.0, 999_999.0],
        merged_at=pd.to_datetime(["2035-01-01T00:00:00Z", "2040-01-01T00:00:00Z"]),
        closed_at=pd.to_datetime(["2036-01-01T00:00:00Z", "2041-01-01T00:00:00Z"]),
        developer_performance_score=[-1_000_000.0, 1_000_000.0],
    )

    actual = trained_result.model.predict_hours(probed)

    np.testing.assert_allclose(actual, expected, rtol=0.0, atol=1e-12)


def test_training_is_deterministic_when_leakage_probes_are_present(
    model_frame: pd.DataFrame,
    trained_result: ModelResult,
) -> None:
    probed = model_frame.assign(
        merged_at=pd.date_range("2030-01-01", periods=100, tz="UTC"),
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


def test_prediction_rejects_missing_allowlisted_features(
    model_frame: pd.DataFrame,
    trained_result: ModelResult,
) -> None:
    missing_change_size = model_frame.tail(1).drop(columns=["change_size"])

    with pytest.raises(ValueError, match="change_size"):
        trained_result.model.predict_hours(missing_change_size)


def test_training_rejects_missing_allowlisted_features(
    model_frame: pd.DataFrame,
) -> None:
    missing_commits = model_frame.drop(columns=["commits"])

    with pytest.raises(ValueError, match="commits"):
        train_merge_time_model(missing_commits, min_samples=80)
