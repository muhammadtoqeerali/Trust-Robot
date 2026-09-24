"""TRUST-ROBOT Phase-6 probabilistic health-output calibration contract.

Phase 6 concerns probabilistic calibration of the modality-health model.

It is deliberately distinct from:
- camera/LiDAR/IMU geometric calibration;
- extrinsic or intrinsic calibration;
- temporal synchronization;
- health-threshold selection;
- suppression/recovery/fallback operating points.

The project proposal names temperature scaling as the current calibration
mechanism and reserves calibration selection for validation/calibration data.

No empirical calibration can execute in the current repository state because
Phase-5 has no trained health model, admissible health labels, or uncalibrated
health-model outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


SCHEMA = (
    "TRUST_ROBOT_PHASE6_PROBABILISTIC_CALIBRATION_CONTRACT_V1"
)


class ProbabilisticCalibrationError(ValueError):
    """Raised when the Phase-6 calibration contract is violated."""


class CalibrationKind(str, Enum):
    MODALITY_HEALTH_PROBABILITY = (
        "modality_health_probability"
    )


class CalibrationMechanism(str, Enum):
    TEMPERATURE_SCALING = (
        "temperature_scaling"
    )


class CalibrationLifecycle(str, Enum):
    CONTRACT_IMPLEMENTED_INPUTS_UNAVAILABLE = (
        "contract_implemented_inputs_unavailable"
    )


@dataclass(frozen=True)
class CurrentCalibrationEvidenceGate:
    phase5_empirical_health_model_complete: bool = False
    trained_health_model_available: bool = False
    uncalibrated_health_model_outputs_available: bool = False
    admissible_health_labels_available: bool = False

    validation_calibration_inputs_available: bool = False

    calibration_objective_selected: bool = False
    temperature_scope_selected: bool = False
    temperature_parameter_selected: bool = False

    calibration_execution_authorized: bool = False
    calibrated_output_authorized: bool = False

    confirmation_closed: bool = True
    confirmation_selection_authorized: bool = False

    def __post_init__(self) -> None:
        false_fields = (
            "phase5_empirical_health_model_complete",
            "trained_health_model_available",
            "uncalibrated_health_model_outputs_available",
            "admissible_health_labels_available",
            "validation_calibration_inputs_available",
            "calibration_objective_selected",
            "temperature_scope_selected",
            "temperature_parameter_selected",
            "calibration_execution_authorized",
            "calibrated_output_authorized",
            "confirmation_selection_authorized",
        )

        for field_name in false_fields:
            if getattr(
                self,
                field_name,
            ) is not False:
                raise ProbabilisticCalibrationError(
                    f"{field_name} must remain false in the current "
                    "Phase-6 evidence state"
                )

        if self.confirmation_closed is not True:
            raise ProbabilisticCalibrationError(
                "confirmation-test partition must remain closed"
            )


CURRENT_CALIBRATION_GATE = (
    CurrentCalibrationEvidenceGate()
)


def assert_calibration_execution_authorized(
    gate: CurrentCalibrationEvidenceGate = (
        CURRENT_CALIBRATION_GATE
    ),
) -> None:
    if gate.calibration_execution_authorized is not True:
        raise ProbabilisticCalibrationError(
            "probabilistic calibration execution is not authorized: "
            "trained health-model outputs and admissible validation "
            "supervision are unavailable"
        )


def assert_calibrated_output_authorized(
    gate: CurrentCalibrationEvidenceGate = (
        CURRENT_CALIBRATION_GATE
    ),
) -> None:
    if gate.calibrated_output_authorized is not True:
        raise ProbabilisticCalibrationError(
            "calibrated health-probability output is not authorized"
        )


def build_contract_manifest(
    *,
    phase5_freeze_sha256: str,
    phase5_health_model_config_sha256: str,
    evaluation_protocol_sha256: str,
    prospective_split_sha256: str,
    frontier_report_sha256: str,
    frontier_json_sha256: str,
    master_context_sha256: str,
    phase_plan_sha256: str,
) -> dict[str, Any]:
    gate = CURRENT_CALIBRATION_GATE

    return {
        "schema":
            SCHEMA,

        "lifecycle_status":
            CalibrationLifecycle
            .CONTRACT_IMPLEMENTED_INPUTS_UNAVAILABLE
            .value,

        "calibration_scope": {
            "kind":
                CalibrationKind
                .MODALITY_HEALTH_PROBABILITY
                .value,

            "probabilistic_health_output_calibration":
                True,

            "sensor_geometry_calibration":
                False,

            "camera_intrinsic_calibration_modified":
                False,

            "sensor_extrinsic_calibration_modified":
                False,

            "temporal_synchronization_modified":
                False,

            "reference_frame_alignment_modified":
                False,
        },

        "proposal_mechanism_contract": {
            "mechanism":
                CalibrationMechanism
                .TEMPERATURE_SCALING
                .value,

            "mechanism_source":
                "TRUST_ROBOT project proposal/master context",

            "proposal_mechanism_declared":
                True,

            "mechanism_selected_from_validation_outcomes":
                False,

            "candidate_method_comparison_performed":
                False,

            "historical_imu_reliability_calibrator_adopted":
                False,

            "historical_ood_calibrator_adopted":
                False,

            "input_representation":
                "unselected",

            "optimization_objective":
                "unselected",

            "calibration_quality_metrics":
                [],

            "temperature_scope":
                "unselected",

            "temperature_parameter":
                None,

            "temperature_parameter_selected":
                False,

            "parameter_fit_performed":
                False,
        },

        "selection_partition": {
            "partition":
                "validation_calibration",

            "trajectory_count":
                7,

            "partition_frozen":
                True,

            "validation_only_selection_required":
                True,

            "bags_open_authorized_in_current_state":
                False,

            "calibration_execution_authorized":
                False,

            "selection_requires_trained_health_model":
                True,

            "selection_requires_admissible_health_labels":
                True,

            "selection_requires_uncalibrated_health_model_outputs":
                True,

            "physical_fact_cannot_be_created_by_validation_selection":
                True,
        },

        "confirmation_boundary": {
            "partition":
                "confirmation_test",

            "trajectory_count":
                7,

            "closed":
                gate.confirmation_closed,

            "may_select_calibration_mechanism":
                False,

            "may_select_calibration_objective":
                False,

            "may_select_temperature_scope":
                False,

            "may_select_temperature_parameter":
                False,

            "may_select_health_threshold":
                False,

            "selection_authorized":
                gate.confirmation_selection_authorized,
        },

        "current_evidence_gate": {
            "phase5_empirical_health_model_complete":
                gate.phase5_empirical_health_model_complete,

            "trained_health_model_available":
                gate.trained_health_model_available,

            "uncalibrated_health_model_outputs_available":
                gate.uncalibrated_health_model_outputs_available,

            "admissible_health_labels_available":
                gate.admissible_health_labels_available,

            "validation_calibration_inputs_available":
                gate.validation_calibration_inputs_available,

            "calibration_objective_selected":
                gate.calibration_objective_selected,

            "temperature_scope_selected":
                gate.temperature_scope_selected,

            "temperature_parameter_selected":
                gate.temperature_parameter_selected,

            "calibration_execution_authorized":
                gate.calibration_execution_authorized,

            "calibrated_output_authorized":
                gate.calibrated_output_authorized,
        },

        "runtime_output": {
            "uncalibrated_health_probability_input_available":
                False,

            "calibrated_health_probability_output":
                "disabled",

            "calibration_artifact_sha256":
                None,

            "calibration_receipt_sha256":
                None,
        },

        "operating_point_separation": {
            "health_threshold":
                None,

            "health_threshold_selected":
                False,

            "suppression_threshold_selected":
                False,

            "recovery_threshold_selected":
                False,

            "fallback_safety_threshold_selected":
                False,

            "threshold_selection_is_not_temperature_calibration":
                True,
        },

        "scientific_boundary": {
            "health_labels_created_by_calibration":
                False,

            "final_localization_error_used_for_calibration":
                False,

            "reference_data_used":
                False,

            "physical_measurement_time_selected":
                False,

            "cross_modal_synchronization_selected":
                False,

            "ate_rpe_computation_authorized":
                False,

            "final_scoring_authorized":
                False,

            "confirmation_data_used":
                False,
        },

        "source_bindings": {
            "phase5_freeze_sha256":
                phase5_freeze_sha256,

            "phase5_health_model_config_sha256":
                phase5_health_model_config_sha256,

            "evaluation_protocol_sha256":
                evaluation_protocol_sha256,

            "prospective_split_sha256":
                prospective_split_sha256,

            "phase6_frontier_report_sha256":
                frontier_report_sha256,

            "phase6_frontier_json_sha256":
                frontier_json_sha256,

            "master_context_sha256":
                master_context_sha256,

            "phase_plan_sha256":
                phase_plan_sha256,
        },
    }


def validate_contract_manifest(
    payload: Mapping[str, Any],
) -> None:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise ProbabilisticCalibrationError(
            "calibration contract must be a mapping"
        )

    if payload.get(
        "schema"
    ) != SCHEMA:
        raise ProbabilisticCalibrationError(
            "unexpected Phase-6 calibration schema"
        )

    if payload[
        "lifecycle_status"
    ] != (
        CalibrationLifecycle
        .CONTRACT_IMPLEMENTED_INPUTS_UNAVAILABLE
        .value
    ):
        raise ProbabilisticCalibrationError(
            "unexpected calibration lifecycle"
        )

    scope = payload[
        "calibration_scope"
    ]

    if scope != {
        "kind": "modality_health_probability",
        "probabilistic_health_output_calibration": True,
        "sensor_geometry_calibration": False,
        "camera_intrinsic_calibration_modified": False,
        "sensor_extrinsic_calibration_modified": False,
        "temporal_synchronization_modified": False,
        "reference_frame_alignment_modified": False,
    }:
        raise ProbabilisticCalibrationError(
            "probabilistic/sensor calibration scope separation changed"
        )

    mechanism = payload[
        "proposal_mechanism_contract"
    ]

    if mechanism[
        "mechanism"
    ] != "temperature_scaling":
        raise ProbabilisticCalibrationError(
            "project proposal calibration mechanism changed"
        )

    if mechanism[
        "proposal_mechanism_declared"
    ] is not True:
        raise ProbabilisticCalibrationError(
            "proposal calibration mechanism must remain explicit"
        )

    false_mechanism_keys = (
        "mechanism_selected_from_validation_outcomes",
        "candidate_method_comparison_performed",
        "historical_imu_reliability_calibrator_adopted",
        "historical_ood_calibrator_adopted",
        "temperature_parameter_selected",
        "parameter_fit_performed",
    )

    for key in false_mechanism_keys:
        if mechanism[
            key
        ] is not False:
            raise ProbabilisticCalibrationError(
                f"{key} must remain false"
            )

    if mechanism[
        "input_representation"
    ] != "unselected":
        raise ProbabilisticCalibrationError(
            "calibration input representation is not yet selected"
        )

    if mechanism[
        "optimization_objective"
    ] != "unselected":
        raise ProbabilisticCalibrationError(
            "calibration objective is not yet selected"
        )

    if mechanism[
        "calibration_quality_metrics"
    ] != []:
        raise ProbabilisticCalibrationError(
            "calibration quality metrics were selected unexpectedly"
        )

    if mechanism[
        "temperature_scope"
    ] != "unselected":
        raise ProbabilisticCalibrationError(
            "temperature scope is not yet selected"
        )

    if mechanism[
        "temperature_parameter"
    ] is not None:
        raise ProbabilisticCalibrationError(
            "temperature parameter must remain unset"
        )

    selection = payload[
        "selection_partition"
    ]

    expected_selection = {
        "partition": "validation_calibration",
        "trajectory_count": 7,
        "partition_frozen": True,
        "validation_only_selection_required": True,
        "bags_open_authorized_in_current_state": False,
        "calibration_execution_authorized": False,
        "selection_requires_trained_health_model": True,
        "selection_requires_admissible_health_labels": True,
        "selection_requires_uncalibrated_health_model_outputs": True,
        "physical_fact_cannot_be_created_by_validation_selection": True,
    }

    if selection != expected_selection:
        raise ProbabilisticCalibrationError(
            "validation-only calibration boundary changed"
        )

    confirmation = payload[
        "confirmation_boundary"
    ]

    expected_confirmation = {
        "partition": "confirmation_test",
        "trajectory_count": 7,
        "closed": True,
        "may_select_calibration_mechanism": False,
        "may_select_calibration_objective": False,
        "may_select_temperature_scope": False,
        "may_select_temperature_parameter": False,
        "may_select_health_threshold": False,
        "selection_authorized": False,
    }

    if confirmation != expected_confirmation:
        raise ProbabilisticCalibrationError(
            "confirmation-test calibration boundary changed"
        )

    gate = payload[
        "current_evidence_gate"
    ]

    if set(
        gate.values()
    ) != {
        False,
    }:
        raise ProbabilisticCalibrationError(
            "all current empirical calibration gates must remain false"
        )

    runtime = payload[
        "runtime_output"
    ]

    if runtime != {
        "uncalibrated_health_probability_input_available": False,
        "calibrated_health_probability_output": "disabled",
        "calibration_artifact_sha256": None,
        "calibration_receipt_sha256": None,
    }:
        raise ProbabilisticCalibrationError(
            "calibrated runtime output must remain disabled"
        )

    operating = payload[
        "operating_point_separation"
    ]

    if operating != {
        "health_threshold": None,
        "health_threshold_selected": False,
        "suppression_threshold_selected": False,
        "recovery_threshold_selected": False,
        "fallback_safety_threshold_selected": False,
        "threshold_selection_is_not_temperature_calibration": True,
    }:
        raise ProbabilisticCalibrationError(
            "calibration/operating-point separation changed"
        )

    scientific = payload[
        "scientific_boundary"
    ]

    for key, value in scientific.items():
        if value is not False:
            raise ProbabilisticCalibrationError(
                f"scientific boundary {key} must remain false"
            )
