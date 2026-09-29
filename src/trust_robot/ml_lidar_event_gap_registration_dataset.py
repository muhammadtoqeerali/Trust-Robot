"""Harder TRAIN-only LiDAR synthetic-intervention benchmark.

The benchmark uses real M2DGR TRAIN LiDAR point clouds.

For each prospectively selected non-overlapping 3-scan window:

    clean stream:   scan0, scan1, scan2
    corrupt stream: scan0,        scan2

The frozen Phase-2 registration kernel therefore produces:

    clean observation:   scan1 -> scan2
    gap observation:     scan0 -> scan2

Only the five frozen registration diagnostics are model features.

The corruption family, truth, trajectory identity, timestamps, scan indices,
raw hashes, registration topology, and clean/corrupt pairing are provenance
only and are never model features.

Labels represent synthetic intervention truth, not physical sensor health.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping, Sequence
import json
import math

from .corruption import (
    CorruptionFamily,
    CorruptionSpec,
    ScenarioContext,
    SensorModality,
    apply_corruption,
)
from .corruption_selection import (
    CorruptionSelectionRecord,
    MagnitudeSelectionSource,
    TargetSelectionSource,
    bind_spec_to_selection,
)
from .lidar_corruption_adapter import (
    M2DGRVelodyneCleanAdapterResult,
    adapt_m2dgr_velodyne_messages,
)
from .lidar_corruption_estimator import (
    run_paired_frozen_lidar_registration,
)


CONFIG_SCHEMA = (
    "TRUST_ROBOT_M2DGR_LIDAR_EVENT_GAP_REGISTRATION_DATASET_CONFIG_V1"
)

DATASET_SCHEMA = (
    "TRUST_ROBOT_M2DGR_LIDAR_EVENT_GAP_REGISTRATION_DATASET_V1"
)

SAMPLE_SCHEMA = (
    "TRUST_ROBOT_M2DGR_LIDAR_EVENT_GAP_REGISTRATION_SAMPLE_V1"
)

FEATURE_NAMES = (
    "source_point_count",
    "target_point_count",
    "fixed_point_iterations",
    "final_correspondence_count",
    "final_nearest_neighbor_rmse_m",
)

WINDOWS_PER_TRAJECTORY = 100

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


class MLLidarEventGapDatasetError(
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


def partition_for_trajectory(
    trajectory: str,
) -> str:
    if trajectory in DEVELOPMENT_TRAIN:
        return "development_train"

    if trajectory in DEVELOPMENT_CHECK:
        return "development_check"

    raise MLLidarEventGapDatasetError(
        "trajectory outside frozen TRAIN development cohort"
    )


def evenly_spaced_window_starts(
    diagnostic_count: int,
    *,
    selected_count: int = WINDOWS_PER_TRAJECTORY,
) -> tuple[int, ...]:
    if (
        type(
            diagnostic_count
        ) is not int
        or diagnostic_count < 2
    ):
        raise MLLidarEventGapDatasetError(
            "diagnostic_count must be integer >=2"
        )

    if (
        type(
            selected_count
        ) is not int
        or selected_count < 2
    ):
        raise MLLidarEventGapDatasetError(
            "selected_count must be integer >=2"
        )

    eligible_window_count = (
        diagnostic_count
        - 1
    )

    if eligible_window_count < selected_count:
        raise MLLidarEventGapDatasetError(
            "not enough eligible three-scan windows"
        )

    result = tuple(
        int(
            round(
                k
                * (
                    eligible_window_count
                    - 1
                )
                / (
                    selected_count
                    - 1
                )
            )
        )
        for k in range(
            selected_count
        )
    )

    if len(
        set(
            result
        )
    ) != selected_count:
        raise MLLidarEventGapDatasetError(
            "window selection generated duplicate indices"
        )

    for left, right in zip(
        result,
        result[
            1:
        ],
    ):
        if right - left < 3:
            raise MLLidarEventGapDatasetError(
                "selected three-scan windows overlap"
            )

    if result[
        0
    ] != 0:
        raise MLLidarEventGapDatasetError(
            "first selected window changed"
        )

    if result[
        -1
    ] != (
        eligible_window_count
        - 1
    ):
        raise MLLidarEventGapDatasetError(
            "last selected window changed"
        )

    return result


def build_event_gap_spec(
) -> CorruptionSpec:
    return CorruptionSpec(
        family=
            CorruptionFamily.EVENT_GAP,

        modality=
            SensorModality.LIDAR,

        start_index=
            1,

        length=
            1,

        scenario_context=
            ScenarioContext.UNATTRIBUTED,

        severity_id=
            None,

        seed=
            None,

        threat_model_id=
            None,

        parameters=
            {},
    )


def build_selection_record(
) -> CorruptionSelectionRecord:
    return CorruptionSelectionRecord(
        plan_name=
            "trust_robot_m2dgr_lidar_event_gap_registration_benchmark_v1",

        target_selection_source=
            TargetSelectionSource(
                "deterministic_train_metadata_rule"
            ),

        target_selection_rationale=(
            "The middle event of every prospectively selected three-scan "
            "window is the unique internal event and is removed."
        ),

        magnitude_selection_source=
            MagnitudeSelectionSource(
                "explicit_pre_execution_literal"
            ),

        magnitude_selection_rationale=(
            "Exactly one middle LiDAR scan is removed; this is the minimal "
            "non-zero EVENT_GAP instance and was fixed before execution."
        ),

        selection_locked_before_execution=
            True,

        estimator_output_used=
            False,

        registration_diagnostic_used=
            False,

        reference_data_used=
            False,

        ground_truth_metric_used=
            False,

        validation_metric_used=
            False,

        confirmation_test_used=
            False,

        source_artifacts=(
            "configs/trust_robot/phase3_corruption_selection_policy_v1.json",
            "configs/trust_robot/phase3_lidar_event_gap_real_smoke_v1.json",
            "configs/trust_robot/phase3_lidar_paired_estimator_registration_v1.json",
        ),

        metadata={
            "outer_split":
                "TRAIN",

            "windows_per_trajectory":
                WINDOWS_PER_TRAJECTORY,

            "window_selection":
                "deterministic_even_spacing_from_frozen_scan_count_metadata",

            "real_physical_health_truth":
                False,
        },
    )


def build_selection_binding(
) -> dict[str, Any]:
    return dict(
        bind_spec_to_selection(
            build_event_gap_spec(),
            build_selection_record(),
        )
    )


def validate_config(
    payload: Mapping[str, Any],
) -> None:
    if payload.get(
        "schema"
    ) != CONFIG_SCHEMA:
        raise MLLidarEventGapDatasetError(
            "config schema mismatch"
        )

    if payload.get(
        "schema_version"
    ) != 1:
        raise MLLidarEventGapDatasetError(
            "config version mismatch"
        )

    if payload.get(
        "content_sha256"
    ) != content_sha256(
        payload
    ):
        raise MLLidarEventGapDatasetError(
            "config digest mismatch"
        )

    if payload.get(
        "windows_per_trajectory"
    ) != WINDOWS_PER_TRAJECTORY:
        raise MLLidarEventGapDatasetError(
            "windows-per-trajectory changed"
        )

    counts = payload.get(
        "expected_phase4_diagnostic_counts"
    )

    if counts != EXPECTED_DIAGNOSTIC_COUNTS:
        raise MLLidarEventGapDatasetError(
            "frozen diagnostic counts changed"
        )

    split = payload.get(
        "development_split"
    )

    if not isinstance(
        split,
        Mapping,
    ):
        raise MLLidarEventGapDatasetError(
            "development split missing"
        )

    if tuple(
        split.get(
            "development_train",
            (),
        )
    ) != DEVELOPMENT_TRAIN:
        raise MLLidarEventGapDatasetError(
            "development train changed"
        )

    if tuple(
        split.get(
            "development_check",
            (),
        )
    ) != DEVELOPMENT_CHECK:
        raise MLLidarEventGapDatasetError(
            "development check changed"
        )

    if payload.get(
        "expected_total_windows"
    ) != 2200:
        raise MLLidarEventGapDatasetError(
            "expected total windows changed"
        )

    if payload.get(
        "expected_total_samples"
    ) != 4400:
        raise MLLidarEventGapDatasetError(
            "expected total samples changed"
        )

    boundary = payload.get(
        "scientific_boundary"
    )

    if not isinstance(
        boundary,
        Mapping,
    ):
        raise MLLidarEventGapDatasetError(
            "scientific boundary missing"
        )

    for field in (
        "real_physical_health_truth",
        "model_fit_authorized",
        "validation_access",
        "confirmation_access",
        "reference_data_access",
        "ATE_RPE",
    ):
        if boundary.get(
            field
        ) is not False:
            raise MLLidarEventGapDatasetError(
                field
                + " must remain false"
            )


def _feature_vector(
    diagnostics: Mapping[str, Any],
) -> list[
    float | int
]:
    values = []

    for name in FEATURE_NAMES:
        if name not in diagnostics:
            raise MLLidarEventGapDatasetError(
                "missing diagnostic feature "
                + name
            )

        value = diagnostics[
            name
        ]

        if (
            isinstance(
                value,
                bool,
            )
            or not isinstance(
                value,
                (
                    int,
                    float,
                ),
            )
            or not math.isfinite(
                float(
                    value
                )
            )
        ):
            raise MLLidarEventGapDatasetError(
                "diagnostic feature must be finite numeric"
            )

        values.append(
            value
        )

    return values


def _sample_id(
    *,
    trajectory: str,
    window_start_scan_index: int,
    label: int,
    window_fingerprint: str,
) -> str:
    value = {
        "trajectory":
            trajectory,

        "window_start_scan_index":
            window_start_scan_index,

        "label":
            label,

        "window_fingerprint":
            window_fingerprint,

        "schema":
            DATASET_SCHEMA,
    }

    return (
        "TRUST_GAP_SAMPLE_"
        + sha256(
            canonical_json_bytes(
                value
            )
        ).hexdigest()[
            :24
        ]
    )


def build_paired_samples_from_messages(
    *,
    trajectory: str,
    window_start_scan_index: int,
    messages: Sequence[object],
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    if len(
        messages
    ) != 3:
        raise MLLidarEventGapDatasetError(
            "exactly three LiDAR messages required"
        )

    partition = partition_for_trajectory(
        trajectory
    )

    adapted: M2DGRVelodyneCleanAdapterResult = (
        adapt_m2dgr_velodyne_messages(
            messages
        )
    )

    adapter_receipt = adapted.receipt_dict()

    if adapter_receipt.get(
        "event_count"
    ) != 3:
        raise MLLidarEventGapDatasetError(
            "adapter did not produce exactly three events"
        )

    pair = apply_corruption(
        adapted.stream,
        build_event_gap_spec(),
    )

    if pair.clean.n_events != 3:
        raise MLLidarEventGapDatasetError(
            "clean event count changed"
        )

    if pair.corrupt.n_events != 2:
        raise MLLidarEventGapDatasetError(
            "corrupt event count must equal two"
        )

    if len(
        pair.truths
    ) != 1:
        raise MLLidarEventGapDatasetError(
            "exactly one corruption truth required"
        )

    execution = (
        run_paired_frozen_lidar_registration(
            pair
        )
    )

    clean = execution.get(
        "clean"
    )

    corrupt = execution.get(
        "corrupt"
    )

    if not isinstance(
        clean,
        Mapping,
    ) or not isinstance(
        corrupt,
        Mapping,
    ):
        raise MLLidarEventGapDatasetError(
            "paired registration branches missing"
        )

    if clean.get(
        "origin_pairs"
    ) != [
        [
            0,
            1,
        ],
        [
            1,
            2,
        ],
    ]:
        raise MLLidarEventGapDatasetError(
            "clean registration topology changed"
        )

    if corrupt.get(
        "origin_pairs"
    ) != [
        [
            0,
            2,
        ],
    ]:
        raise MLLidarEventGapDatasetError(
            "EVENT_GAP registration topology changed"
        )

    clean_records = clean.get(
        "records"
    )

    corrupt_records = corrupt.get(
        "records"
    )

    if (
        not isinstance(
            clean_records,
            list,
        )
        or len(
            clean_records
        ) != 2
        or not isinstance(
            corrupt_records,
            list,
        )
        or len(
            corrupt_records
        ) != 1
    ):
        raise MLLidarEventGapDatasetError(
            "paired registration record counts changed"
        )

    clean_record = clean_records[
        1
    ]

    corrupt_record = corrupt_records[
        0
    ]

    if (
        clean_record.get(
            "previous_clean_origin_index"
        ) != 1
        or clean_record.get(
            "current_clean_origin_index"
        ) != 2
    ):
        raise MLLidarEventGapDatasetError(
            "clean model observation must be scan1->scan2"
        )

    if (
        corrupt_record.get(
            "previous_clean_origin_index"
        ) != 0
        or corrupt_record.get(
            "current_clean_origin_index"
        ) != 2
    ):
        raise MLLidarEventGapDatasetError(
            "gap model observation must be scan0->scan2"
        )

    event_records = adapter_receipt.get(
        "event_records"
    )

    if (
        not isinstance(
            event_records,
            list,
        )
        or len(
            event_records
        ) != 3
    ):
        raise MLLidarEventGapDatasetError(
            "adapter event provenance missing"
        )

    raw_hashes = [
        item[
            "raw_pointcloud_data_sha256"
        ]
        for item
        in event_records
    ]

    decoded_hashes = [
        item[
            "decoded_xyz_data_sha256"
        ]
        for item
        in event_records
    ]

    header_stamps = [
        int(
            item[
                "header_stamp_ns"
            ]
        )
        for item
        in event_records
    ]

    window_identity = {
        "trajectory":
            trajectory,

        "window_start_scan_index":
            window_start_scan_index,

        "raw_pointcloud_data_sha256":
            raw_hashes,

        "decoded_xyz_data_sha256":
            decoded_hashes,

        "header_stamps_ns":
            header_stamps,
    }

    window_fingerprint = sha256(
        canonical_json_bytes(
            window_identity
        )
    ).hexdigest()

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
            window_start_scan_index
            + 1,
            window_start_scan_index
            + 2,
        ],

        "window_fingerprint_sha256":
            window_fingerprint,

        "raw_pointcloud_data_sha256":
            raw_hashes,

        "decoded_xyz_data_sha256":
            decoded_hashes,

        "header_stamps_ns":
            header_stamps,

        "header_stamps_are_model_features":
            False,

        "physical_measurement_time_verified":
            False,

        "feature_names":
            list(
                FEATURE_NAMES
            ),

        "trajectory_identity_is_model_feature":
            False,

        "corruption_truth_is_model_feature":
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

    clean_sample = {
        **common,

        "sample_id":
            _sample_id(
                trajectory=
                    trajectory,

                window_start_scan_index=
                    window_start_scan_index,

                label=
                    0,

                window_fingerprint=
                    window_fingerprint,
            ),

        "label":
            0,

        "label_name":
            "clean_middle_to_final_registration",

        "synthetic_intervention_applied":
            False,

        "intervention_family":
            "NONE",

        "registration_origin_pair": [
            1,
            2,
        ],

        "feature_values":
            _feature_vector(
                clean_record[
                    "diagnostics"
                ]
            ),
    }

    gap_sample = {
        **common,

        "sample_id":
            _sample_id(
                trajectory=
                    trajectory,

                window_start_scan_index=
                    window_start_scan_index,

                label=
                    1,

                window_fingerprint=
                    window_fingerprint,
            ),

        "label":
            1,

        "label_name":
            "synthetic_event_gap_first_to_final_registration",

        "synthetic_intervention_applied":
            True,

        "intervention_family":
            CorruptionFamily.EVENT_GAP.value,

        "registration_origin_pair": [
            0,
            2,
        ],

        "feature_values":
            _feature_vector(
                corrupt_record[
                    "diagnostics"
                ]
            ),
    }

    provenance = {
        "trajectory":
            trajectory,

        "development_partition":
            partition,

        "window_start_scan_index":
            window_start_scan_index,

        "window_fingerprint_sha256":
            window_fingerprint,

        "adapter_receipt_content_sha256":
            adapter_receipt[
                "content_sha256"
            ],

        "clean_stream_fingerprint_sha256":
            pair.clean.fingerprint(),

        "corrupt_stream_fingerprint_sha256":
            pair.corrupt.fingerprint(),

        "corruption_spec_id":
            pair.truths[
                0
            ].spec.spec_id,

        "corruption_injection_id":
            pair.truths[
                0
            ].injection_id,

        "paired_registration_content_sha256":
            execution[
                "content_sha256"
            ],

        "raw_pointcloud_data_sha256":
            raw_hashes,

        "decoded_xyz_data_sha256":
            decoded_hashes,
    }

    return (
        clean_sample,
        gap_sample,
        provenance,
    )
