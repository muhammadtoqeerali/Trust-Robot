"""TRUST-ROBOT SE4 health-model training resolution.

SE4 is the stage at which an actual modality-health model would be trained.

At the current frozen frontier, training is not scientifically authorized
because no admissible empirical TRAIN health-supervision source and no real
healthy/degraded/unusable labels have been accepted.

This module therefore resolves the current SE4 state fail closed.

It binds the exact SE3 diagnostic input contracts prospectively, while:
- preserving the historical frozen Phase-5 interface unchanged;
- selecting no classifier architecture;
- fitting no model;
- emitting no health state or probability;
- performing no calibration or threshold selection;
- opening neither validation nor confirmation;
- using no reference trajectory or final localization score as supervision.

SE4 remains incomplete until admissible empirical TRAIN supervision exists.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Mapping
import json


SCHEMA = (
    "TRUST_ROBOT_SE4_HEALTH_MODEL_TRAINING_RESOLUTION_V1"
)

SCHEMA_VERSION = 1

RESOLUTION_ID = (
    "trust_robot_se4_health_model_training_resolution_v1"
)

HEALTH_STATES = (
    "healthy",
    "degraded",
    "unusable",
)

CAMERA_FEATURES = (
    "gray_mean_intensity_8bit",
    "gray_std_intensity_8bit",
    "gray_mean_abs_neighbor_difference_8bit",
)

IMU_FEATURES = (
    "angular_speed_norm_rad_s",
    "linear_acceleration_norm_m_s2",
)

LIDAR_FEATURES = (
    "source_point_count",
    "target_point_count",
    "fixed_point_iterations",
    "final_correspondence_count",
    "final_nearest_neighbor_rmse_m",
)

FROZEN_INPUT_SHA256 = {
    "SE2_health_supervision_freeze":
        "63da52c788208ae715abc7e0b8eb0ba6777cc16d33d90466332779c630618230",

    "SE3_multimodal_feature_pipeline_freeze":
        "a987f9793b60ea674991577a189711f2e535961796b1d74dfd6454e60de8e994",

    "phase5_multimodal_health_model_interface":
        "aa48c67cdcd19aa5af2a297f42b20d1bb4369b5dcd38bdc2c2ca9ae68ceb4ea3",

    "phase5_multimodal_software_architecture_freeze":
        "457a42c3778731307b1371208407fca6d7cf8e604718f81138034479deb0d09a",

    "software_evidence_completion_plan":
        "5624c4b6e28172859122abec121735314d317d613bded01a0ce18501ea715cdb",
}

SE3_FREEZE_CONTENT_SHA256 = (
    "ce68cfa263e31b20060d92af48b4eba6f82cc5b706bc7f3108c3ac2c6448bb90"
)


class SE4HealthModelTrainingResolutionError(ValueError):
    """Raised when the fail-closed SE4 resolution is violated."""


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


def content_sha256(
    payload: Mapping[str, object],
) -> str:
    value = dict(
        payload
    )

    value.pop(
        "content_sha256",
        None,
    )

    return sha256(
        _canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def build_se4_health_model_training_resolution(
) -> dict[str, object]:
    """Build the current fail-closed SE4 training resolution."""

    payload: dict[str, object] = {
        "schema":
            SCHEMA,

        "schema_version":
            SCHEMA_VERSION,

        "resolution_id":
            RESOLUTION_ID,

        "stage": {
            "stage_id":
                "SE4",

            "stage_name":
                "health_model_training",

            "track":
                "software_evidence_completion",

            "purpose":
                (
                    "Train the actual modality-health model using admissible "
                    "TRAIN evidence and leakage-safe trajectory grouping."
                ),

            "current_resolution":
                "blocked_no_admissible_train_supervision",

            "SE4_complete":
                False,
        },

        "health_states": [
            *HEALTH_STATES
        ],

        "frozen_diagnostic_inputs": {
            "camera": {
                "contract_source":
                    "SE3_multimodal_feature_pipeline_freeze",

                "feature_names": [
                    *CAMERA_FEATURES
                ],

                "feature_contract_resolved":
                    True,

                "stream":
                    "/camera/color/image_raw/compressed",

                "health_semantics":
                    False,
            },

            "imu": {
                "contract_source":
                    "SE3_multimodal_feature_pipeline_freeze",

                "feature_names": [
                    *IMU_FEATURES
                ],

                "feature_contract_resolved":
                    True,

                "source_streams": [
                    "/camera/imu",
                    "/handsfree/imu",
                ],

                "streams_kept_separate":
                    True,

                "health_semantics":
                    False,
            },

            "lidar": {
                "contract_source":
                    "Phase4_validated_diagnostic_feature_extraction_freeze",

                "feature_names": [
                    *LIDAR_FEATURES
                ],

                "feature_contract_resolved":
                    True,

                "phase4_contract_reopened":
                    False,

                "stream":
                    "/velodyne_points",

                "health_semantics":
                    False,
            },

            "gnss": {
                "role":
                    "optional",

                "feature_contract_resolved":
                    False,

                "feature_names":
                    [],
            },
        },

        "historical_phase5_interface": {
            "interface_is_hash_frozen":
                True,

            "interface_predates_SE3_exact_camera_IMU_resolution":
                True,

            "historical_camera_feature_names":
                [],

            "historical_IMU_feature_names":
                [],

            "historical_camera_feature_contract_selected":
                False,

            "historical_IMU_feature_contract_selected":
                False,

            "historical_artifact_rewritten":
                False,

            "SE4_uses_SE3_freeze_as_authoritative_exact_feature_binding":
                True,
        },

        "supervision_gate": {
            "accepted_baseline_nominality_source_count":
                0,

            "accepted_health_supervision_source_count":
                0,

            "real_health_label_count":
                0,

            "training_label_source_selected":
                False,

            "empirical_health_supervision_available":
                False,

            "health_label_generation_authorized":
                False,

            "classifier_training_authorized":
                False,

            "health_inference_authorized":
                False,

            "blocker":
                (
                    "No accepted empirical TRAIN health-supervision source "
                    "and no real healthy/degraded/unusable labels are "
                    "available under the frozen SE2 admissibility protocol."
                ),
        },

        "future_training_requirements": {
            "admissible_TRAIN_supervision_required":
                True,

            "real_health_labels_required":
                True,

            "trajectory_grouping_required":
                True,

            "derivative_lineage_grouping_required":
                True,

            "cross_partition_training_forbidden":
                True,

            "confirmation_for_model_selection_forbidden":
                True,

            "final_localization_error_as_health_label_forbidden":
                True,

            "diagnostic_feature_value_as_health_label_forbidden":
                True,

            "classifier_output_as_own_supervision_forbidden":
                True,
        },

        "model_state": {
            "classifier_architecture":
                "unselected",

            "classifier_architecture_selected":
                False,

            "model_family_selection_executed":
                False,

            "hyperparameter_selection_executed":
                False,

            "model_training_executed":
                False,

            "trained_model_artifact_sha256":
                None,

            "health_probability_output_enabled":
                False,

            "health_state_output_enabled":
                False,
        },

        "partition_access": {
            "train_access":
                True,

            "validation_access":
                False,

            "confirmation_access":
                False,

            "reference_trajectory_access":
                False,
        },

        "execution_boundary": {
            "SE3_feature_contracts_reopened":
                False,

            "supervised_feature_selection_executed":
                False,

            "health_label_assignment_executed":
                False,

            "model_training_executed":
                False,

            "probability_calibration_executed":
                False,

            "health_threshold_selection_executed":
                False,

            "reference_association_executed":
                False,

            "ate_rpe_computed":
                False,

            "final_scoring_executed":
                False,
        },

        "transition_policy": {
            "SE4_training_may_execute":
                False,

            "SE4_complete":
                False,

            "SE5_may_proceed":
                False,

            "SE5_blocker":
                (
                    "SE4 has no trained health-model artifact because "
                    "admissible empirical TRAIN supervision is unavailable."
                ),

            "validation_remains_closed":
                True,

            "confirmation_remains_closed":
                True,

            "SE9_remains_closed":
                True,
        },

        "frozen_input_sha256":
            dict(
                FROZEN_INPUT_SHA256
            ),

        "SE3_freeze_content_sha256":
            SE3_FREEZE_CONTENT_SHA256,
    }

    payload[
        "content_sha256"
    ] = content_sha256(
        payload
    )

    return payload


def validate_se4_health_model_training_resolution(
    payload: Mapping[str, object],
) -> Mapping[str, object]:
    """Accept only the exact current fail-closed SE4 resolution."""

    if not isinstance(
        payload,
        Mapping,
    ):
        raise SE4HealthModelTrainingResolutionError(
            "payload must be a mapping"
        )

    expected = (
        build_se4_health_model_training_resolution()
    )

    if dict(
        payload
    ) != expected:
        raise SE4HealthModelTrainingResolutionError(
            "SE4 health-model training resolution differs from the "
            "frozen fail-closed state"
        )

    if payload.get(
        "content_sha256"
    ) != content_sha256(
        payload
    ):
        raise SE4HealthModelTrainingResolutionError(
            "content_sha256 mismatch"
        )

    return payload


def assert_training_execution_authorized(
    payload: Mapping[str, object],
) -> None:
    """Fail closed while admissible empirical TRAIN supervision is absent."""

    validate_se4_health_model_training_resolution(
        payload
    )

    gate = payload[
        "supervision_gate"
    ]

    transition = payload[
        "transition_policy"
    ]

    if (
        transition[
            "SE4_training_may_execute"
        ] is not True
        or gate[
            "classifier_training_authorized"
        ] is not True
        or gate[
            "accepted_health_supervision_source_count"
        ] <= 0
        or gate[
            "real_health_label_count"
        ] <= 0
    ):
        raise SE4HealthModelTrainingResolutionError(
            "SE4 model training remains blocked: admissible empirical TRAIN "
            "health supervision and real health labels are unavailable"
        )


def assert_se5_entry_authorized(
    payload: Mapping[str, object],
) -> None:
    """Fail closed: SE5 cannot open before a legitimate SE4 model exists."""

    validate_se4_health_model_training_resolution(
        payload
    )

    if payload[
        "transition_policy"
    ][
        "SE5_may_proceed"
    ] is not True:
        raise SE4HealthModelTrainingResolutionError(
            "SE5 validation/calibration remains blocked because SE4 has no "
            "authorized trained health-model artifact"
        )
