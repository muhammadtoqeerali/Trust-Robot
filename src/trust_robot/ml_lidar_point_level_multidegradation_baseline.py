"""TRAIN-only multi-degradation LiDAR baseline.

Primary learning task
---------------------
Binary classification:

    0 = CLEAN
    1 = synthetic degraded

Synthetic degraded families:

    POINT_DROPOUT
    XYZ_GAUSSIAN_NOISE
    AZIMUTH_SECTOR_OCCLUSION

All model fitting is restricted to development_train trajectories.

development_check trajectories are used for reporting only.

These labels are synthetic intervention truth, not real sensor-health truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence
import json
import math

import numpy as np

from sklearn.base import BaseEstimator
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


CONFIG_SCHEMA = (
    "TRUST_ROBOT_M2DGR_LIDAR_POINT_LEVEL_MULTIDEGRADATION_BASELINE_CONFIG_V1"
)

RESULT_SCHEMA = (
    "TRUST_ROBOT_M2DGR_LIDAR_POINT_LEVEL_MULTIDEGRADATION_BASELINE_RESULTS_V1"
)

FEATURE_NAMES = (
    "source_point_count",
    "target_point_count",
    "fixed_point_iterations",
    "final_correspondence_count",
    "final_nearest_neighbor_rmse_m",
)

FEATURE_COUNT = 5

DEGRADATION_FAMILIES = (
    "POINT_DROPOUT",
    "XYZ_GAUSSIAN_NOISE",
    "AZIMUTH_SECTOR_OCCLUSION",
)

MODEL_NAMES = (
    "logistic_regression",
    "random_forest",
    "histogram_gradient_boosting",
)

PROBABILITY_THRESHOLD = 0.5
RANDOM_SEED = 20260928

DEVELOPMENT_TRAIN = (
    "Circle_01",
    "door_01",
    "gate_01",
    "hall_01",
    "hall_03",
    "hall_04",
    "lift_02",
    "room_02",
    "room_dark_01",
    "room_dark_02",
    "room_dark_03",
    "street_01",
    "street_03",
    "street_04",
    "street_05",
    "street_07",
    "walk_01",
)

DEVELOPMENT_CHECK = (
    "hall_05",
    "lift_04",
    "room_dark_04",
    "street_010",
    "street_09",
)


class MLLidarPointLevelBaselineError(
    ValueError
):
    pass


@dataclass(
    frozen=True
)
class LoadedDataset:
    X: np.ndarray

    y: np.ndarray

    families: tuple[str, ...]

    trajectories: tuple[str, ...]

    window_keys: tuple[
        tuple[
            str,
            int,
        ],
        ...
    ]

    sample_ids: tuple[str, ...]


def canonical_json_bytes(
    payload: Mapping[str, Any],
) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def content_sha256(
    payload: Mapping[str, Any],
) -> str:
    value = dict(payload)
    value.pop(
        "content_sha256",
        None,
    )

    return sha256(
        canonical_json_bytes(value)
    ).hexdigest()


def validate_config(
    payload: Mapping[str, Any],
) -> None:
    if payload.get(
        "schema"
    ) != CONFIG_SCHEMA:
        raise MLLidarPointLevelBaselineError(
            "config schema mismatch"
        )

    if payload.get(
        "schema_version"
    ) != 1:
        raise MLLidarPointLevelBaselineError(
            "config version mismatch"
        )

    if payload.get(
        "content_sha256"
    ) != content_sha256(
        payload
    ):
        raise MLLidarPointLevelBaselineError(
            "config content digest mismatch"
        )

    if tuple(
        payload.get(
            "feature_names",
            (),
        )
    ) != FEATURE_NAMES:
        raise MLLidarPointLevelBaselineError(
            "feature contract changed"
        )

    if tuple(
        payload.get(
            "degradation_families",
            (),
        )
    ) != DEGRADATION_FAMILIES:
        raise MLLidarPointLevelBaselineError(
            "degradation-family contract changed"
        )

    if tuple(
        payload.get(
            "model_names",
            (),
        )
    ) != MODEL_NAMES:
        raise MLLidarPointLevelBaselineError(
            "model set changed"
        )

    if payload.get(
        "probability_threshold"
    ) != PROBABILITY_THRESHOLD:
        raise MLLidarPointLevelBaselineError(
            "probability threshold changed"
        )

    if payload.get(
        "random_seed"
    ) != RANDOM_SEED:
        raise MLLidarPointLevelBaselineError(
            "random seed changed"
        )

    split = payload.get(
        "development_split"
    )

    if tuple(
        split.get(
            "development_train",
            (),
        )
    ) != DEVELOPMENT_TRAIN:
        raise MLLidarPointLevelBaselineError(
            "development_train changed"
        )

    if tuple(
        split.get(
            "development_check",
            (),
        )
    ) != DEVELOPMENT_CHECK:
        raise MLLidarPointLevelBaselineError(
            "development_check changed"
        )

    if set(
        DEVELOPMENT_TRAIN
    ) & set(
        DEVELOPMENT_CHECK
    ):
        raise MLLidarPointLevelBaselineError(
            "trajectory leakage"
        )

    policy = payload.get(
        "selection_policy"
    )

    for field in (
        "hyperparameter_search_executed",
        "model_family_selection_executed",
        "final_health_model_selected",
        "VALIDATION_used",
        "CONFIRMATION_used",
        "reference_data_used",
        "real_health_labels_used",
    ):
        if policy.get(field) is not False:
            raise MLLidarPointLevelBaselineError(
                field
                + " must remain false"
            )


def _allowed_trajectories(
    partition: str,
) -> tuple[str, ...]:
    if partition == "development_train":
        return DEVELOPMENT_TRAIN

    if partition == "development_check":
        return DEVELOPMENT_CHECK

    raise MLLidarPointLevelBaselineError(
        "unknown partition"
    )


def load_dataset(
    path: Path,
    *,
    expected_partition: str,
) -> LoadedDataset:
    allowed = set(
        _allowed_trajectories(
            expected_partition
        )
    )

    X = []
    y = []
    families = []
    trajectories = []
    window_keys = []
    sample_ids = []

    per_window_families = {}

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        for raw_line in handle:
            if not raw_line.strip():
                raise MLLidarPointLevelBaselineError(
                    "blank dataset line"
                )

            sample = json.loads(
                raw_line
            )

            if sample.get(
                "outer_split"
            ) != "TRAIN":
                raise MLLidarPointLevelBaselineError(
                    "non-TRAIN sample"
                )

            if sample.get(
                "development_partition"
            ) != expected_partition:
                raise MLLidarPointLevelBaselineError(
                    "partition mismatch"
                )

            trajectory = sample.get(
                "trajectory"
            )

            if trajectory not in allowed:
                raise MLLidarPointLevelBaselineError(
                    "trajectory crossed partition"
                )

            if sample.get(
                "feature_names"
            ) != list(
                FEATURE_NAMES
            ):
                raise MLLidarPointLevelBaselineError(
                    "feature order changed"
                )

            values = sample.get(
                "feature_values"
            )

            if (
                not isinstance(
                    values,
                    list,
                )
                or len(values)
                != FEATURE_COUNT
            ):
                raise MLLidarPointLevelBaselineError(
                    "feature vector length mismatch"
                )

            numeric = [
                float(value)
                for value
                in values
            ]

            if not all(
                math.isfinite(value)
                for value
                in numeric
            ):
                raise MLLidarPointLevelBaselineError(
                    "non-finite feature"
                )

            family = sample.get(
                "degradation_family"
            )

            if family not in (
                "CLEAN",
                *DEGRADATION_FAMILIES,
            ):
                raise MLLidarPointLevelBaselineError(
                    "unknown degradation family"
                )

            binary_label = sample.get(
                "binary_degraded_label"
            )

            expected_label = (
                0
                if family == "CLEAN"
                else 1
            )

            if binary_label != expected_label:
                raise MLLidarPointLevelBaselineError(
                    "binary label / family mismatch"
                )

            for field in (
                "trajectory_identity_is_model_feature",
                "window_index_is_model_feature",
                "corruption_family_is_model_feature",
                "corruption_parameters_are_model_features",
                "timestamps_are_model_features",
                "reference_data_used",
                "validation_data_used",
                "confirmation_data_used",
                "label_is_real_physical_health_truth",
            ):
                if sample.get(field) is not False:
                    raise MLLidarPointLevelBaselineError(
                        field
                        + " must remain false"
                    )

            start = sample.get(
                "window_start_scan_index"
            )

            if (
                type(start) is not int
                or start < 0
            ):
                raise MLLidarPointLevelBaselineError(
                    "window start invalid"
                )

            key = (
                trajectory,
                start,
            )

            per_window_families.setdefault(
                key,
                set(),
            ).add(
                family
            )

            sample_id = sample.get(
                "sample_id"
            )

            if (
                not isinstance(
                    sample_id,
                    str,
                )
                or not sample_id
            ):
                raise MLLidarPointLevelBaselineError(
                    "sample id missing"
                )

            X.append(numeric)
            y.append(expected_label)
            families.append(family)
            trajectories.append(
                trajectory
            )
            window_keys.append(key)
            sample_ids.append(sample_id)

    if not X:
        raise MLLidarPointLevelBaselineError(
            "empty dataset"
        )

    expected_family_set = {
        "CLEAN",
        *DEGRADATION_FAMILIES,
    }

    for key, family_set in (
        per_window_families.items()
    ):
        if family_set != expected_family_set:
            raise MLLidarPointLevelBaselineError(
                "incomplete degradation family set "
                + repr(key)
            )

    matrix = np.asarray(
        X,
        dtype=np.float64,
    )

    labels = np.asarray(
        y,
        dtype=np.int64,
    )

    if set(
        np.unique(labels).tolist()
    ) != {
        0,
        1,
    }:
        raise MLLidarPointLevelBaselineError(
            "both binary classes required"
        )

    return LoadedDataset(
        X=
            matrix,

        y=
            labels,

        families=
            tuple(families),

        trajectories=
            tuple(trajectories),

        window_keys=
            tuple(window_keys),

        sample_ids=
            tuple(sample_ids),
    )


def build_models(
) -> dict[
    str,
    BaseEstimator,
]:
    return {
        "logistic_regression":
            Pipeline(
                steps=[
                    (
                        "scale",
                        StandardScaler(),
                    ),
                    (
                        "model",
                        LogisticRegression(
                            C=1.0,
                            solver="lbfgs",
                            max_iter=1000,
                            random_state=
                                RANDOM_SEED,
                        ),
                    ),
                ]
            ),

        "random_forest":
            RandomForestClassifier(
                n_estimators=128,
                max_depth=16,
                min_samples_leaf=4,
                max_features="sqrt",
                random_state=
                    RANDOM_SEED,
                n_jobs=1,
            ),

        "histogram_gradient_boosting":
            HistGradientBoostingClassifier(
                learning_rate=0.1,
                max_iter=150,
                max_leaf_nodes=31,
                min_samples_leaf=20,
                l2_regularization=
                    1.0e-6,
                random_state=
                    RANDOM_SEED,
            ),
    }


def balanced_binary_sample_weights(
    y: Sequence[int],
) -> np.ndarray:
    labels = np.asarray(
        y,
        dtype=np.int64,
    )

    count_0 = int(
        np.sum(
            labels == 0
        )
    )

    count_1 = int(
        np.sum(
            labels == 1
        )
    )

    if (
        count_0 == 0
        or count_1 == 0
    ):
        raise MLLidarPointLevelBaselineError(
            "both classes required for weights"
        )

    n = labels.size

    weight_0 = (
        n
        / (
            2.0
            * count_0
        )
    )

    weight_1 = (
        n
        / (
            2.0
            * count_1
        )
    )

    return np.where(
        labels == 0,
        weight_0,
        weight_1,
    ).astype(
        np.float64
    )


def fit_with_binary_class_weights(
    model: BaseEstimator,
    X: np.ndarray,
    y: np.ndarray,
) -> BaseEstimator:
    weights = (
        balanced_binary_sample_weights(
            y
        )
    )

    if isinstance(
        model,
        Pipeline,
    ):
        model.fit(
            X,
            y,
            model__sample_weight=
                weights,
        )

    else:
        model.fit(
            X,
            y,
            sample_weight=
                weights,
        )

    return model


def positive_probability(
    model: BaseEstimator,
    X: np.ndarray,
) -> np.ndarray:
    result = np.asarray(
        model.predict_proba(X),
        dtype=np.float64,
    )

    if (
        result.ndim != 2
        or result.shape[1] != 2
    ):
        raise MLLidarPointLevelBaselineError(
            "predict_proba shape invalid"
        )

    return result[:, 1]


def binary_metrics(
    y_true: Sequence[int],
    probability: Sequence[float],
) -> dict[str, Any]:
    y = np.asarray(
        y_true,
        dtype=np.int64,
    )

    p = np.asarray(
        probability,
        dtype=np.float64,
    )

    if y.shape != p.shape:
        raise MLLidarPointLevelBaselineError(
            "metric vector shape mismatch"
        )

    if set(
        np.unique(y).tolist()
    ) != {
        0,
        1,
    }:
        raise MLLidarPointLevelBaselineError(
            "metrics require both classes"
        )

    if (
        not np.all(
            np.isfinite(p)
        )
        or np.any(p < 0.0)
        or np.any(p > 1.0)
    ):
        raise MLLidarPointLevelBaselineError(
            "invalid probability"
        )

    prediction = (
        p
        >= PROBABILITY_THRESHOLD
    ).astype(
        np.int64
    )

    matrix = confusion_matrix(
        y,
        prediction,
        labels=[
            0,
            1,
        ],
    )

    tn, fp, fn, tp = [
        int(item)
        for item
        in matrix.ravel()
    ]

    return {
        "balanced_accuracy":
            float(
                balanced_accuracy_score(
                    y,
                    prediction,
                )
            ),

        "precision":
            float(
                precision_score(
                    y,
                    prediction,
                    zero_division=0,
                )
            ),

        "recall":
            float(
                recall_score(
                    y,
                    prediction,
                    zero_division=0,
                )
            ),

        "f1":
            float(
                f1_score(
                    y,
                    prediction,
                    zero_division=0,
                )
            ),

        "roc_auc":
            float(
                roc_auc_score(
                    y,
                    p,
                )
            ),

        "average_precision":
            float(
                average_precision_score(
                    y,
                    p,
                )
            ),

        "brier_score":
            float(
                brier_score_loss(
                    y,
                    p,
                )
            ),

        "confusion_matrix": {
            "tn":
                tn,

            "fp":
                fp,

            "fn":
                fn,

            "tp":
                tp,
        },

        "sample_count":
            int(
                y.size
            ),

        "negative_count":
            int(
                np.sum(
                    y == 0
                )
            ),

        "positive_count":
            int(
                np.sum(
                    y == 1
                )
            ),
    }


def per_family_metrics(
    dataset: LoadedDataset,
    probability: np.ndarray,
) -> dict[
    str,
    dict[str, Any],
]:
    families = np.asarray(
        dataset.families,
        dtype=object,
    )

    result = {}

    clean_mask = (
        families
        == "CLEAN"
    )

    for family in (
        DEGRADATION_FAMILIES
    ):
        mask = (
            clean_mask
            | (
                families
                == family
            )
        )

        result[
            family
        ] = binary_metrics(
            dataset.y[
                mask
            ],
            probability[
                mask
            ],
        )

    return result


def per_trajectory_metrics(
    dataset: LoadedDataset,
    probability: np.ndarray,
) -> dict[
    str,
    dict[str, Any],
]:
    trajectories = np.asarray(
        dataset.trajectories,
        dtype=object,
    )

    result = {}

    for trajectory in sorted(
        set(
            trajectories.tolist()
        )
    ):
        mask = (
            trajectories
            == trajectory
        )

        result[
            trajectory
        ] = binary_metrics(
            dataset.y[
                mask
            ],
            probability[
                mask
            ],
        )

    return result
