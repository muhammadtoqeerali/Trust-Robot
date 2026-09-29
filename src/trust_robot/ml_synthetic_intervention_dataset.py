"""TRAIN-only synthetic-intervention ML development dataset.

This module creates a mechanical development benchmark from the already
frozen Phase-4 M2DGR LiDAR diagnostic feature artifacts.

Important semantic boundary:

* class 0 means no TRUST-ROBOT synthetic intervention was applied;
* class 1 means the frozen EVENT_REPEAT operator was applied to the
  diagnostic-feature event stream;
* neither class is real physical sensor-health ground truth;
* this module does not train the final TRUST-ROBOT health model.

The first benchmark intentionally uses a two-event temporal window of the
five frozen LiDAR diagnostic features.  The Phase-3 EVENT_REPEAT mechanism
replaces the second feature-event payload with the preceding payload while
preserving event progression.

The EventStream timestamps used by the corruption kernel are local synthetic
ordinals (0, 1) only.  They are not physical measurement time and are not
model inputs.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence
import json
import math

import numpy as np

from .corruption import (
    CorruptionFamily,
    CorruptionSpec,
    EventStream,
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
from .diagnostic_artifacts import (
    validate_lidar_diagnostic_artifact_record,
)


DATASET_SCHEMA = (
    "TRUST_ROBOT_M2DGR_TRAIN_ONLY_SYNTHETIC_INTERVENTION_DATASET_V1"
)

SAMPLE_SCHEMA = (
    "TRUST_ROBOT_M2DGR_SYNTHETIC_INTERVENTION_SAMPLE_V1"
)

CONFIG_SCHEMA = (
    "TRUST_ROBOT_M2DGR_ML_SYNTHETIC_INTERVENTION_DATASET_CONFIG_V1"
)

FEATURE_NAMES = (
    "source_point_count",
    "target_point_count",
    "fixed_point_iterations",
    "final_correspondence_count",
    "final_nearest_neighbor_rmse_m",
)

WINDOW_FEATURE_NAMES = tuple(
    "previous__" + name
    for name in FEATURE_NAMES
) + tuple(
    "current__" + name
    for name in FEATURE_NAMES
)

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

INTERVENTION_FAMILY = CorruptionFamily.EVENT_REPEAT

INTERVENTION_START_INDEX = 1
INTERVENTION_LENGTH = 1

LOCAL_KERNEL_TIMESTAMPS_NS = (
    0,
    1,
)


class MLSyntheticInterventionDatasetError(
    ValueError
):
    """Raised when the TRAIN-only development dataset contract is violated."""


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


def _require_sha256(
    value: object,
    *,
    name: str,
) -> str:
    if (
        not isinstance(
            value,
            str,
        )
        or len(
            value
        ) != 64
    ):
        raise MLSyntheticInterventionDatasetError(
            name
            + " must be a SHA-256 hexadecimal string"
        )

    try:
        int(
            value,
            16,
        )
    except ValueError as exc:
        raise MLSyntheticInterventionDatasetError(
            name
            + " must be hexadecimal"
        ) from exc

    return value.lower()


def _feature_vector(
    values: Sequence[object],
) -> np.ndarray:
    if isinstance(
        values,
        (
            str,
            bytes,
            bytearray,
        ),
    ):
        raise MLSyntheticInterventionDatasetError(
            "feature_values must be numeric sequence"
        )

    if len(
        values
    ) != len(
        FEATURE_NAMES
    ):
        raise MLSyntheticInterventionDatasetError(
            "exactly five frozen LiDAR feature values are required"
        )

    result = np.asarray(
        [
            float(
                value
            )
            for value in values
        ],
        dtype=np.float64,
    )

    if result.shape != (
        len(
            FEATURE_NAMES
        ),
    ):
        raise MLSyntheticInterventionDatasetError(
            "feature vector shape changed"
        )

    if not np.all(
        np.isfinite(
            result
        )
    ):
        raise MLSyntheticInterventionDatasetError(
            "feature vector must be finite"
        )

    return result


def partition_for_trajectory(
    trajectory: str,
) -> str:
    if trajectory in DEVELOPMENT_TRAIN:
        return "development_train"

    if trajectory in DEVELOPMENT_CHECK:
        return "development_check"

    raise MLSyntheticInterventionDatasetError(
        "trajectory is outside frozen TRAIN-only ML development cohort"
    )


def build_corruption_spec(
) -> CorruptionSpec:
    return CorruptionSpec(
        family=
            INTERVENTION_FAMILY,

        modality=
            SensorModality.LIDAR,

        start_index=
            INTERVENTION_START_INDEX,

        length=
            INTERVENTION_LENGTH,

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
        plan_name=(
            "trust_robot_m2dgr_train_lidar_feature_stream_"
            "event_repeat_v1"
        ),

        target_selection_source=
            TargetSelectionSource(
                "deterministic_train_metadata_rule"
            ),

        target_selection_rationale=(
            "Within each prospectively defined two-event diagnostic-feature "
            "window, event index 1 is the unique second event and is therefore "
            "the deterministic EVENT_REPEAT target."
        ),

        magnitude_selection_source=
            MagnitudeSelectionSource(
                "explicit_pre_execution_literal"
            ),

        magnitude_selection_rationale=(
            "length=1 is prospectively fixed before dataset generation as "
            "the minimal non-zero EVENT_REPEAT mechanical intervention."
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
            "configs/trust_robot/phase4_lidar_train_diagnostic_artifacts_v1.json",
        ),

        metadata={
            "outer_split":
                "TRAIN",

            "benchmark_scope":
                "synthetic_intervention_discrimination",

            "feature_stream_only":
                True,

            "real_physical_health_truth":
                False,
        },
    )


def build_selection_binding(
) -> dict[str, Any]:
    return dict(
        bind_spec_to_selection(
            build_corruption_spec(),
            build_selection_record(),
        )
    )


def selection_binding_sha256(
) -> str:
    return sha256(
        canonical_json_bytes(
            build_selection_binding()
        )
    ).hexdigest()


def build_contract(
) -> dict[str, Any]:
    return {
        "schema":
            DATASET_SCHEMA,

        "schema_version":
            1,

        "source": {
            "dataset":
                "M2DGR",

            "outer_split":
                "TRAIN",

            "source_artifact":
                "Phase4 validated LiDAR diagnostic features",

            "source_feature_order":
                list(
                    FEATURE_NAMES
                ),

            "raw_rosbag_reprocessing_required":
                False,
        },

        "development_split": {
            "method":
                "trajectory_group_holdout",

            "development_train":
                list(
                    DEVELOPMENT_TRAIN
                ),

            "development_check":
                list(
                    DEVELOPMENT_CHECK
                ),

            "random_row_split_allowed":
                False,

            "trajectory_cross_partition_allowed":
                False,
        },

        "sample_representation": {
            "window_event_count":
                2,

            "model_input_feature_names":
                list(
                    WINDOW_FEATURE_NAMES
                ),

            "model_input_feature_count":
                len(
                    WINDOW_FEATURE_NAMES
                ),

            "physical_measurement_time_used":
                False,

            "cross_modal_alignment_used":
                False,

            "reference_data_used":
                False,
        },

        "synthetic_intervention": {
            "family":
                INTERVENTION_FAMILY.value,

            "modality":
                SensorModality.LIDAR.value,

            "local_window_target_index":
                INTERVENTION_START_INDEX,

            "length":
                INTERVENTION_LENGTH,

            "kernel_timestamp_semantics":
                "synthetic_local_ordinal_only",

            "kernel_timestamp_values_ns":
                list(
                    LOCAL_KERNEL_TIMESTAMPS_NS
                ),

            "kernel_timestamps_are_physical_measurement_time":
                False,

            "selection_binding_sha256":
                selection_binding_sha256(),
        },

        "classes": {
            "0":
                "uncorrupted_source_window",

            "1":
                "declared_synthetic_EVENT_REPEAT",
        },

        "scientific_boundary": {
            "labels_are_synthetic_intervention_truth":
                True,

            "labels_are_real_physical_health_truth":
                False,

            "final_health_model_training":
                False,

            "health_state_assignment":
                False,

            "validation_access":
                False,

            "confirmation_access":
                False,

            "ATE_RPE":
                False,
        },
    }


def validate_config(
    payload: Mapping[str, Any],
) -> None:
    if payload.get(
        "schema"
    ) != CONFIG_SCHEMA:
        raise MLSyntheticInterventionDatasetError(
            "config schema mismatch"
        )

    if payload.get(
        "schema_version"
    ) != 1:
        raise MLSyntheticInterventionDatasetError(
            "config version mismatch"
        )

    stored = payload.get(
        "content_sha256"
    )

    if (
        not isinstance(
            stored,
            str,
        )
        or stored != content_sha256(
            payload
        )
    ):
        raise MLSyntheticInterventionDatasetError(
            "config content digest mismatch"
        )

    split = payload.get(
        "development_split"
    )

    if not isinstance(
        split,
        Mapping,
    ):
        raise MLSyntheticInterventionDatasetError(
            "development_split missing"
        )

    if tuple(
        split.get(
            "development_train",
            (),
        )
    ) != DEVELOPMENT_TRAIN:
        raise MLSyntheticInterventionDatasetError(
            "development_train changed"
        )

    if tuple(
        split.get(
            "development_check",
            (),
        )
    ) != DEVELOPMENT_CHECK:
        raise MLSyntheticInterventionDatasetError(
            "development_check changed"
        )

    if split.get(
        "random_row_split_allowed"
    ) is not False:
        raise MLSyntheticInterventionDatasetError(
            "row-level split must remain forbidden"
        )

    sources = payload.get(
        "source_files"
    )

    if (
        not isinstance(
            sources,
            Mapping,
        )
        or set(
            sources
        ) != set(
            ALL_TRAIN
        )
    ):
        raise MLSyntheticInterventionDatasetError(
            "source file set must equal the 22 frozen TRAIN trajectories"
        )

    expected_total = 0

    for trajectory in ALL_TRAIN:
        source = sources[
            trajectory
        ]

        if not isinstance(
            source,
            Mapping,
        ):
            raise MLSyntheticInterventionDatasetError(
                "source file entry must be mapping"
            )

        _require_sha256(
            source.get(
                "sha256"
            ),
            name=(
                trajectory
                + ".sha256"
            ),
        )

        count = source.get(
            "record_count"
        )

        if (
            type(
                count
            ) is not int
            or count < 2
        ):
            raise MLSyntheticInterventionDatasetError(
                "source record count must be integer >=2"
            )

        expected_total += count

    if expected_total != 90992:
        raise MLSyntheticInterventionDatasetError(
            "frozen Phase-4 total record count changed"
        )

    if payload.get(
        "expected_total_input_records"
    ) != 90992:
        raise MLSyntheticInterventionDatasetError(
            "expected input count changed"
        )

    if payload.get(
        "expected_total_window_pairs"
    ) != 90970:
        raise MLSyntheticInterventionDatasetError(
            "expected window-pair count changed"
        )

    if payload.get(
        "expected_total_samples"
    ) != 181940:
        raise MLSyntheticInterventionDatasetError(
            "expected sample count changed"
        )

    boundary = payload.get(
        "scientific_boundary"
    )

    if not isinstance(
        boundary,
        Mapping,
    ):
        raise MLSyntheticInterventionDatasetError(
            "scientific boundary missing"
        )

    required_false = (
        "real_physical_health_truth",
        "final_health_model_training_authorized",
        "validation_access",
        "confirmation_access",
        "reference_data_access",
        "ATE_RPE",
    )

    for field in required_false:
        if boundary.get(
            field
        ) is not False:
            raise MLSyntheticInterventionDatasetError(
                field
                + " must remain false"
            )


def _sample_id(
    *,
    trajectory: str,
    development_partition: str,
    source_scan_index: int,
    previous_sha256: str,
    current_sha256: str,
    label: int,
) -> str:
    payload = {
        "trajectory":
            trajectory,

        "development_partition":
            development_partition,

        "source_scan_index":
            source_scan_index,

        "previous_sha256":
            previous_sha256,

        "current_sha256":
            current_sha256,

        "label":
            label,

        "intervention_family":
            (
                "NONE"
                if label == 0
                else INTERVENTION_FAMILY.value
            ),

        "dataset_schema":
            DATASET_SCHEMA,
    }

    return (
        "TRUST_ML_SAMPLE_"
        + sha256(
            canonical_json_bytes(
                payload
            )
        ).hexdigest()[
            :24
        ]
    )


def build_window_samples_from_vectors(
    *,
    trajectory: str,
    development_partition: str,
    source_scan_index: int,
    previous_feature_values: Sequence[object],
    current_feature_values: Sequence[object],
    previous_source_record_sha256: str,
    current_source_record_sha256: str,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
]:
    expected_partition = partition_for_trajectory(
        trajectory
    )

    if (
        development_partition
        != expected_partition
    ):
        raise MLSyntheticInterventionDatasetError(
            "trajectory development partition mismatch"
        )

    if (
        type(
            source_scan_index
        ) is not int
        or source_scan_index < 2
    ):
        raise MLSyntheticInterventionDatasetError(
            "source_scan_index must be integer >=2"
        )

    previous_sha = _require_sha256(
        previous_source_record_sha256,
        name=
            "previous_source_record_sha256",
    )

    current_sha = _require_sha256(
        current_source_record_sha256,
        name=
            "current_source_record_sha256",
    )

    previous = _feature_vector(
        previous_feature_values
    )

    current = _feature_vector(
        current_feature_values
    )

    clean_stream = EventStream(
        modality=
            SensorModality.LIDAR,

        source_id=(
            trajectory
            + ":phase4_lidar_diagnostic_two_event_window"
        ),

        timestamps_ns=
            np.asarray(
                LOCAL_KERNEL_TIMESTAMPS_NS,
                dtype=np.int64,
            ),

        payloads=(
            previous.copy(),
            current.copy(),
        ),

        metadata={
            "outer_split":
                "TRAIN",

            "development_partition":
                development_partition,

            "source_scan_index":
                source_scan_index,

            "time_semantics":
                "synthetic_local_ordinal_for_corruption_kernel_only",

            "physical_measurement_time":
                False,

            "reference_data_used":
                False,
        },
    )

    paired = apply_corruption(
        clean_stream,
        build_corruption_spec(),
    )

    if len(
        paired.truths
    ) != 1:
        raise MLSyntheticInterventionDatasetError(
            "EVENT_REPEAT must produce exactly one truth record"
        )

    corrupt_previous = np.asarray(
        paired.corrupt.payloads[
            0
        ],
        dtype=np.float64,
    )

    corrupt_current = np.asarray(
        paired.corrupt.payloads[
            1
        ],
        dtype=np.float64,
    )

    if not np.array_equal(
        corrupt_previous,
        previous,
    ):
        raise MLSyntheticInterventionDatasetError(
            "EVENT_REPEAT unexpectedly changed previous event"
        )

    if not np.array_equal(
        corrupt_current,
        previous,
    ):
        raise MLSyntheticInterventionDatasetError(
            "EVENT_REPEAT did not repeat preceding payload"
        )

    clean_values = tuple(
        float(
            value
        )
        for value
        in np.concatenate(
            (
                previous,
                current,
            )
        )
    )

    corrupt_values = tuple(
        float(
            value
        )
        for value
        in np.concatenate(
            (
                corrupt_previous,
                corrupt_current,
            )
        )
    )

    common = {
        "schema":
            SAMPLE_SCHEMA,

        "outer_split":
            "TRAIN",

        "development_partition":
            development_partition,

        "trajectory":
            trajectory,

        "source_scan_index":
            source_scan_index,

        "previous_source_record_sha256":
            previous_sha,

        "current_source_record_sha256":
            current_sha,

        "feature_names":
            list(
                WINDOW_FEATURE_NAMES
            ),

        "feature_stream_corruption_scope":
            "frozen_lidar_diagnostic_feature_event_stream",

        "physical_measurement_time_used":
            False,

        "cross_modal_alignment_used":
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

                development_partition=
                    development_partition,

                source_scan_index=
                    source_scan_index,

                previous_sha256=
                    previous_sha,

                current_sha256=
                    current_sha,

                label=
                    0,
            ),

        "label":
            0,

        "label_name":
            "uncorrupted_source_window",

        "synthetic_intervention_applied":
            False,

        "intervention_family":
            "NONE",

        "feature_values":
            list(
                clean_values
            ),
    }

    corrupt_sample = {
        **common,

        "sample_id":
            _sample_id(
                trajectory=
                    trajectory,

                development_partition=
                    development_partition,

                source_scan_index=
                    source_scan_index,

                previous_sha256=
                    previous_sha,

                current_sha256=
                    current_sha,

                label=
                    1,
            ),

        "label":
            1,

        "label_name":
            "declared_synthetic_EVENT_REPEAT",

        "synthetic_intervention_applied":
            True,

        "intervention_family":
            INTERVENTION_FAMILY.value,

        "feature_values":
            list(
                corrupt_values
            ),
    }

    validate_sample(
        clean_sample
    )

    validate_sample(
        corrupt_sample
    )

    return (
        clean_sample,
        corrupt_sample,
    )


def validate_sample(
    sample: Mapping[str, Any],
) -> None:
    expected_keys = {
        "schema",
        "sample_id",
        "outer_split",
        "development_partition",
        "trajectory",
        "source_scan_index",
        "previous_source_record_sha256",
        "current_source_record_sha256",
        "label",
        "label_name",
        "synthetic_intervention_applied",
        "intervention_family",
        "feature_names",
        "feature_values",
        "feature_stream_corruption_scope",
        "physical_measurement_time_used",
        "cross_modal_alignment_used",
        "reference_data_used",
        "validation_data_used",
        "confirmation_data_used",
        "label_is_real_physical_health_truth",
    }

    if set(
        sample
    ) != expected_keys:
        raise MLSyntheticInterventionDatasetError(
            "sample field set changed"
        )

    if sample[
        "schema"
    ] != SAMPLE_SCHEMA:
        raise MLSyntheticInterventionDatasetError(
            "sample schema mismatch"
        )

    trajectory = sample[
        "trajectory"
    ]

    if not isinstance(
        trajectory,
        str,
    ):
        raise MLSyntheticInterventionDatasetError(
            "trajectory must be string"
        )

    expected_partition = partition_for_trajectory(
        trajectory
    )

    if sample[
        "development_partition"
    ] != expected_partition:
        raise MLSyntheticInterventionDatasetError(
            "sample partition mismatch"
        )

    if sample[
        "outer_split"
    ] != "TRAIN":
        raise MLSyntheticInterventionDatasetError(
            "sample outer split must be TRAIN"
        )

    if tuple(
        sample[
            "feature_names"
        ]
    ) != WINDOW_FEATURE_NAMES:
        raise MLSyntheticInterventionDatasetError(
            "sample feature order changed"
        )

    values = sample[
        "feature_values"
    ]

    if (
        not isinstance(
            values,
            list,
        )
        or len(
            values
        ) != len(
            WINDOW_FEATURE_NAMES
        )
    ):
        raise MLSyntheticInterventionDatasetError(
            "sample feature vector length mismatch"
        )

    for value in values:
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
            raise MLSyntheticInterventionDatasetError(
                "sample feature value must be finite numeric"
            )

    label = sample[
        "label"
    ]

    if label == 0:
        if (
            sample[
                "label_name"
            ]
            != "uncorrupted_source_window"
            or sample[
                "synthetic_intervention_applied"
            ]
            is not False
            or sample[
                "intervention_family"
            ]
            != "NONE"
        ):
            raise MLSyntheticInterventionDatasetError(
                "class-0 semantics changed"
            )

    elif label == 1:
        if (
            sample[
                "label_name"
            ]
            != "declared_synthetic_EVENT_REPEAT"
            or sample[
                "synthetic_intervention_applied"
            ]
            is not True
            or sample[
                "intervention_family"
            ]
            != INTERVENTION_FAMILY.value
        ):
            raise MLSyntheticInterventionDatasetError(
                "class-1 semantics changed"
            )

    else:
        raise MLSyntheticInterventionDatasetError(
            "sample label must be 0 or 1"
        )

    for field in (
        "physical_measurement_time_used",
        "cross_modal_alignment_used",
        "reference_data_used",
        "validation_data_used",
        "confirmation_data_used",
        "label_is_real_physical_health_truth",
    ):
        if sample[
            field
        ] is not False:
            raise MLSyntheticInterventionDatasetError(
                field
                + " must remain false"
            )

    _require_sha256(
        sample[
            "previous_source_record_sha256"
        ],
        name=
            "previous_source_record_sha256",
    )

    _require_sha256(
        sample[
            "current_source_record_sha256"
        ],
        name=
            "current_source_record_sha256",
    )


def iter_trajectory_samples(
    feature_jsonl: Path,
    *,
    trajectory: str,
    development_partition: str,
) -> Iterator[
    dict[str, Any]
]:
    expected_partition = partition_for_trajectory(
        trajectory
    )

    if (
        development_partition
        != expected_partition
    ):
        raise MLSyntheticInterventionDatasetError(
            "trajectory partition mismatch"
        )

    previous: Mapping[
        str,
        Any,
    ] | None = None

    previous_line_number: int | None = None

    with feature_jsonl.open(
        "r",
        encoding="utf-8",
    ) as handle:
        for line_number, raw_line in enumerate(
            handle,
            start=1,
        ):
            if not raw_line.strip():
                raise MLSyntheticInterventionDatasetError(
                    "blank diagnostic JSONL line encountered"
                )

            try:
                record = json.loads(
                    raw_line
                )
            except json.JSONDecodeError as exc:
                raise MLSyntheticInterventionDatasetError(
                    "invalid diagnostic JSONL"
                ) from exc

            validate_lidar_diagnostic_artifact_record(
                record
            )

            if record.get(
                "trajectory"
            ) != trajectory:
                raise MLSyntheticInterventionDatasetError(
                    "diagnostic trajectory identity mismatch"
                )

            scan_index = record.get(
                "scan_index"
            )

            if (
                type(
                    scan_index
                ) is not int
                or scan_index < 1
            ):
                raise MLSyntheticInterventionDatasetError(
                    "diagnostic scan_index invalid"
                )

            if previous is not None:
                previous_scan_index = previous[
                    "scan_index"
                ]

                if scan_index != (
                    previous_scan_index
                    + 1
                ):
                    raise MLSyntheticInterventionDatasetError(
                        "diagnostic scan indices are not consecutive"
                    )

                clean_sample, corrupt_sample = (
                    build_window_samples_from_vectors(
                        trajectory=
                            trajectory,

                        development_partition=
                            development_partition,

                        source_scan_index=
                            scan_index,

                        previous_feature_values=
                            previous[
                                "feature_values"
                            ],

                        current_feature_values=
                            record[
                                "feature_values"
                            ],

                        previous_source_record_sha256=
                            previous[
                                "content_sha256"
                            ],

                        current_source_record_sha256=
                            record[
                                "content_sha256"
                            ],
                    )
                )

                yield clean_sample
                yield corrupt_sample

            previous = record
            previous_line_number = line_number

    if previous is None:
        raise MLSyntheticInterventionDatasetError(
            "diagnostic feature JSONL is empty"
        )

    if previous_line_number is None:
        raise MLSyntheticInterventionDatasetError(
            "internal line-count state invalid"
        )
