"""Paired 13-feature TRAIN-only synthetic LiDAR development baseline.

This module evaluates the exact same semantic samples and trajectory split
as the frozen five-feature point-level multi-degradation baseline.

Only the feature representation changes:

    frozen representation:   5 features
    extended representation: 13 features

No hyperparameter search or model-family selection is performed.
The labels remain synthetic intervention truth, not real health truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import json
import math

import numpy as np
from sklearn.metrics import roc_auc_score

from .lidar_noise_sensitive_diagnostics import (
    COMBINED_FEATURE_NAMES,
    LEGACY_PHASE4_FEATURE_NAMES,
    NOISE_SENSITIVE_FEATURE_NAMES,
)

from .ml_lidar_point_level_multidegradation_baseline import (
    DEGRADATION_FAMILIES,
    DEVELOPMENT_CHECK,
    DEVELOPMENT_TRAIN,
    MODEL_NAMES,
    PROBABILITY_THRESHOLD,
    RANDOM_SEED,
    balanced_binary_sample_weights,
    binary_metrics,
    build_models,
    fit_with_binary_class_weights,
    per_family_metrics,
    per_trajectory_metrics,
    positive_probability,
)


CONFIG_SCHEMA = (
    "TRUST_ROBOT_M2DGR_LIDAR_EXTENDED_13_FEATURE_MULTIDEGRADATION_BASELINE_CONFIG_V1"
)

RESULT_SCHEMA = (
    "TRUST_ROBOT_M2DGR_LIDAR_EXTENDED_13_FEATURE_MULTIDEGRADATION_BASELINE_RESULTS_V1"
)

FEATURE_NAMES = COMBINED_FEATURE_NAMES
FEATURE_COUNT = 13


class Extended13FeatureBaselineError(
    ValueError
):
    pass


@dataclass(
    frozen=True
)
class LoadedExtendedDataset:
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

    parent_sample_ids: tuple[str, ...]


def load_extended_dataset(
    path: Path,
    *,
    expected_partition: str,
) -> LoadedExtendedDataset:
    if expected_partition == "development_train":
        allowed = set(
            DEVELOPMENT_TRAIN
        )

    elif expected_partition == "development_check":
        allowed = set(
            DEVELOPMENT_CHECK
        )

    else:
        raise Extended13FeatureBaselineError(
            "unknown development partition"
        )

    X = []
    y = []
    families = []
    trajectories = []
    window_keys = []
    sample_ids = []
    parent_sample_ids = []

    per_window_families = {}

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        for raw_line in handle:
            if not raw_line.strip():
                raise Extended13FeatureBaselineError(
                    "blank dataset line"
                )

            item = json.loads(
                raw_line
            )

            if item.get(
                "outer_split"
            ) != "TRAIN":
                raise Extended13FeatureBaselineError(
                    "non-TRAIN sample"
                )

            if item.get(
                "development_partition"
            ) != expected_partition:
                raise Extended13FeatureBaselineError(
                    "partition mismatch"
                )

            trajectory = item.get(
                "trajectory"
            )

            if trajectory not in allowed:
                raise Extended13FeatureBaselineError(
                    "trajectory crossed development partition"
                )

            if item.get(
                "feature_names"
            ) != list(
                FEATURE_NAMES
            ):
                raise Extended13FeatureBaselineError(
                    "13-feature contract mismatch"
                )

            values = item.get(
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
                raise Extended13FeatureBaselineError(
                    "feature-vector length mismatch"
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
                raise Extended13FeatureBaselineError(
                    "non-finite feature value"
                )

            family = item.get(
                "degradation_family"
            )

            if family not in (
                "CLEAN",
                *DEGRADATION_FAMILIES,
            ):
                raise Extended13FeatureBaselineError(
                    "unknown degradation family"
                )

            expected_label = (
                0
                if family == "CLEAN"
                else 1
            )

            if item.get(
                "binary_degraded_label"
            ) != expected_label:
                raise Extended13FeatureBaselineError(
                    "family / binary label mismatch"
                )

            sample_id = item.get(
                "sample_id"
            )

            parent_sample_id = item.get(
                "parent_sample_id"
            )

            if (
                not isinstance(
                    sample_id,
                    str,
                )
                or not sample_id
            ):
                raise Extended13FeatureBaselineError(
                    "sample_id missing"
                )

            if parent_sample_id != sample_id:
                raise Extended13FeatureBaselineError(
                    "paired parent sample identity changed"
                )

            if item.get(
                "combined_feature_count"
            ) != 13:
                raise Extended13FeatureBaselineError(
                    "combined feature count changed"
                )

            if item.get(
                "legacy_feature_count"
            ) != 5:
                raise Extended13FeatureBaselineError(
                    "legacy feature count changed"
                )

            if item.get(
                "new_residual_feature_count"
            ) != 8:
                raise Extended13FeatureBaselineError(
                    "new residual feature count changed"
                )

            if item.get(
                "parent_sample_population_changed"
            ) is not False:
                raise Extended13FeatureBaselineError(
                    "parent population changed"
                )

            if item.get(
                "registration_algorithm_modified"
            ) is not False:
                raise Extended13FeatureBaselineError(
                    "registration algorithm changed"
                )

            if item.get(
                "registration_refit_inside_extended_extractor"
            ) is not False:
                raise Extended13FeatureBaselineError(
                    "extended extractor refit registration"
                )

            if item.get(
                "label_is_real_physical_health_truth"
            ) is not False:
                raise Extended13FeatureBaselineError(
                    "real-health truth boundary changed"
                )

            start = item.get(
                "window_start_scan_index"
            )

            if (
                type(start) is not int
                or start < 0
            ):
                raise Extended13FeatureBaselineError(
                    "invalid window start"
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

            X.append(
                numeric
            )

            y.append(
                expected_label
            )

            families.append(
                family
            )

            trajectories.append(
                trajectory
            )

            window_keys.append(
                key
            )

            sample_ids.append(
                sample_id
            )

            parent_sample_ids.append(
                parent_sample_id
            )

    if not X:
        raise Extended13FeatureBaselineError(
            "empty dataset"
        )

    required_families = {
        "CLEAN",
        *DEGRADATION_FAMILIES,
    }

    for key, observed in (
        per_window_families.items()
    ):
        if observed != required_families:
            raise Extended13FeatureBaselineError(
                "incomplete family set for "
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

    return LoadedExtendedDataset(
        X=
            matrix,

        y=
            labels,

        families=
            tuple(
                families
            ),

        trajectories=
            tuple(
                trajectories
            ),

        window_keys=
            tuple(
                window_keys
            ),

        sample_ids=
            tuple(
                sample_ids
            ),

        parent_sample_ids=
            tuple(
                parent_sample_ids
            ),
    )


def load_parent_five_feature_index(
    *paths: Path,
) -> dict[
    str,
    dict[str, Any],
]:
    result = {}

    for path in paths:
        with path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            for raw_line in handle:
                if not raw_line.strip():
                    raise Extended13FeatureBaselineError(
                        "blank parent line"
                    )

                item = json.loads(
                    raw_line
                )

                sample_id = item.get(
                    "sample_id"
                )

                if (
                    not isinstance(
                        sample_id,
                        str,
                    )
                    or not sample_id
                ):
                    raise Extended13FeatureBaselineError(
                        "parent sample_id missing"
                    )

                if sample_id in result:
                    raise Extended13FeatureBaselineError(
                        "duplicate parent sample_id"
                    )

                if item.get(
                    "feature_names"
                ) != list(
                    LEGACY_PHASE4_FEATURE_NAMES
                ):
                    raise Extended13FeatureBaselineError(
                        "parent five-feature contract changed"
                    )

                values = item.get(
                    "feature_values"
                )

                if (
                    not isinstance(
                        values,
                        list,
                    )
                    or len(values) != 5
                ):
                    raise Extended13FeatureBaselineError(
                        "parent five-feature vector invalid"
                    )

                result[
                    sample_id
                ] = item

    return result


def assert_exact_parent_pairing(
    dataset: LoadedExtendedDataset,
    parent_index: Mapping[
        str,
        Mapping[str, Any],
    ],
) -> None:
    for row_index, sample_id in enumerate(
        dataset.sample_ids
    ):
        parent = parent_index.get(
            sample_id
        )

        if parent is None:
            raise Extended13FeatureBaselineError(
                "parent sample missing"
            )

        if parent.get(
            "trajectory"
        ) != dataset.trajectories[
            row_index
        ]:
            raise Extended13FeatureBaselineError(
                "paired trajectory changed"
            )

        if parent.get(
            "window_start_scan_index"
        ) != dataset.window_keys[
            row_index
        ][1]:
            raise Extended13FeatureBaselineError(
                "paired window changed"
            )

        if parent.get(
            "degradation_family"
        ) != dataset.families[
            row_index
        ]:
            raise Extended13FeatureBaselineError(
                "paired family changed"
            )

        parent_label = int(
            parent[
                "binary_degraded_label"
            ]
        )

        if parent_label != int(
            dataset.y[
                row_index
            ]
        ):
            raise Extended13FeatureBaselineError(
                "paired label changed"
            )

        parent_features = [
            float(value)
            for value
            in parent[
                "feature_values"
            ]
        ]

        observed = dataset.X[
            row_index,
            :5,
        ]

        for index in range(
            5
        ):
            if index < 4:
                if float(
                    observed[index]
                ) != parent_features[
                    index
                ]:
                    raise Extended13FeatureBaselineError(
                        "paired legacy integer-like feature changed"
                    )

            else:
                if not math.isclose(
                    float(
                        observed[index]
                    ),
                    parent_features[
                        index
                    ],
                    rel_tol=
                        1.0e-12,
                    abs_tol=
                        1.0e-12,
                ):
                    raise Extended13FeatureBaselineError(
                        "paired legacy RMSE changed"
                    )


def univariate_report(
    dataset: LoadedExtendedDataset,
) -> dict[
    str,
    dict[str, float],
]:
    result = {}

    for index, name in enumerate(
        FEATURE_NAMES
    ):
        raw_auc = float(
            roc_auc_score(
                dataset.y,
                dataset.X[
                    :,
                    index,
                ],
            )
        )

        result[
            name
        ] = {
            "raw_direction_roc_auc":
                raw_auc,

            "direction_agnostic_roc_auc":
                max(
                    raw_auc,
                    1.0
                    - raw_auc
                ),
        }

    return result


def per_family_univariate_report(
    dataset: LoadedExtendedDataset,
) -> dict[
    str,
    dict[
        str,
        dict[str, float],
    ],
]:
    families = np.asarray(
        dataset.families,
        dtype=object,
    )

    clean = (
        families
        == "CLEAN"
    )

    result = {}

    for family in (
        DEGRADATION_FAMILIES
    ):
        mask = (
            clean
            | (
                families
                == family
            )
        )

        family_result = {}

        for index, name in enumerate(
            FEATURE_NAMES
        ):
            raw_auc = float(
                roc_auc_score(
                    dataset.y[
                        mask
                    ],
                    dataset.X[
                        mask,
                        index,
                    ],
                )
            )

            family_result[
                name
            ] = {
                "raw_direction_roc_auc":
                    raw_auc,

                "direction_agnostic_roc_auc":
                    max(
                        raw_auc,
                        1.0
                        - raw_auc
                    ),
            }

        result[
            family
        ] = family_result

    return result


def validate_config(
    payload: Mapping[str, Any],
) -> None:
    if payload.get(
        "schema"
    ) != CONFIG_SCHEMA:
        raise Extended13FeatureBaselineError(
            "config schema mismatch"
        )

    if payload.get(
        "schema_version"
    ) != 1:
        raise Extended13FeatureBaselineError(
            "config version mismatch"
        )

    if payload.get(
        "feature_count"
    ) != 13:
        raise Extended13FeatureBaselineError(
            "feature count changed"
        )

    if payload.get(
        "legacy_feature_count"
    ) != 5:
        raise Extended13FeatureBaselineError(
            "legacy feature count changed"
        )

    if payload.get(
        "new_residual_feature_count"
    ) != 8:
        raise Extended13FeatureBaselineError(
            "new residual feature count changed"
        )

    if tuple(
        payload.get(
            "feature_names",
            (),
        )
    ) != FEATURE_NAMES:
        raise Extended13FeatureBaselineError(
            "feature names changed"
        )

    if tuple(
        payload.get(
            "model_names",
            (),
        )
    ) != MODEL_NAMES:
        raise Extended13FeatureBaselineError(
            "model set changed"
        )

    if payload.get(
        "probability_threshold"
    ) != PROBABILITY_THRESHOLD:
        raise Extended13FeatureBaselineError(
            "threshold changed"
        )

    if payload.get(
        "random_seed"
    ) != RANDOM_SEED:
        raise Extended13FeatureBaselineError(
            "seed changed"
        )

    policy = payload.get(
        "selection_policy",
        {},
    )

    for name in (
        "hyperparameter_search_executed",
        "model_family_selection_executed",
        "final_health_model_selected",
        "VALIDATION_used",
        "CONFIRMATION_used",
        "reference_data_used",
        "real_health_labels_used",
    ):
        if policy.get(
            name
        ) is not False:
            raise Extended13FeatureBaselineError(
                name
                + " must remain false"
            )
