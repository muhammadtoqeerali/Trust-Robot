from __future__ import annotations

from hashlib import sha256
from typing import Any
import json
import math

import numpy as np

from .corruption import (
    EventStream,
    PairedCorruption,
    SensorModality,
)
from .lidar_frontend import (
    register_current_scan_to_previous,
)


REGISTRATION_PATH_SCHEMA = (
    "TRUST_ROBOT_PHASE3_FROZEN_LIDAR_REGISTRATION_PATH_V1"
)


class LidarCorruptionEstimatorError(ValueError):
    """Raised when paired estimator-plumbing input is invalid."""


def _canonical_json(
    value: object,
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _array_sha(
    value,
) -> str:
    array = np.ascontiguousarray(
        value
    )

    return sha256(
        array.tobytes(
            order="C"
        )
    ).hexdigest()


def _pose_payload(
    pose,
) -> dict[str, object]:
    return {
        "translation_m": [
            float(
                value
            )
            for value
            in pose.translation_m
        ],

        "quaternion_wxyz": [
            float(
                value
            )
            for value
            in pose.quaternion_wxyz
        ],
    }


def _diagnostic_payload(
    diagnostics,
) -> dict[str, object]:
    rmse = float(
        diagnostics.final_nearest_neighbor_rmse_m
    )

    if not math.isfinite(
        rmse
    ):
        raise LidarCorruptionEstimatorError(
            "frozen registration produced non-finite diagnostic RMSE"
        )

    return {
        "source_point_count":
            int(
                diagnostics.source_point_count
            ),

        "target_point_count":
            int(
                diagnostics.target_point_count
            ),

        "fixed_point_iterations":
            int(
                diagnostics.fixed_point_iterations
            ),

        "final_correspondence_count":
            int(
                diagnostics.final_correspondence_count
            ),

        "final_nearest_neighbor_rmse_m":
            rmse,

        "convergence_rule":
            str(
                diagnostics.convergence_rule
            ),

        "correspondence_rejection_used":
            bool(
                diagnostics.correspondence_rejection_used
            ),

        "voxel_downsampling_used":
            bool(
                diagnostics.voxel_downsampling_used
            ),

        "interpretation":
            "execution_diagnostic_only_not_accuracy_score",
    }


def run_frozen_lidar_registration_path(
    stream: EventStream,
) -> dict[str, Any]:
    if stream.modality is not SensorModality.LIDAR:
        raise LidarCorruptionEstimatorError(
            "frozen LiDAR registration path requires lidar modality"
        )

    if stream.n_events < 2:
        raise LidarCorruptionEstimatorError(
            "registration path requires at least two events"
        )

    if not stream.timestamps_strictly_increasing():
        raise LidarCorruptionEstimatorError(
            "registration path requires strictly increasing event labels"
        )

    stream_fingerprint_before = (
        stream.fingerprint()
    )

    records = []

    for pair_index in range(
        1,
        stream.n_events,
    ):
        previous_index = (
            pair_index
            - 1
        )

        current_index = pair_index

        previous_xyz = stream.payloads[
            previous_index
        ]

        current_xyz = stream.payloads[
            current_index
        ]

        result = register_current_scan_to_previous(
            previous_xyz,
            current_xyz,
        )

        records.append(
            {
                "pair_index":
                    previous_index,

                "previous_event_index":
                    previous_index,

                "current_event_index":
                    current_index,

                "previous_clean_origin_index":
                    int(
                        stream.origin_indices[
                            previous_index
                        ]
                    ),

                "current_clean_origin_index":
                    int(
                        stream.origin_indices[
                            current_index
                        ]
                    ),

                "previous_timestamp_ns":
                    int(
                        stream.timestamps_ns[
                            previous_index
                        ]
                    ),

                "current_timestamp_ns":
                    int(
                        stream.timestamps_ns[
                            current_index
                        ]
                    ),

                "previous_xyz_sha256":
                    _array_sha(
                        previous_xyz
                    ),

                "current_xyz_sha256":
                    _array_sha(
                        current_xyz
                    ),

                "previous_lidar_T_current_lidar":
                    _pose_payload(
                        result.previous_lidar_T_current_lidar
                    ),

                "diagnostics":
                    _diagnostic_payload(
                        result.diagnostics
                    ),
            }
        )

    stream_fingerprint_after = (
        stream.fingerprint()
    )

    if (
        stream_fingerprint_before
        != stream_fingerprint_after
    ):
        raise LidarCorruptionEstimatorError(
            "registration execution mutated EventStream"
        )

    payload: dict[str, Any] = {
        "schema":
            REGISTRATION_PATH_SCHEMA,

        "modality":
            stream.modality.value,

        "source_id":
            stream.source_id,

        "event_count":
            stream.n_events,

        "increment_count":
            len(
                records
            ),

        "origin_pairs": [
            [
                record[
                    "previous_clean_origin_index"
                ],
                record[
                    "current_clean_origin_index"
                ],
            ]
            for record
            in records
        ],

        "stream_fingerprint_sha256":
            stream_fingerprint_before,

        "records":
            records,

        "scientific_scope": {
            "frozen_phase2_registration_kernel_used":
                True,

            "reference_data_used":
                False,

            "confirmation_test_data_used":
                False,

            "ground_truth_association_performed":
                False,

            "alignment_performed":
                False,

            "ate_computed":
                False,

            "rpe_computed":
                False,

            "trajectory_scoring_performed":
                False,

            "estimator_scoring_performed":
                False,

            "accuracy_claimed":
                False,

            "registration_diagnostics_are_accuracy_score":
                False,
        },
    }

    payload[
        "content_sha256"
    ] = sha256(
        _canonical_json(
            payload
        ).encode(
            "utf-8"
        )
    ).hexdigest()

    return payload


def run_paired_frozen_lidar_registration(
    pair: PairedCorruption,
) -> dict[str, Any]:
    clean_before = pair.clean.fingerprint()
    corrupt_before = pair.corrupt.fingerprint()

    clean = run_frozen_lidar_registration_path(
        pair.clean
    )

    corrupt = run_frozen_lidar_registration_path(
        pair.corrupt
    )

    if pair.clean.fingerprint() != clean_before:
        raise LidarCorruptionEstimatorError(
            "paired execution mutated clean stream"
        )

    if pair.corrupt.fingerprint() != corrupt_before:
        raise LidarCorruptionEstimatorError(
            "paired execution mutated corrupt stream"
        )

    truth_ids = [
        truth.injection_id
        for truth
        in pair.truths
    ]

    spec_ids = [
        truth.spec.spec_id
        for truth
        in pair.truths
    ]

    payload: dict[str, Any] = {
        "schema":
            "TRUST_ROBOT_PHASE3_PAIRED_FROZEN_LIDAR_REGISTRATION_V1",

        "clean":
            clean,

        "corrupt":
            corrupt,

        "corruption_spec_ids":
            spec_ids,

        "corruption_injection_ids":
            truth_ids,

        "path_topology": {
            "clean_origin_pairs":
                clean[
                    "origin_pairs"
                ],

            "corrupt_origin_pairs":
                corrupt[
                    "origin_pairs"
                ],

            "registration_path_changed_by_corruption":
                (
                    clean[
                        "origin_pairs"
                    ]
                    != corrupt[
                        "origin_pairs"
                    ]
                ),
        },

        "interpretation": {
            "mechanical_input_path_proof":
                True,

            "clean_corrupt_accuracy_comparison":
                False,

            "clean_corrupt_error_metric":
                None,

            "registration_diagnostic_threshold_selected":
                False,

            "outputs_may_modify_corruption_spec":
                False,
        },

        "scientific_scope": {
            "real_or_synthetic_lidar_registration_execution":
                True,

            "reference_data_used":
                False,

            "confirmation_test_data_used":
                False,

            "ground_truth_association_performed":
                False,

            "alignment_performed":
                False,

            "ate_computed":
                False,

            "rpe_computed":
                False,

            "trajectory_scoring_performed":
                False,

            "estimator_scoring_performed":
                False,

            "accuracy_comparison_performed":
                False,

            "severity_selection_performed":
                False,

            "attack_budget_selection_performed":
                False,
        },
    }

    payload[
        "content_sha256"
    ] = sha256(
        _canonical_json(
            payload
        ).encode(
            "utf-8"
        )
    ).hexdigest()

    return payload
