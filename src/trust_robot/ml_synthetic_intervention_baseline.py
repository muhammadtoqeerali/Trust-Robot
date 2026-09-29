"""Synthetic-intervention ML development benchmark.

This is deliberately NOT the final TRUST-ROBOT health model.

It fits fixed, prospectively declared classifiers only on the internal
development-train trajectories of the frozen M2DGR TRAIN partition and
evaluates them only on separate internal development-check trajectories.

The labels describe the presence/absence of a declared synthetic
EVENT_REPEAT intervention.  They are not real sensor-health labels.
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
    "TRUST_ROBOT_M2DGR_SYNTHETIC_INTERVENTION_BASELINE_CONFIG_V1"
)

RESULT_SCHEMA = (
    "TRUST_ROBOT_M2DGR_SYNTHETIC_INTERVENTION_BASELINE_RESULTS_V1"
)

FEATURE_COUNT = 10
BASE_FEATURE_COUNT = 5

PROBABILITY_THRESHOLD = 0.5
RANDOM_SEED = 20260928

MODEL_NAMES = (
    "logistic_regression",
    "random_forest",
    "histogram_gradient_boosting",
)

DEVELOPMENT_TRAIN_TRAJECTORIES = (
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

DEVELOPMENT_CHECK_TRAJECTORIES = (
    "hall_05",
    "lift_04",
    "room_dark_04",
    "street_010",
    "street_09",
)


class MLSyntheticInterventionBaselineError(
    ValueError
):
    """Raised when the development-benchmark contract is violated."""


@dataclass(
    frozen=True
)
class LoadedDataset:
    X: np.ndarray
    y: np.ndarray
    trajectories: tuple[str, ...]
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
        raise MLSyntheticInterventionBaselineError(
            "config schema mismatch"
        )

    if payload.get(
        "schema_version"
    ) != 1:
        raise MLSyntheticInterventionBaselineError(
            "config schema version mismatch"
        )

    if payload.get(
        "content_sha256"
    ) != content_sha256(
        payload
    ):
        raise MLSyntheticInterventionBaselineError(
            "config content digest mismatch"
        )

    if payload.get(
        "probability_threshold"
    ) != PROBABILITY_THRESHOLD:
        raise MLSyntheticInterventionBaselineError(
            "probability threshold changed"
        )

    if payload.get(
        "random_seed"
    ) != RANDOM_SEED:
        raise MLSyntheticInterventionBaselineError(
            "random seed changed"
        )

    if tuple(
        payload.get(
            "model_names",
            (),
        )
    ) != MODEL_NAMES:
        raise MLSyntheticInterventionBaselineError(
            "model set changed"
        )

    split = payload.get(
        "development_split"
    )

    if not isinstance(
        split,
        Mapping,
    ):
        raise MLSyntheticInterventionBaselineError(
            "development split missing"
        )

    if tuple(
        split.get(
            "development_train",
            (),
        )
    ) != DEVELOPMENT_TRAIN_TRAJECTORIES:
        raise MLSyntheticInterventionBaselineError(
            "development-train trajectories changed"
        )

    if tuple(
        split.get(
            "development_check",
            (),
        )
    ) != DEVELOPMENT_CHECK_TRAJECTORIES:
        raise MLSyntheticInterventionBaselineError(
            "development-check trajectories changed"
        )

    if set(
        DEVELOPMENT_TRAIN_TRAJECTORIES
    ) & set(
        DEVELOPMENT_CHECK_TRAJECTORIES
    ):
        raise MLSyntheticInterventionBaselineError(
            "development trajectory leakage"
        )

    policy = payload.get(
        "selection_policy"
    )

    if not isinstance(
        policy,
        Mapping,
    ):
        raise MLSyntheticInterventionBaselineError(
            "selection policy missing"
        )

    required_false = (
        "hyperparameter_search_executed",
        "final_health_model_selected",
        "validation_used",
        "confirmation_used",
        "reference_data_used",
        "real_health_labels_used",
    )

    for field in required_false:
        if policy.get(
            field
        ) is not False:
            raise MLSyntheticInterventionBaselineError(
                field
                + " must remain false"
            )


def _allowed_trajectories(
    expected_partition: str,
) -> tuple[str, ...]:
    if expected_partition == "development_train":
        return DEVELOPMENT_TRAIN_TRAJECTORIES

    if expected_partition == "development_check":
        return DEVELOPMENT_CHECK_TRAJECTORIES

    raise MLSyntheticInterventionBaselineError(
        "unexpected development partition"
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

    features: list[
        list[float]
    ] = []

    labels: list[
        int
    ] = []

    trajectories: list[
        str
    ] = []

    sample_ids: list[
        str
    ] = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        for line_number, raw_line in enumerate(
            handle,
            start=1,
        ):
            if not raw_line.strip():
                raise MLSyntheticInterventionBaselineError(
                    "blank ML dataset line"
                )

            try:
                sample = json.loads(
                    raw_line
                )
            except json.JSONDecodeError as exc:
                raise MLSyntheticInterventionBaselineError(
                    "invalid ML dataset JSON"
                ) from exc

            if sample.get(
                "outer_split"
            ) != "TRAIN":
                raise MLSyntheticInterventionBaselineError(
                    "non-TRAIN sample encountered"
                )

            if sample.get(
                "development_partition"
            ) != expected_partition:
                raise MLSyntheticInterventionBaselineError(
                    "development partition mismatch"
                )

            trajectory = sample.get(
                "trajectory"
            )

            if trajectory not in allowed:
                raise MLSyntheticInterventionBaselineError(
                    "trajectory crossed development partition"
                )

            if sample.get(
                "label_is_real_physical_health_truth"
            ) is not False:
                raise MLSyntheticInterventionBaselineError(
                    "real-health semantics unexpectedly enabled"
                )

            for field in (
                "reference_data_used",
                "validation_data_used",
                "confirmation_data_used",
                "physical_measurement_time_used",
                "cross_modal_alignment_used",
            ):
                if sample.get(
                    field
                ) is not False:
                    raise MLSyntheticInterventionBaselineError(
                        field
                        + " must remain false"
                    )

            label = sample.get(
                "label"
            )

            if label not in (
                0,
                1,
            ):
                raise MLSyntheticInterventionBaselineError(
                    "label must be binary"
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
                raise MLSyntheticInterventionBaselineError(
                    "feature vector length mismatch"
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
                raise MLSyntheticInterventionBaselineError(
                    "non-finite feature value"
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
                raise MLSyntheticInterventionBaselineError(
                    "sample_id missing"
                )

            features.append(
                numeric
            )

            labels.append(
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

    if not features:
        raise MLSyntheticInterventionBaselineError(
            "empty ML development dataset"
        )

    X = np.asarray(
        features,
        dtype=np.float64,
    )

    y = np.asarray(
        labels,
        dtype=np.int64,
    )

    if X.ndim != 2 or X.shape[
        1
    ] != FEATURE_COUNT:
        raise MLSyntheticInterventionBaselineError(
            "materialized feature matrix shape invalid"
        )

    if set(
        np.unique(
            y
        ).tolist()
    ) != {
        0,
        1,
    }:
        raise MLSyntheticInterventionBaselineError(
            "both classes are required"
        )

    return LoadedDataset(
        X=X,
        y=y,
        trajectories=tuple(
            trajectories
        ),
        sample_ids=tuple(
            sample_ids
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


def mechanism_signature_probability(
    X: np.ndarray,
) -> np.ndarray:
    values = np.asarray(
        X,
        dtype=np.float64,
    )

    if (
        values.ndim != 2
        or values.shape[
            1
        ] != FEATURE_COUNT
    ):
        raise MLSyntheticInterventionBaselineError(
            "mechanism baseline feature matrix invalid"
        )

    previous = values[
        :,
        :BASE_FEATURE_COUNT,
    ]

    current = values[
        :,
        BASE_FEATURE_COUNT:,
    ]

    return np.all(
        previous == current,
        axis=1,
    ).astype(
        np.float64
    )


def compute_binary_metrics(
    y_true: Sequence[int],
    probabilities: Sequence[float],
    *,
    threshold: float = PROBABILITY_THRESHOLD,
) -> dict[str, Any]:
    y = np.asarray(
        y_true,
        dtype=np.int64,
    )

    probability = np.asarray(
        probabilities,
        dtype=np.float64,
    )

    if y.ndim != 1:
        raise MLSyntheticInterventionBaselineError(
            "labels must be one-dimensional"
        )

    if probability.shape != y.shape:
        raise MLSyntheticInterventionBaselineError(
            "probability shape mismatch"
        )

    if set(
        np.unique(
            y
        ).tolist()
    ) != {
        0,
        1,
    }:
        raise MLSyntheticInterventionBaselineError(
            "metrics require both classes"
        )

    if not np.all(
        np.isfinite(
            probability
        )
    ):
        raise MLSyntheticInterventionBaselineError(
            "non-finite model probabilities"
        )

    if np.any(
        probability < 0.0
    ) or np.any(
        probability > 1.0
    ):
        raise MLSyntheticInterventionBaselineError(
            "probabilities outside [0,1]"
        )

    predicted = (
        probability
        >= float(
            threshold
        )
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

    tn, fp, fn, tp = (
        int(
            value
        )
        for value
        in matrix.ravel()
    )

    return {
        "threshold":
            float(
                threshold
            ),

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
                    probability,
                )
            ),

        "average_precision":
            float(
                average_precision_score(
                    y,
                    probability,
                )
            ),

        "brier_score":
            float(
                brier_score_loss(
                    y,
                    probability,
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

        "positive_count":
            int(
                np.sum(
                    y == 1
                )
            ),

        "negative_count":
            int(
                np.sum(
                    y == 0
                )
            ),
    }


def compute_per_trajectory_metrics(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    trajectories: Sequence[str],
) -> dict[
    str,
    dict[str, Any],
]:
    trajectory_array = np.asarray(
        trajectories,
        dtype=object,
    )

    y = np.asarray(
        y_true,
        dtype=np.int64,
    )

    probability = np.asarray(
        probabilities,
        dtype=np.float64,
    )

    if not (
        y.shape
        == probability.shape
        == trajectory_array.shape
    ):
        raise MLSyntheticInterventionBaselineError(
            "per-trajectory vector shape mismatch"
        )

    result = {}

    for trajectory in sorted(
        set(
            trajectory_array.tolist()
        )
    ):
        mask = (
            trajectory_array
            == trajectory
        )

        result[
            trajectory
        ] = compute_binary_metrics(
            y[
                mask
            ],
            probability[
                mask
            ],
        )

    return result


def predict_positive_probability(
    model: BaseEstimator,
    X: np.ndarray,
) -> np.ndarray:
    if not hasattr(
        model,
        "predict_proba",
    ):
        raise MLSyntheticInterventionBaselineError(
            "model must expose predict_proba"
        )

    matrix = np.asarray(
        model.predict_proba(
            X
        ),
        dtype=np.float64,
    )

    if (
        matrix.ndim != 2
        or matrix.shape[
            1
        ] != 2
    ):
        raise MLSyntheticInterventionBaselineError(
            "predict_proba output shape invalid"
        )

    return matrix[
        :,
        1
    ]


def build_result_contract(
) -> dict[str, Any]:
    return {
        "schema":
            RESULT_SCHEMA,

        "schema_version":
            1,

        "task":
            "synthetic_EVENT_REPEAT_intervention_discrimination",

        "models":
            list(
                MODEL_NAMES
            ),

        "mechanism_signature_baseline":
            True,

        "probability_threshold":
            PROBABILITY_THRESHOLD,

        "hyperparameter_search":
            False,

        "final_health_model_selection":
            False,

        "scientific_boundary": {
            "real_health_truth":
                False,

            "final_TRUST_ROBOT_health_model":
                False,

            "VALIDATION_open":
                False,

            "CONFIRMATION_open":
                False,

            "reference_data_used":
                False,

            "ATE_RPE":
                False,
        },
    }
