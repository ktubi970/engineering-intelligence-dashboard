from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

CATEGORICAL_FEATURES = ("repository", "author_association")
NUMERIC_FEATURES = (
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
)
MODEL_FEATURES = (*CATEGORICAL_FEATURES, *NUMERIC_FEATURES)


class InsufficientTrainingDataError(ValueError):
    """Raised when the frame is too small for honest evaluation."""


@dataclass(frozen=True, slots=True)
class MergeTimeModel:
    pipeline: Pipeline

    def predict_hours(self, features: pd.DataFrame) -> np.ndarray:
        feature_frame = _select_features(features)
        log_predictions = self.pipeline.predict(feature_frame)
        return np.maximum(np.expm1(log_predictions), 0.0)


@dataclass(frozen=True, slots=True)
class ModelResult:
    model: MergeTimeModel
    mae_hours: float
    baseline_mae_hours: float
    test_rows: int
    feature_importance: dict[str, float]


def chronological_split(
    frame: pd.DataFrame,
    test_fraction: float = 0.2,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split rows into an older training set and a newer test set."""
    if len(frame) < 2:
        raise ValueError("Chronological splitting requires at least two rows.")

    ordered = frame.sort_values("created_at", kind="mergesort").reset_index(drop=True)
    split_at = int(len(ordered) * (1 - test_fraction))

    train = ordered.iloc[:split_at].copy()
    test = ordered.iloc[split_at:].copy()
    return train, test


def train_merge_time_model(frame: pd.DataFrame, min_samples: int = 80) -> ModelResult:
    if len(frame) < min_samples:
        raise InsufficientTrainingDataError(
            f"At least {min_samples} rows are required to train the merge-time model."
        )

    train, test = chronological_split(frame)
    preprocessor = _build_preprocessor()
    regressor = RandomForestRegressor(
        n_estimators=200,
        max_depth=8,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1,
    )
    pipeline = Pipeline(
        [
            ("preprocessor", preprocessor),
            ("regressor", regressor),
        ]
    )

    train_features = _select_features(train)
    test_features = _select_features(test)
    train_target = train["merge_hours"]
    test_target = test["merge_hours"]
    pipeline.fit(train_features, np.log1p(train_target))

    model = MergeTimeModel(pipeline)
    predictions = model.predict_hours(test_features)
    baseline = np.full(len(test), float(train_target.median()))

    return ModelResult(
        model=model,
        mae_hours=float(mean_absolute_error(test_target, predictions)),
        baseline_mae_hours=float(mean_absolute_error(test_target, baseline)),
        test_rows=len(test),
        feature_importance=_aggregate_feature_importance(pipeline),
    )


def _build_preprocessor() -> ColumnTransformer:
    numeric_pipeline = Pipeline([("imputer", SimpleImputer(strategy="median"))])
    categorical_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("one_hot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        [
            ("categorical", categorical_pipeline, list(CATEGORICAL_FEATURES)),
            ("numeric", numeric_pipeline, list(NUMERIC_FEATURES)),
        ]
    )


def _aggregate_feature_importance(pipeline: Pipeline) -> dict[str, float]:
    preprocessor = pipeline.named_steps["preprocessor"]
    regressor = pipeline.named_steps["regressor"]
    categorical_pipeline = preprocessor.named_transformers_["categorical"]
    encoder = categorical_pipeline.named_steps["one_hot"]

    importance = {feature: 0.0 for feature in MODEL_FEATURES}
    position = 0
    for feature, categories in zip(CATEGORICAL_FEATURES, encoder.categories_, strict=True):
        width = len(categories)
        importance[feature] = float(
            regressor.feature_importances_[position : position + width].sum()
        )
        position += width

    for feature, value in zip(
        NUMERIC_FEATURES,
        regressor.feature_importances_[position:],
        strict=True,
    ):
        importance[feature] = float(value)
    return importance


def _select_features(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [feature for feature in MODEL_FEATURES if feature not in frame]
    if missing:
        missing_names = ", ".join(missing)
        raise ValueError(f"Missing required model features: {missing_names}.")
    return frame.loc[:, MODEL_FEATURES]
