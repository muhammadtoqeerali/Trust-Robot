"""Paired 13-feature extension of the frozen point-level LiDAR dataset.

The semantic benchmark population is unchanged. Each output sample retains
the exact parent sample_id, trajectory, selected window, degradation family,
binary label, and intervention parameters.

The historical five diagnostic features must first reproduce the frozen
parent sample. Eight observational final-nearest-neighbor statistics are
then appended.

No registration algorithm change and no real physical-health truth are
introduced here.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping, Sequence
import json
import math

from .lidar_noise_sensitive_diagnostics import (
    COMBINED_FEATURE_NAMES,
    LEGACY_PHASE4_FEATURE_NAMES,
    NOISE_SENSITIVE_FEATURE_NAMES,
    LidarNoiseSensitiveDiagnostics,
    combine_legacy_and_noise_sensitive_features,
)

from .ml_lidar_point_level_registration_dataset import (
    ALL_TRAIN,
    DEVELOPMENT_CHECK,
    DEVELOPMENT_TRAIN,
    EXPECTED_DIAGNOSTIC_COUNTS,
    WINDOWS_PER_TRAJECTORY,
    build_corruption_specs,
    evenly_spaced_two_scan_starts,
    partition_for_trajectory,
)


CONFIG_SCHEMA = (
    "TRUST_ROBOT_M2DGR_LIDAR_EXTENDED_13_FEATURE_REGISTRATION_DATASET_CONFIG_V1"
)

SAMPLE_SCHEMA = (
    "TRUST_ROBOT_M2DGR_LIDAR_EXTENDED_13_FEATURE_SAMPLE_V1"
)

FAMILIES = (
    "CLEAN",
    "POINT_DROPOUT",
    "XYZ_GAUSSIAN_NOISE",
    "AZIMUTH_SECTOR_OCCLUSION",
)

LEGACY_RMSE_REL_TOL = 1.0e-12
LEGACY_RMSE_ABS_TOL = 1.0e-12


class Extended13FeatureDatasetError(
    ValueError
):
    pass


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
        canonical_json_bytes(
            value
        )
    ).hexdigest()


def legacy_features_from_registration(
    registration_result: object,
) -> tuple[float, ...]:
    if not hasattr(
        registration_result,
        "diagnostics",
    ):
        raise Extended13FeatureDatasetError(
            "registration diagnostics missing"
        )

    diagnostics = (
        registration_result
        .diagnostics
    )

    names = LEGACY_PHASE4_FEATURE_NAMES

    values = []

    for name in names:
        if not hasattr(
            diagnostics,
            name,
        ):
            raise Extended13FeatureDatasetError(
                "missing diagnostic: "
                + name
            )

        value = float(
            getattr(
                diagnostics,
                name,
            )
        )

        if not math.isfinite(
            value
        ):
            raise Extended13FeatureDatasetError(
                "non-finite legacy diagnostic"
            )

        values.append(value)

    return tuple(values)


def assert_parent_legacy_identity(
    observed: Sequence[object],
    parent: Sequence[object],
) -> None:
    if (
        len(observed) != 5
        or len(parent) != 5
    ):
        raise Extended13FeatureDatasetError(
            "legacy identity requires five features"
        )

    for index, (
        actual,
        expected,
    ) in enumerate(
        zip(
            observed,
            parent,
            strict=True,
        )
    ):
        actual_float = float(actual)
        expected_float = float(expected)

        if index < 4:
            if actual_float != expected_float:
                raise Extended13FeatureDatasetError(
                    "parent legacy feature identity failure at index "
                    + str(index)
                )

        else:
            if not math.isclose(
                actual_float,
                expected_float,
                rel_tol=
                    LEGACY_RMSE_REL_TOL,
                abs_tol=
                    LEGACY_RMSE_ABS_TOL,
            ):
                raise Extended13FeatureDatasetError(
                    "parent RMSE identity failure"
                )


def validate_parent_sample(
    sample: Mapping[str, Any],
    *,
    trajectory: str,
    window_start: int,
    family: str,
) -> None:
    if sample.get(
        "outer_split"
    ) != "TRAIN":
        raise Extended13FeatureDatasetError(
            "parent sample is not TRAIN"
        )

    if sample.get(
        "trajectory"
    ) != trajectory:
        raise Extended13FeatureDatasetError(
            "parent trajectory mismatch"
        )

    if sample.get(
        "window_start_scan_index"
    ) != window_start:
        raise Extended13FeatureDatasetError(
            "parent window mismatch"
        )

    if sample.get(
        "degradation_family"
    ) != family:
        raise Extended13FeatureDatasetError(
            "parent degradation-family mismatch"
        )

    if sample.get(
        "feature_names"
    ) != list(
        LEGACY_PHASE4_FEATURE_NAMES
    ):
        raise Extended13FeatureDatasetError(
            "parent feature contract mismatch"
        )

    values = sample.get(
        "feature_values"
    )

    if (
        not isinstance(
            values,
            list,
        )
        or len(values) != 5
    ):
        raise Extended13FeatureDatasetError(
            "parent feature vector invalid"
        )

    expected_label = (
        0
        if family == "CLEAN"
        else 1
    )

    if sample.get(
        "binary_degraded_label"
    ) != expected_label:
        raise Extended13FeatureDatasetError(
            "parent binary label mismatch"
        )

    if sample.get(
        "label_is_real_physical_health_truth"
    ) is not False:
        raise Extended13FeatureDatasetError(
            "parent real-health boundary changed"
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
        raise Extended13FeatureDatasetError(
            "parent sample_id missing"
        )


def build_extended_sample(
    *,
    parent_sample: Mapping[str, Any],
    observed_legacy_features: Sequence[object],
    extended_diagnostics: LidarNoiseSensitiveDiagnostics,
) -> dict[str, Any]:
    parent_features = (
        parent_sample.get(
            "feature_values"
        )
    )

    if (
        not isinstance(
            parent_features,
            list,
        )
        or len(
            parent_features
        ) != 5
    ):
        raise Extended13FeatureDatasetError(
            "parent feature vector invalid"
        )

    assert_parent_legacy_identity(
        observed_legacy_features,
        parent_features,
    )

    combined = (
        combine_legacy_and_noise_sensitive_features(
            observed_legacy_features,
            extended_diagnostics,
        )
    )

    if len(
        combined
    ) != 13:
        raise Extended13FeatureDatasetError(
            "combined feature count changed"
        )

    result = dict(
        parent_sample
    )

    result[
        "schema"
    ] = SAMPLE_SCHEMA

    result[
        "feature_names"
    ] = list(
        COMBINED_FEATURE_NAMES
    )

    result[
        "feature_values"
    ] = [
        float(value)
        for value
        in combined
    ]

    result[
        "parent_sample_id"
    ] = parent_sample[
        "sample_id"
    ]

    result[
        "parent_legacy_feature_values_sha256"
    ] = sha256(
        canonical_json_bytes(
            {
                "feature_names":
                    list(
                        LEGACY_PHASE4_FEATURE_NAMES
                    ),

                "feature_values":
                    parent_features,
            }
        )
    ).hexdigest()

    result[
        "legacy_feature_count"
    ] = 5

    result[
        "new_residual_feature_count"
    ] = 8

    result[
        "combined_feature_count"
    ] = 13

    result[
        "parallel_observational_extension"
    ] = True

    result[
        "registration_algorithm_modified"
    ] = False

    result[
        "registration_refit_inside_extended_extractor"
    ] = False

    result[
        "parent_sample_population_changed"
    ] = False

    return result


def validate_config(
    payload: Mapping[str, Any],
) -> None:
    if payload.get(
        "schema"
    ) != CONFIG_SCHEMA:
        raise Extended13FeatureDatasetError(
            "config schema mismatch"
        )

    if payload.get(
        "schema_version"
    ) != 1:
        raise Extended13FeatureDatasetError(
            "config version mismatch"
        )

    if payload.get(
        "content_sha256"
    ) != content_sha256(
        payload
    ):
        raise Extended13FeatureDatasetError(
            "config digest mismatch"
        )

    if payload.get(
        "expected_window_count"
    ) != 1100:
        raise Extended13FeatureDatasetError(
            "window count changed"
        )

    if payload.get(
        "expected_registration_count"
    ) != 4400:
        raise Extended13FeatureDatasetError(
            "registration count changed"
        )

    if payload.get(
        "expected_sample_count"
    ) != 4400:
        raise Extended13FeatureDatasetError(
            "sample count changed"
        )

    if payload.get(
        "combined_feature_count"
    ) != 13:
        raise Extended13FeatureDatasetError(
            "combined feature count changed"
        )

    if tuple(
        payload.get(
            "families",
            (),
        )
    ) != FAMILIES:
        raise Extended13FeatureDatasetError(
            "family contract changed"
        )

    if payload.get(
        "expected_diagnostic_counts"
    ) != EXPECTED_DIAGNOSTIC_COUNTS:
        raise Extended13FeatureDatasetError(
            "trajectory diagnostic counts changed"
        )

    boundary = payload.get(
        "scientific_boundary",
        {},
    )

    for key in (
        "real_physical_health_truth",
        "model_fit_authorized",
        "VALIDATION_open",
        "CONFIRMATION_open",
        "reference_data_used",
        "ATE_RPE",
    ):
        if boundary.get(
            key
        ) is not False:
            raise Extended13FeatureDatasetError(
                key
                + " must remain false"
            )
