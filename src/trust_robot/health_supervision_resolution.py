from __future__ import annotations

from hashlib import sha256
from types import MappingProxyType
from typing import Mapping
import json


SE2_HEALTH_SUPERVISION_SCHEMA = (
    "TRUST_ROBOT_SE2_HEALTH_SUPERVISION_PROTOCOL_V1"
)

SE2_HEALTH_SUPERVISION_PROTOCOL_ID = (
    "trust_robot_se2_health_supervision_protocol_v1"
)

HEALTH_STATES = (
    "healthy",
    "degraded",
    "unusable",
)

FROZEN_INPUT_SHA256: Mapping[str, str] = MappingProxyType(
    {
        "se1_freeze_manifest":
            "46224af94a07787883b9bd76e0df88cb43f60e834484add04b64933afdbafb02",

        "software_evidence_completion_plan":
            "5624c4b6e28172859122abec121735314d317d613bded01a0ce18501ea715cdb",

        "health_semantics_module":
            "3499dbe9951db232b04f5b5e90e4e584f8fcd1af1906de3a64769da0972d68a4",

        "health_semantics_config":
            "dc77b600b7306eb146f4ab901e7beca26f1075a6befee5d977a0f0e43070dc22",

        "health_supervision_module":
            "f1ffa072c43998b750804a5ec606570504a27c9f6c60a6aa93b4b8e02bfb1be5",

        "health_supervision_config":
            "08d65e6bca3a87df8d23cb2992bdb84544c66c51df764d3539ceac0fb6a95adc",

        "controlled_availability_module":
            "460c61b15a215a9fca36162aec7644a9f565731716e5f32d727a71d2101a6040",

        "controlled_availability_config":
            "364d2c4d043c5a99e969ea3406d8bb338931705a236b169249b1c06c294f0361",

        "baseline_nominality_module":
            "e8cf8033800973545853fda90c234ada4caffe874be3520ba431f7aef9a86117",

        "baseline_nominality_config":
            "3e54df63f06875c3764c130922d6b967ac94075fc414510240a35e0397b89f00",

        "baseline_raw_capture_module":
            "8c6402afde41e95f98a6e71a9ed557d6edb9bf34adbbce9f6ce00c573440e140",

        "baseline_raw_capture_config":
            "9d71073e3620e1b3447a9bc11952c1a3a909ec7b14fa14cfda075f8d3fdbc5a7",

        "acquisition_session_provenance_module":
            "ff79ccf0ea68355028ef9fd3fa76f431479a9a7f2fba6b60a34d75bd9bf3cf20",

        "acquisition_session_provenance_config":
            "08b691bcc0eb3db7d9b0059608f8134b7b6086f526b6c11e64cf03ac3efa763b",

        "live_acquisition_plan_config":
            "9988bf72a341a045831b2efe49d393f6886075ca179034ceecf4a191b4f8992d",

        "live_executor_safety_config":
            "9370692895bc156552a664b23fd84445a32a3b20ead8c1d1c4f495c31e6dca6a",
    }
)


class SE2HealthSupervisionProtocolError(ValueError):
    """Raised when the frozen SE2 supervision resolution is violated."""


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


def _content_sha256(
    payload: Mapping[str, object],
) -> str:
    value = dict(payload)
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


