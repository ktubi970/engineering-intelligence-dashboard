from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

RAW_FEATURES = ("repository", "number", "created_at")
CATEGORICAL_FEATURES = ("repository",)
NUMERIC_FEATURES = (
    "number",
    "opened_year",
    "opened_month",
    "opened_day",
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
        feature_frame = _derive_features(features)
        log_predictions = self.pipeline.predict(feature_frame)
        return np.maximum(np.expm1(log_predictions), 0.0)


@dataclass(frozen=True, slots=True)
class ModelResult:
    model: MergeTimeModel
    mae_hours: float
    baseline_mae_hours: float
    baseline_hours: float
    cutoff: pd.Timestamp
    train_rows: int
    test_rows: int
    purged_rows: int
    feature_importance: dict[str, float]


def chronological_split(
    frame: pd.DataFrame,
    test_fraction: float = 0.2,
    min_samples: int = 2,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Hold out the newest openings and keep only labels known at that cutoff."""
    if len(frame) < 2:
        raise ValueError("Chronological splitting requires at least two rows.")

    ordered = frame.sort_values("created_at", kind="mergesort").reset_index(drop=True)
    split_at = int(len(ordered) * (1 - test_fraction))

    test = ordered.iloc[split_at:].copy()
    cutoff = pd.to_datetime(test["created_at"], utc=True).min()
    train_candidates = ordered.iloc[:split_at]
    available_labels = pd.to_datetime(train_candidates["merged_at"], utc=True) < cutoff
    train = train_candidates.loc[available_labels].copy()

    minimum_train_rows = floor((1 - test_fraction) * min_samples)
    minimum_test_rows = ceil(test_fraction * min_samples)
    if len(train) < minimum_train_rows or len(test) < minimum_test_rows:
        raise InsufficientTrainingDataError(
            f"{len(frame)} selected rows exist but too few labels were known by the cutoff "
            f"{cutoff.isoformat()}. {len(train)} time-safe training rows and "
            f"{len(test)} test rows are available; at least {minimum_train_rows} "
            f"training rows and {minimum_test_rows} test rows are required."
        )

    max_train_merged_at = pd.to_datetime(train["merged_at"], utc=True).max()
    min_test_created_at = pd.to_datetime(test["created_at"], utc=True).min()
    assert max_train_merged_at < cutoff <= min_test_created_at
    return train, test


def train_merge_time_model(frame: pd.DataFrame, min_samples: int = 80) -> ModelResult:
    if len(frame) < min_samples:
        raise InsufficientTrainingDataError(
            f"At least {min_samples} rows are required to train the merge-time model."
        )

    train, test = chronological_split(frame, min_samples=min_samples)
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

    train_features = _derive_features(train)
    train_target = train["merge_hours"]
    test_target = test["merge_hours"]
    pipeline.fit(train_features, np.log1p(train_target))

    model = MergeTimeModel(pipeline)
    predictions = model.predict_hours(test)
    baseline_hours = float(train_target.median())
    baseline = np.full(len(test), baseline_hours)
    cutoff = pd.to_datetime(test["created_at"], utc=True).min()

    return ModelResult(
        model=model,
        mae_hours=float(mean_absolute_error(test_target, predictions)),
        baseline_mae_hours=float(mean_absolute_error(test_target, baseline)),
        baseline_hours=baseline_hours,
        cutoff=cutoff,
        train_rows=len(train),
        test_rows=len(test),
        purged_rows=len(frame) - len(train) - len(test),
        feature_importance=_aggregate_feature_importance(pipeline),
    )


def _build_preprocessor() -> ColumnTransformer:
    numeric_pipeline = Pipeline(
        [("imputer", SimpleImputer(strategy="median", keep_empty_features=True))]
    )
    categorical_pipeline = Pipeline(
        [
            (
                "imputer",
                SimpleImputer(strategy="most_frequent", keep_empty_features=True),
            ),
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


def _derive_features(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [feature for feature in RAW_FEATURES if feature not in frame]
    if missing:
        missing_names = ", ".join(missing)
        raise ValueError(f"Missing required model fields: {missing_names}.")

    created_at = pd.to_datetime(frame["created_at"], utc=True)
    return pd.DataFrame(
        {
            "repository": frame["repository"],
            "number": frame["number"],
            "opened_year": created_at.dt.year,
            "opened_month": created_at.dt.month,
            "opened_day": created_at.dt.day,
            "opened_weekday": created_at.dt.weekday,
            "opened_hour": created_at.dt.hour,
        },
        index=frame.index,
    )
