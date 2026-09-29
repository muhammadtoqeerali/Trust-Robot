"""TRAIN-only point-level LiDAR registration degradation dataset.

Each prospectively selected two-scan window has one frozen clean Phase-4
diagnostic observation and three newly executed synthetic corrupted
registration observations:

    CLEAN
    POINT_DROPOUT
    XYZ_GAUSSIAN_NOISE
    AZIMUTH_SECTOR_OCCLUSION

The clean branch is reused from the already-qualified Phase-4 artifact.

The raw two-scan window is nevertheless decoded during replay so the clean
Phase-4 point-count diagnostics can be bound to the actual selected scans.

No label here is real physical sensor-health truth.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping, Sequence
import json
import math

import numpy as np

from .corruption import (
    EventStream,
    SensorModality,
)
from .lidar_point_level_corruption import (
    LidarPointCorruptionFamily,
    LidarPointCorruptionSpec,
    apply_lidar_point_corruption,
)
from .lidar_corruption_estimator import (
    run_frozen_lidar_registration_path,
)


CONFIG_SCHEMA = (
    "TRUST_ROBOT_M2DGR_LIDAR_POINT_LEVEL_REGISTRATION_DATASET_CONFIG_V1"
)

SAMPLE_SCHEMA = (
    "TRUST_ROBOT_M2DGR_LIDAR_POINT_LEVEL_REGISTRATION_SAMPLE_V1"
)

FEATURE_NAMES = (
    "source_point_count",
    "target_point_count",
    "fixed_point_iterations",
    "final_correspondence_count",
    "final_nearest_neighbor_rmse_m",
)

WINDOWS_PER_TRAJECTORY = 50

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

ALL_TRAIN = DEVELOPMENT_TRAIN + DEVELOPMENT_CHECK

EXPECTED_DIAGNOSTIC_COUNTS = {
    "Circle_01": 2338,
    "door_01": 4605,
    "gate_01": 1721,
    "hall_01": 3510,
    "hall_03": 1644,
    "hall_04": 1812,
    "hall_05": 4016,
    "lift_02": 4872,
    "lift_04": 2985,
    "room_02": 751,
    "room_dark_01": 1111,
    "room_dark_02": 1646,
    "room_dark_03": 1158,
    "room_dark_04": 1434,
    "street_01": 10269,
    "street_010": 9086,
    "street_03": 3534,
    "street_04": 8567,
    "street_05": 4686,
    "street_07": 9275,
    "street_09": 9059,
    "walk_01": 2913,
}

FAMILY_CLASS_ID = {
    "CLEAN": 0,
    "POINT_DROPOUT": 1,
    "XYZ_GAUSSIAN_NOISE": 2,
    "AZIMUTH_SECTOR_OCCLUSION": 3,
}


class MLLidarPointLevelDatasetError(
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
    value.pop("content_sha256", None)

    return sha256(
        canonical_json_bytes(value)
    ).hexdigest()


def partition_for_trajectory(
    trajectory: str,
) -> str:
    if trajectory in DEVELOPMENT_TRAIN:
        return "development_train"

    if trajectory in DEVELOPMENT_CHECK:
        return "development_check"

    raise MLLidarPointLevelDatasetError(
        "trajectory outside frozen TRAIN cohort"
    )


def evenly_spaced_two_scan_starts(
    diagnostic_count: int,
    *,
    selected_count: int = WINDOWS_PER_TRAJECTORY,
) -> tuple[int, ...]:
    if (
        type(diagnostic_count) is not int
        or diagnostic_count < selected_count
    ):
        raise MLLidarPointLevelDatasetError(
            "invalid diagnostic count"
        )

    result = tuple(
        int(
            round(
                k
                * (diagnostic_count - 1)
                / (selected_count - 1)
            )
        )
        for k in range(selected_count)
    )

    if len(set(result)) != selected_count:
        raise MLLidarPointLevelDatasetError(
            "duplicate selected window"
        )

    if result[0] != 0:
        raise MLLidarPointLevelDatasetError(
            "first selected window changed"
        )

    if result[-1] != diagnostic_count - 1:
        raise MLLidarPointLevelDatasetError(
            "last selected window changed"
        )

    for left, right in zip(
        result,
        result[1:],
    ):
        if right - left < 2:
            raise MLLidarPointLevelDatasetError(
                "selected two-scan windows overlap"
            )

    return result


def build_corruption_specs(
) -> tuple[LidarPointCorruptionSpec, ...]:
    return (
        LidarPointCorruptionSpec(
            family=
                LidarPointCorruptionFamily.POINT_DROPOUT,
            target_event_index=
                1,
            remove_fraction=
                0.30,
        ),
        LidarPointCorruptionSpec(
            family=
                LidarPointCorruptionFamily.XYZ_GAUSSIAN_NOISE,
            target_event_index=
                1,
            sigma_m=
                0.05,
        ),
        LidarPointCorruptionSpec(
            family=
                LidarPointCorruptionFamily.AZIMUTH_SECTOR_OCCLUSION,
            target_event_index=
                1,
            sector_width_degrees=
                60.0,
        ),
    )


def _feature_vector(
    values: Sequence[object],
) -> list[float | int]:
    if (
        isinstance(values, (str, bytes, bytearray))
        or len(values) != 5
    ):
        raise MLLidarPointLevelDatasetError(
            "exactly five diagnostic features required"
        )

    result = []

    for value in values:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
        ):
            raise MLLidarPointLevelDatasetError(
                "feature must be finite numeric"
            )

        result.append(value)

    return result


def _extract_corrupt_features(
    stream: EventStream,
) -> tuple[
    list[float | int],
    dict[str, Any],
]:
    result = run_frozen_lidar_registration_path(
        stream
    )

    if result.get("origin_pairs") != [[0, 1]]:
        raise MLLidarPointLevelDatasetError(
            "two-scan registration topology changed"
        )

    records = result.get("records")

    if (
        not isinstance(records, list)
        or len(records) != 1
    ):
        raise MLLidarPointLevelDatasetError(
            "expected exactly one registration record"
        )

    diagnostics = records[0].get(
        "diagnostics"
    )

    if not isinstance(
        diagnostics,
        Mapping,
    ):
        raise MLLidarPointLevelDatasetError(
            "registration diagnostics missing"
        )

    features = _feature_vector(
        [
            diagnostics[name]
            for name in FEATURE_NAMES
        ]
    )

    return (
        features,
        result,
    )


def _sample_id(
    *,
    trajectory: str,
    window_start_scan_index: int,
    family: str,
    clean_record_sha256: str,
) -> str:
    payload = {
        "trajectory":
            trajectory,
        "window_start_scan_index":
            window_start_scan_index,
        "family":
            family,
        "clean_record_sha256":
            clean_record_sha256,
    }

    return (
        "TRUST_POINT_SAMPLE_"
        + sha256(
            canonical_json_bytes(payload)
        ).hexdigest()[:24]
    )


def build_window_samples(
    *,
    clean_stream: EventStream,
    clean_feature_values: Sequence[object],
    clean_phase4_record_sha256: str,
    trajectory: str,
    window_start_scan_index: int,
) -> tuple[
    list[dict[str, Any]],
    dict[str, Any],
]:
    if clean_stream.modality != SensorModality.LIDAR:
        raise MLLidarPointLevelDatasetError(
            "clean stream must be LiDAR"
        )

    if clean_stream.n_events != 2:
        raise MLLidarPointLevelDatasetError(
            "exactly two clean events required"
        )

    partition = partition_for_trajectory(
        trajectory
    )

    features = _feature_vector(
        clean_feature_values
    )

    previous_count = int(
        clean_stream.payloads[0].shape[0]
    )

    current_count = int(
        clean_stream.payloads[1].shape[0]
    )

    source_count = float(features[0])
    target_count = float(features[1])

    if (
        not source_count.is_integer()
        or int(source_count)
        != current_count
    ):
        raise MLLidarPointLevelDatasetError(
            "Phase-4 source_point_count does not bind to selected current scan"
        )

    if (
        not target_count.is_integer()
        or int(target_count)
        != previous_count
    ):
        raise MLLidarPointLevelDatasetError(
            "Phase-4 target_point_count does not bind to selected previous scan"
        )

    if (
        not isinstance(
            clean_phase4_record_sha256,
            str,
        )
        or len(
            clean_phase4_record_sha256
        ) != 64
    ):
        raise MLLidarPointLevelDatasetError(
            "clean Phase-4 record SHA missing"
        )

    window_key = (
        "M2DGR:TRAIN:"
        + trajectory
        + ":two_scan_start:"
        + str(window_start_scan_index)
    )

    common = {
        "schema":
            SAMPLE_SCHEMA,

        "outer_split":
            "TRAIN",

        "development_partition":
            partition,

        "trajectory":
            trajectory,

        "window_start_scan_index":
            window_start_scan_index,

        "window_scan_indices": [
            window_start_scan_index,
            window_start_scan_index + 1,
        ],

        "clean_phase4_record_sha256":
            clean_phase4_record_sha256,

        "clean_stream_fingerprint_sha256":
            clean_stream.fingerprint(),

        "feature_names":
            list(FEATURE_NAMES),

        "trajectory_identity_is_model_feature":
            False,

        "window_index_is_model_feature":
            False,

        "corruption_family_is_model_feature":
            False,

        "corruption_parameters_are_model_features":
            False,

        "timestamps_are_model_features":
            False,

        "reference_data_used":
            False,

        "validation_data_used":
            False,

        "confirmation_data_used":
            False,

        "label_is_real_physical_health_truth":
            False,
    }

    samples = [
        {
            **common,

            "sample_id":
                _sample_id(
                    trajectory=
                        trajectory,

                    window_start_scan_index=
                        window_start_scan_index,

                    family=
                        "CLEAN",

                    clean_record_sha256=
                        clean_phase4_record_sha256,
                ),

            "degradation_family":
                "CLEAN",

            "family_class_id":
                0,

            "binary_degraded_label":
                0,

            "synthetic_intervention_applied":
                False,

            "feature_values":
                features,
        }
    ]

    corruption_receipts = []

    for spec in build_corruption_specs():
        corrupted = apply_lidar_point_corruption(
            clean_stream,
            spec,
            window_key=
                window_key,
        )

        corrupt_features, registration = (
            _extract_corrupt_features(
                corrupted.corrupt
            )
        )

        family = spec.family.value

        samples.append(
            {
                **common,

                "sample_id":
                    _sample_id(
                        trajectory=
                            trajectory,

                        window_start_scan_index=
                            window_start_scan_index,

                        family=
                            family,

                        clean_record_sha256=
                            clean_phase4_record_sha256,
                    ),

                "degradation_family":
                    family,

                "family_class_id":
                    FAMILY_CLASS_ID[
                        family
                    ],

                "binary_degraded_label":
                    1,

                "synthetic_intervention_applied":
                    True,

                "feature_values":
                    corrupt_features,
            }
        )

        corruption_receipts.append(
            {
                "family":
                    family,

                "truth":
                    dict(
                        corrupted.truth
                    ),

                "corrupt_stream_fingerprint_sha256":
                    corrupted.corrupt.fingerprint(),

                "registration_content_sha256":
                    registration.get(
                        "content_sha256"
                    ),

                "registration_origin_pairs":
                    registration.get(
                        "origin_pairs"
                    ),
            }
        )

    provenance = {
        "trajectory":
            trajectory,

        "development_partition":
            partition,

        "window_start_scan_index":
            window_start_scan_index,

        "window_key":
            window_key,

        "clean_phase4_record_sha256":
            clean_phase4_record_sha256,

        "clean_stream_fingerprint_sha256":
            clean_stream.fingerprint(),

        "previous_point_count":
            previous_count,

        "current_point_count":
            current_count,

        "corruptions":
            corruption_receipts,
    }

    if len(samples) != 4:
        raise MLLidarPointLevelDatasetError(
            "exactly four samples per selected window required"
        )

    return (
        samples,
        provenance,
    )


def validate_config(
    payload: Mapping[str, Any],
) -> None:
    if payload.get("schema") != CONFIG_SCHEMA:
        raise MLLidarPointLevelDatasetError(
            "config schema mismatch"
        )

    if payload.get("schema_version") != 1:
        raise MLLidarPointLevelDatasetError(
            "config version mismatch"
        )

    if payload.get(
        "content_sha256"
    ) != content_sha256(payload):
        raise MLLidarPointLevelDatasetError(
            "config digest mismatch"
        )

    if payload.get(
        "windows_per_trajectory"
    ) != 50:
        raise MLLidarPointLevelDatasetError(
            "windows-per-trajectory changed"
        )

    if payload.get(
        "expected_total_windows"
    ) != 1100:
        raise MLLidarPointLevelDatasetError(
            "window count changed"
        )

    if payload.get(
        "expected_new_corrupted_registrations"
    ) != 3300:
        raise MLLidarPointLevelDatasetError(
            "registration count changed"
        )

    if payload.get(
        "expected_total_samples"
    ) != 4400:
        raise MLLidarPointLevelDatasetError(
            "sample count changed"
        )

    if payload.get(
        "expected_phase4_diagnostic_counts"
    ) != EXPECTED_DIAGNOSTIC_COUNTS:
        raise MLLidarPointLevelDatasetError(
            "Phase-4 diagnostic counts changed"
        )

    boundary = payload.get(
        "scientific_boundary"
    )

    for field in (
        "real_physical_health_truth",
        "model_fit_authorized",
        "VALIDATION_open",
        "CONFIRMATION_open",
        "reference_data_used",
        "ATE_RPE",
    ):
        if boundary.get(field) is not False:
            raise MLLidarPointLevelDatasetError(
                field + " must remain false"
            )