def build_se2_health_supervision_protocol_manifest(
) -> dict[str, object]:
    """Build the fail-closed SE2 health-supervision resolution.

    SE2 resolves admissibility rules only.

    It does not accept a supervision source, assign health labels, train a
    classifier, select features or thresholds, calibrate probabilities,
    access validation/confirmation, read reference trajectories, or score
    localization.

    The current repository has no empirical baseline/intervention receipts
    satisfying the frozen protocol, so health-model training remains blocked.
    """

    payload: dict[str, object] = {
        "schema":
            SE2_HEALTH_SUPERVISION_SCHEMA,

        "schema_version":
            1,

        "protocol_id":
            SE2_HEALTH_SUPERVISION_PROTOCOL_ID,

        "stage": {
            "stage_id":
                "SE2",

            "stage_name":
                "health_supervision_protocol",

            "track":
                "software_evidence_completion",

            "status":
                "protocol_resolved_no_accepted_empirical_source_ready_for_SE3",

            "purpose":
                (
                    "Resolve admissible healthy/degraded/unusable "
                    "supervision without converting availability, clean or "
                    "corruption identity, diagnostic values, reference "
                    "metrics, or final localization error into health labels."
                ),
        },

        "state_vocabulary": [
            *HEALTH_STATES
        ],

        "state_semantics": {
            "healthy":
                (
                    "Nominal for the declared measurement role during the "
                    "labeled interval according to an accepted, prospective, "
                    "measurement-role-grounded supervision source."
                ),

            "degraded":
                (
                    "Non-nominal impairment of the declared measurement "
                    "role while the role remains usable during the labeled "
                    "interval according to an accepted supervision source."
                ),

            "unusable":
                (
                    "Unable to provide measurement information suitable for "
                    "the declared measurement role during the labeled "
                    "interval according to an accepted supervision source."
                ),
        },

        "admissible_supervision": {
            "prospective_declaration_required":
                True,

            "measurement_role_grounding_required":
                True,

            "explicit_source_identity_required":
                True,

            "explicit_interval_provenance_required":
                True,

            "explicit_state_criteria_required":
                True,

            "independent_baseline_nominality_required":
                True,

            "independent_intervention_or_state_evidence_required":
                True,

            "independent_measurement_relation_verification_required":
                True,

            "independent_of_diagnostic_features_required":
                True,

            "independent_of_reference_trajectory_required":
                True,

            "independent_of_final_estimator_scoring_required":
                True,

            "independent_of_confirmation_test_required":
                True,

            "current_concrete_candidate_class":
                "controlled_measurement_availability",

            "current_concrete_candidate_modality":
                "lidar",

            "current_concrete_candidate_protocol_is_prospective_only":
                True,

            "candidate_shape_validity_implies_source_acceptance":
                False,
        },

        "controlled_availability_mapping": {
            "full":
                "healthy",

            "partial":
                "degraded",

            "absent":
                "unusable",

            "mapping_applies_only_after_source_acceptance":
                True,

            "availability_identity_alone_is_health_label":
                False,

            "missing_measurement_encoded_as_zero_feature_vector":
                False,
        },

        "prohibited_label_basis": {
            "clean_dataset_identity_alone":
                True,

            "synthetic_corruption_identity_alone":
                True,

            "measurement_availability_identity_alone":
                True,

            "diagnostic_value_or_threshold_alone":
                True,

            "reference_trajectory_metric":
                True,

            "ate_or_rpe":
                True,

            "final_localization_error":
                True,

            "final_estimator_score":
                True,

            "confirmation_test_outcome":
                True,

            "classifier_output_as_own_supervision":
                True,

            "historical_imu_reliability_policy":
                True,
        },

        "current_empirical_readiness": {
            "accepted_baseline_nominality_source_count":
                0,

            "accepted_health_supervision_source_count":
                0,

            "real_health_label_count":
                0,

            "training_label_source_selected":
                False,

            "baseline_nominality_receipt_available":
                False,

            "controlled_intervention_receipt_available":
                False,

            "measurement_relation_verification_receipt_available":
                False,

            "live_sensor_execution_authorized":
                False,

            "live_sensor_execution_performed":
                False,

            "health_label_generation_authorized":
                False,

            "empirical_health_supervision_available":
                False,
        },

        "partition_access": {
            "train_authorized":
                True,

            "validation_authorized":
                False,

            "confirmation_authorized":
                False,

            "reference_trajectory_authorized":
                False,

            "cross_partition_supervision_allowed":
                False,
        },

        "execution_boundary": {
            "health_label_assignment_executed":
                False,

            "feature_selection_executed":
                False,

            "model_training_executed":
                False,

            "probability_calibration_executed":
                False,

            "threshold_selection_executed":
                False,

            "reference_association_executed":
                False,

            "ate_rpe_computed":
                False,

            "final_scoring_executed":
                False,
        },

        "transition_policy": {
            "SE2_protocol_definition_resolved":
                True,

            "SE3_may_proceed":
                True,

            "SE3_scope":
                "multimodal_feature_pipeline",

            "SE3_train_access_only":
                True,

            "SE4_health_model_training_may_proceed":
                False,

            "SE4_blocker":
                (
                    "No accepted empirical TRAIN health-supervision source "
                    "and no real health labels are currently available."
                ),

            "SE4_requires_admissible_train_supervision":
                True,

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
    }

    payload[
        "content_sha256"
    ] = _content_sha256(
        payload
    )

    return payload


def validate_se2_health_supervision_protocol_manifest(
    payload: Mapping[str, object],
) -> Mapping[str, object]:
    """Fail closed if the SE2 scientific resolution has been changed."""

    if not isinstance(
        payload,
        Mapping,
    ):
        raise SE2HealthSupervisionProtocolError(
            "payload must be a mapping"
        )

    expected = build_se2_health_supervision_protocol_manifest()

    if dict(payload) != expected:
        raise SE2HealthSupervisionProtocolError(
            "SE2 health-supervision protocol differs from the frozen "
            "resolution"
        )

    if payload.get(
        "content_sha256"
    ) != _content_sha256(
        payload
    ):
        raise SE2HealthSupervisionProtocolError(
            "content_sha256 mismatch"
        )

    return payload


def assert_se3_entry_authorized(
    payload: Mapping[str, object],
) -> None:
    """Authorize only the next TRAIN-only feature-pipeline stage."""

    validate_se2_health_supervision_protocol_manifest(
        payload
    )

    transition = payload[
        "transition_policy"
    ]

    if transition[
        "SE3_may_proceed"
    ] is not True:
        raise SE2HealthSupervisionProtocolError(
            "SE3 entry is not authorized"
        )

    if transition[
        "SE3_train_access_only"
    ] is not True:
        raise SE2HealthSupervisionProtocolError(
            "SE3 must remain TRAIN-only"
        )


def assert_health_model_training_authorized(
    payload: Mapping[str, object],
) -> None:
    """Fail closed: SE4 training is not authorized at the SE2 frontier."""

    validate_se2_health_supervision_protocol_manifest(
        payload
    )

    transition = payload[
        "transition_policy"
    ]

    readiness = payload[
        "current_empirical_readiness"
    ]

    if (
        transition[
            "SE4_health_model_training_may_proceed"
        ] is not True
        or readiness[
            "accepted_health_supervision_source_count"
        ] <= 0
        or readiness[
            "real_health_label_count"
        ] <= 0
    ):
        raise SE2HealthSupervisionProtocolError(
            "health-model training is blocked: admissible empirical TRAIN "
            "health supervision has not been accepted"
        )
