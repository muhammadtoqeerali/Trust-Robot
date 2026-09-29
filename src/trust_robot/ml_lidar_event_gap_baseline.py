"""TRAIN-only hard baseline for LiDAR EVENT_GAP registration diagnostics.

The five model inputs are frozen registration execution diagnostics:

    source_point_count
    target_point_count
    fixed_point_iterations
    final_correspondence_count
    final_nearest_neighbor_rmse_m

No corruption truth, trajectory identity, timestamp, scan index, pairing key,
or reference information enters the model feature matrix.

The target means synthetic EVENT_GAP intervention, not real physical health.
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
    "TRUST_ROBOT_M2DGR_LIDAR_EVENT_GAP_BASELINE_CONFIG_V1"
)

RESULT_SCHEMA = (
    "TRUST_ROBOT_M2DGR_LIDAR_EVENT_GAP_BASELINE_RESULTS_V1"
)

FEATURE_NAMES = (
    "source_point_count",
    "target_point_count",
    "fixed_point_iterations",
    "final_correspondence_count",
    "final_nearest_neighbor_rmse_m",
)

FEATURE_COUNT = 5

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


class MLLidarEventGapBaselineError(
    ValueError
):
    pass


@dataclass(
    frozen=True
)
class LoadedDataset:
    X: np.ndarray
    y: np.ndarray
    trajectories: tuple[str, ...]
    sample_ids: tuple[str, ...]
    window_fingerprints: tuple[str, ...]


def canonical_json_bytes(
    payload: Mapping[str, Any],
) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode(
        "utf-8"
    )


def content_sha256(
    payload: Mapping[str, Any],
) -> str:
    value = dict(
        payload
    )

    value.pop(
        "content_sha256",
        None,
    )

    return sha256(
        canonical_json_bytes(
            value
        )
    ).hexdigest()


def validate_config(
    payload: Mapping[str, Any],
) -> None:
    if payload.get(
        "schema"
    ) != CONFIG_SCHEMA:
        raise MLLidarEventGapBaselineError(
            "config schema mismatch"
        )

    if payload.get(
        "schema_version"
    ) != 1:
        raise MLLidarEventGapBaselineError(
            "config version mismatch"
        )

    if payload.get(
        "content_sha256"
    ) != content_sha256(
        payload
    ):
        raise MLLidarEventGapBaselineError(
            "config digest mismatch"
        )

    if tuple(
        payload.get(
            "feature_names",
            (),
        )
    ) != FEATURE_NAMES:
        raise MLLidarEventGapBaselineError(
            "feature contract changed"
        )

    if tuple(
        payload.get(
            "model_names",
            (),
        )
    ) != MODEL_NAMES:
        raise MLLidarEventGapBaselineError(
            "model family set changed"
        )

    if payload.get(
        "probability_threshold"
    ) != PROBABILITY_THRESHOLD:
        raise MLLidarEventGapBaselineError(
            "threshold changed"
        )

    if payload.get(
        "random_seed"
    ) != RANDOM_SEED:
        raise MLLidarEventGapBaselineError(
            "random seed changed"
        )

    split = payload.get(
        "development_split"
    )

    if not isinstance(
        split,
        Mapping,
    ):
        raise MLLidarEventGapBaselineError(
            "development split missing"
        )

    if tuple(
        split.get(
            "development_train",
            (),
        )
    ) != DEVELOPMENT_TRAIN:
        raise MLLidarEventGapBaselineError(
            "development train changed"
        )

    if tuple(
        split.get(
            "development_check",
            (),
        )
    ) != DEVELOPMENT_CHECK:
        raise MLLidarEventGapBaselineError(
            "development check changed"
        )

    if set(
        DEVELOPMENT_TRAIN
    ) & set(
        DEVELOPMENT_CHECK
    ):
        raise MLLidarEventGapBaselineError(
            "trajectory leakage"
        )

    policy = payload.get(
        "selection_policy"
    )

    if not isinstance(
        policy,
        Mapping,
    ):
        raise MLLidarEventGapBaselineError(
            "selection policy missing"
        )

    for field in (
        "hyperparameter_search_executed",
        "model_family_selection_executed",
        "final_health_model_selected",
        "validation_used",
        "confirmation_used",
        "reference_data_used",
        "real_health_labels_used",
    ):
        if policy.get(
            field
        ) is not False:
            raise MLLidarEventGapBaselineError(
                field
                + " must remain false"
            )


def allowed_trajectories(
    partition: str,
) -> tuple[str, ...]:
    if partition == "development_train":
        return DEVELOPMENT_TRAIN

    if partition == "development_check":
        return DEVELOPMENT_CHECK

    raise MLLidarEventGapBaselineError(
        "unknown development partition"
    )


def load_dataset(
    path: Path,
    *,
    expected_partition: str,
) -> LoadedDataset:
    allowed = set(
        allowed_trajectories(
            expected_partition
        )
    )

    X = []
    y = []
    trajectories = []
    sample_ids = []
    fingerprints = []

    pair_labels: dict[
        tuple[str, str],
        set[int],
    ] = {}

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        for raw_line in handle:
            if not raw_line.strip():
                raise MLLidarEventGapBaselineError(
                    "blank dataset line"
                )

            sample = json.loads(
                raw_line
            )

            if sample.get(
                "outer_split"
            ) != "TRAIN":
                raise MLLidarEventGapBaselineError(
                    "non-TRAIN sample"
                )

            if sample.get(
                "development_partition"
            ) != expected_partition:
                raise MLLidarEventGapBaselineError(
                    "partition mismatch"
                )

            trajectory = sample.get(
                "trajectory"
            )

            if trajectory not in allowed:
                raise MLLidarEventGapBaselineError(
                    "trajectory crossed partition"
                )

            if sample.get(
                "feature_names"
            ) != list(
                FEATURE_NAMES
            ):
                raise MLLidarEventGapBaselineError(
                    "feature names changed"
                )

            values = sample.get(
                "feature_values"
            )

            if (
                not isinstance(
                    values,
                    list,
                )
                or len(
                    values
                ) != FEATURE_COUNT
            ):
                raise MLLidarEventGapBaselineError(
                    "feature length mismatch"
                )

            numeric = [
                float(
                    value
                )
                for value
                in values
            ]

            if not all(
                math.isfinite(
                    value
                )
                for value
                in numeric
            ):
                raise MLLidarEventGapBaselineError(
                    "non-finite feature"
                )

            label = sample.get(
                "label"
            )

            if label not in (
                0,
                1,
            ):
                raise MLLidarEventGapBaselineError(
                    "invalid label"
                )

            for forbidden_true in (
                "header_stamps_are_model_features",
                "trajectory_identity_is_model_feature",
                "corruption_truth_is_model_feature",
                "physical_measurement_time_verified",
                "reference_data_used",
                "validation_data_used",
                "confirmation_data_used",
                "label_is_real_physical_health_truth",
            ):
                if sample.get(
                    forbidden_true
                ) is not False:
                    raise MLLidarEventGapBaselineError(
                        forbidden_true
                        + " must remain false"
                    )

            fingerprint = sample.get(
                "window_fingerprint_sha256"
            )

            if (
                not isinstance(
                    fingerprint,
                    str,
                )
                or len(
                    fingerprint
                ) != 64
            ):
                raise MLLidarEventGapBaselineError(
                    "window fingerprint missing"
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
                raise MLLidarEventGapBaselineError(
                    "sample id missing"
                )

            key = (
                trajectory,
                fingerprint,
            )

            pair_labels.setdefault(
                key,
                set(),
            ).add(
                int(
                    label
                )
            )

            X.append(
                numeric
            )

            y.append(
                int(
                    label
                )
            )

            trajectories.append(
                trajectory
            )

            sample_ids.append(
                sample_id
            )

            fingerprints.append(
                fingerprint
            )

    if not X:
        raise MLLidarEventGapBaselineError(
            "empty dataset"
        )

    for key, labels in pair_labels.items():
        if labels != {
            0,
            1,
        }:
            raise MLLidarEventGapBaselineError(
                "incomplete clean/gap pair "
                + repr(
                    key
                )
            )

    matrix = np.asarray(
        X,
        dtype=np.float64,
    )

    labels = np.asarray(
        y,
        dtype=np.int64,
    )

    if matrix.shape[
        1
    ] != FEATURE_COUNT:
        raise MLLidarEventGapBaselineError(
            "matrix feature count changed"
        )

    if set(
        np.unique(
            labels
        ).tolist()
    ) != {
        0,
        1,
    }:
        raise MLLidarEventGapBaselineError(
            "both classes required"
        )

    return LoadedDataset(
        X=
            matrix,

        y=
            labels,

        trajectories=
            tuple(
                trajectories
            ),

        sample_ids=
            tuple(
                sample_ids
            ),

        window_fingerprints=
            tuple(
                fingerprints
            ),
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
                class_weight="balanced",
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
                l2_regularization=1.0e-6,
                random_state=
                    RANDOM_SEED,
            ),
    }


def positive_probability(
    model: BaseEstimator,
    X: np.ndarray,
) -> np.ndarray:
    result = np.asarray(
        model.predict_proba(
            X
        ),
        dtype=np.float64,
    )

    if (
        result.ndim != 2
        or result.shape[
            1
        ] != 2
    ):
        raise MLLidarEventGapBaselineError(
            "predict_proba shape invalid"
        )

    return result[
        :,
        1
    ]


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
        raise MLLidarEventGapBaselineError(
            "metric vector shape mismatch"
        )

    if set(
        np.unique(
            y
        ).tolist()
    ) != {
        0,
        1,
    }:
        raise MLLidarEventGapBaselineError(
            "metric labels require both classes"
        )

    if (
        not np.all(
            np.isfinite(
                p
            )
        )
        or np.any(
            p < 0.0
        )
        or np.any(
            p > 1.0
        )
    ):
        raise MLLidarEventGapBaselineError(
            "invalid probabilities"
        )

    predicted = (
        p
        >= PROBABILITY_THRESHOLD
    ).astype(
        np.int64
    )

    matrix = confusion_matrix(
        y,
        predicted,
        labels=[
            0,
            1,
        ],
    )

    tn, fp, fn, tp = [
        int(
            item
        )
        for item
        in matrix.ravel()
    ]

    return {
        "balanced_accuracy":
            float(
                balanced_accuracy_score(
                    y,
                    predicted,
                )
            ),

        "precision":
            float(
                precision_score(
                    y,
                    predicted,
                    zero_division=0,
                )
            ),

        "recall":
            float(
                recall_score(
                    y,
                    predicted,
                    zero_division=0,
                )
            ),

        "f1":
            float(
                f1_score(
                    y,
                    predicted,
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
    }


def per_trajectory_metrics(
    y_true: np.ndarray,
    probability: np.ndarray,
    trajectories: Sequence[str],
) -> dict[
    str,
    dict[str, Any],
]:
    y = np.asarray(
        y_true,
        dtype=np.int64,
    )

    p = np.asarray(
        probability,
        dtype=np.float64,
    )

    names = np.asarray(
        trajectories,
        dtype=object,
    )

    if not (
        y.shape
        == p.shape
        == names.shape
    ):
        raise MLLidarEventGapBaselineError(
            "trajectory metric shape mismatch"
        )

    result = {}

    for trajectory in sorted(
        set(
            names.tolist()
        )
    ):
        mask = (
            names
            == trajectory
        )

        result[
            trajectory
        ] = binary_metrics(
            y[
                mask
            ],
            p[
                mask
            ],
        )

    return result
