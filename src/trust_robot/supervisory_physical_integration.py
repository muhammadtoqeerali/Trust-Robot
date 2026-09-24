"""TRUST-ROBOT Phase-14 supervisory / physical-integration contract.

Authoritative architecture:

- the learned health model is not the robot controller;
- safety response is a separate rule-based supervisory layer;
- possible supervisor evidence includes calibrated modality-health
  probabilities, estimator covariance/status, tracking availability,
  residual consistency, solver validity, and frozen validation-selected
  thresholds;
- planned comparison identities are nominal continuation, always-stop,
  health-triggered policy, and oracle-health policy;
- physical experiments must remain guarded and progressively validated.

This module deliberately does not define robot commands, a controller API,
safe-stop semantics, emergency behavior, speed limits, stopping distances,
physical safety metrics, fallback thresholds, physical-test operating points,
or target-specific robot behavior.

Those quantities require prospective evidence and protocol binding before
physical execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


SCHEMA = (
    "TRUST_ROBOT_PHASE14_SUPERVISORY_PHYSICAL_INTEGRATION_CONTRACT_V1"
)

SUPERVISOR_INPUT_IDENTITIES = (
    "calibrated modality-health probabilities",
    "estimator covariance/status",
    "tracking availability",
    "residual consistency",
    "solver validity",
    "frozen validation-selected thresholds",
)

POLICY_COMPARISON_IDENTITIES = (
    "nominal continuation",
    "always-stop",
    "health-triggered policy",
    "oracle-health policy",
)

EVENTUAL_PHYSICAL_PLATFORM_ROLE = (
    "local_quadruped_robot"
)


class SupervisoryPhysicalIntegrationContractError(ValueError):
    """Raised when Phase-14 evidence boundaries are violated."""


class Phase14Lifecycle(str, Enum):
    CONTRACT_IMPLEMENTED_ROBOT_SEMANTICS_UNSELECTED = (
        "contract_implemented_robot_semantics_unselected"
    )


@dataclass(frozen=True)
class CurrentPhase14Gate:
    supervisor_input_availability_verified: bool = False

    policy_comparison_execution_selected: bool = False
    operational_policy_selected: bool = False

    controller_interface_selected: bool = False
    robot_action_mapping_selected: bool = False

    fallback_threshold_selected: bool = False
    safety_threshold_selected: bool = False

    physical_test_protocol_selected: bool = False
    physical_test_partition_instantiated: bool = False

    physical_platform_identity_frozen: bool = False
    physical_reference_instrumentation_frozen: bool = False

    robot_integration_execution_authorized: bool = False
    physical_test_execution_authorized: bool = False

    closed_loop_safety_measurement_authorized: bool = False
    closed_loop_safety_claim_authorized: bool = False

    rq4_closed_loop_safety_answer_available: bool = False
    full_rq4_answer_available: bool = False

    phase9_runtime_suppression_recovery_assumed: bool = False
    phase13_resource_measurement_results_assumed: bool = False
    phase13_onboard_resource_constraints_assumed: bool = False

    validation_data_opened: bool = False
    confirmation_data_used: bool = False

    final_confirmation_execution_authorized: bool = False

    def __post_init__(self) -> None:
        for field_name in self.__dataclass_fields__:
            if getattr(
                self,
                field_name,
            ) is not False:
                raise SupervisoryPhysicalIntegrationContractError(
                    f"{field_name} must remain false in the current "
                    "Phase-14 evidence state"
                )


CURRENT_PHASE14_GATE = CurrentPhase14Gate()


def supervisor_input_identities() -> tuple[str, ...]:
    return SUPERVISOR_INPUT_IDENTITIES


def planned_policy_comparison_identities() -> tuple[str, ...]:
    return POLICY_COMPARISON_IDENTITIES


def assert_robot_integration_execution_authorized(
    gate: CurrentPhase14Gate = CURRENT_PHASE14_GATE,
) -> None:
    if gate.robot_integration_execution_authorized is not True:
        raise SupervisoryPhysicalIntegrationContractError(
            "robot integration execution is not authorized"
        )


def assert_physical_test_execution_authorized(
    gate: CurrentPhase14Gate = CURRENT_PHASE14_GATE,
) -> None:
    if gate.physical_test_execution_authorized is not True:
        raise SupervisoryPhysicalIntegrationContractError(
            "physical test execution is not authorized"
        )


def assert_closed_loop_safety_measurement_authorized(
    gate: CurrentPhase14Gate = CURRENT_PHASE14_GATE,
) -> None:
    if gate.closed_loop_safety_measurement_authorized is not True:
        raise SupervisoryPhysicalIntegrationContractError(
            "closed-loop safety measurement is not authorized"
        )


def assert_closed_loop_safety_claim_authorized(
    gate: CurrentPhase14Gate = CURRENT_PHASE14_GATE,
) -> None:
    if gate.closed_loop_safety_claim_authorized is not True:
        raise SupervisoryPhysicalIntegrationContractError(
            "closed-loop safety claim is not authorized"
        )


def build_contract_manifest(
    *,
    phase13_freeze_sha256: str,
    phase13_contract_sha256: str,
    phase9_freeze_sha256: str,
    phase9_contract_sha256: str,
    master_context_sha256: str,
    phase_plan_sha256: str,
    data_protocol_sha256: str,
    dataset_registry_sha256: str,
    runtime_integration_sha256: str,
    live_executor_config_sha256: str,
    live_executor_module_sha256: str,
    frontier_report_sha256: str,
    frontier_json_sha256: str,
    basis_report_sha256: str,
    basis_json_sha256: str,
) -> dict[str, Any]:
    gate = CURRENT_PHASE14_GATE

    return {
        "schema":
            SCHEMA,

        "lifecycle_status":
            Phase14Lifecycle
            .CONTRACT_IMPLEMENTED_ROBOT_SEMANTICS_UNSELECTED
            .value,

        "phase_scope": {
            "phase":
                14,

            "name":
                "guarded_real_robot_integration_and_supervisory_testing",

            "evidence_role":
                "supervisory_and_closed_loop_evidence",
        },

        "supervisor_architecture": {
            "learned_health_model_is_robot_controller":
                False,

            "separate_rule_based_supervisory_layer_required":
                True,

            "physical_experiments_must_remain_guarded":
                True,

            "physical_experiments_must_be_progressively_validated":
                True,

            "controller_interface_selected":
                gate.controller_interface_selected,

            "robot_action_mapping_selected":
                gate.robot_action_mapping_selected,

            "supervisor_state_machine_selected":
                False,

            "supervisor_update_rate_selected":
                False,
        },

        "supervisor_input_schema": {
            "candidate_inputs":
                list(
                    supervisor_input_identities()
                ),

            "candidate_input_count":
                len(
                    SUPERVISOR_INPUT_IDENTITIES
                ),

            "candidate_input_identity_implies_runtime_readiness":
                False,

            "all_candidate_inputs_runtime_verified":
                gate.supervisor_input_availability_verified,

            "candidate_inputs_are_robot_commands":
                False,
        },

        "planned_policy_comparisons": {
            "identities":
                list(
                    planned_policy_comparison_identities()
                ),

            "identity_count":
                len(
                    POLICY_COMPARISON_IDENTITIES
                ),

            "identities_are_selected_operational_policy":
                False,

            "identities_define_robot_command_semantics":
                False,

            "nominal_continuation_action_semantics_selected":
                False,

            "always_stop_action_semantics_selected":
                False,

            "health_triggered_operational_rule_selected":
                False,

            "oracle_health_is_runtime_available_signal":
                False,

            "oracle_health_role_is_planned_comparison_only":
                True,

            "policy_comparison_execution_selected":
                gate.policy_comparison_execution_selected,

            "operational_policy_selected":
                gate.operational_policy_selected,
        },

        "robot_action_semantics_boundary": {
            "controller_interface":
                None,

            "controller_interface_selected":
                gate.controller_interface_selected,

            "control_command_type":
                None,

            "control_command_type_selected":
                False,

            "command_topic_or_transport":
                None,

            "command_topic_or_transport_selected":
                False,

            "nominal_continuation_command":
                None,

            "nominal_continuation_command_selected":
                False,

            "stop_command":
                None,

            "stop_command_selected":
                False,

            "speed_reduction_command":
                None,

            "speed_reduction_command_selected":
                False,

            "hold_position_command":
                None,

            "hold_position_command_selected":
                False,

            "emergency_action":
                None,

            "emergency_action_selected":
                False,

            "fallback_action_mapping":
                None,

            "fallback_action_mapping_selected":
                gate.robot_action_mapping_selected,
        },

        "physical_platform_boundary": {
            "eventual_platform_role":
                EVENTUAL_PHYSICAL_PLATFORM_ROLE,

            "provisional_dataset_identity":
                "KIOS_QUADRUPED",

            "local_readiness":
                "not_collected",

            "actual_robot_identity":
                None,

            "actual_robot_identity_frozen":
                gate.physical_platform_identity_frozen,

            "compute_hardware":
                None,

            "compute_hardware_frozen":
                False,

            "sensor_suite":
                None,

            "sensor_suite_frozen":
                False,

            "calibration":
                None,

            "calibration_frozen":
                False,

            "synchronization":
                None,

            "synchronization_frozen":
                False,

            "reference_instrumentation":
                None,

            "reference_instrumentation_frozen":
                gate.physical_reference_instrumentation_frozen,

            "controller_interface_verified":
                False,

            "control_command_semantics_verified":
                False,

            "proprioception_available_and_verified":
                False,

            "physical_execution_ready":
                False,
        },

        "physical_partition_boundary": {
            "development_calibration_runs_separate_from_final_held_out_physical_tests":
                True,

            "base_trajectory_derivatives_remain_in_one_partition":
                True,

            "held_out_physical_data_may_select_model":
                False,

            "held_out_physical_data_may_select_learned_parameters":
                False,

            "held_out_physical_data_may_select_calibration_temperature":
                False,

            "held_out_physical_data_may_select_fault_severity_grid":
                False,

            "held_out_physical_data_may_select_attack_budget":
                False,

            "held_out_physical_data_may_select_health_threshold":
                False,

            "held_out_physical_data_may_select_suppression_recovery_threshold":
                False,

            "held_out_physical_data_may_select_fallback_threshold":
                False,

            "held_out_physical_data_may_select_safety_operating_point":
                False,

            "physical_test_partition_instantiated":
                gate.physical_test_partition_instantiated,
        },

        "fallback_and_threshold_boundary": {
            "fallback_defined_by_authoritative_phase9_section":
                False,

            "phase9_fallback_policy_selected":
                False,

            "phase9_fallback_threshold_selected":
                False,

            "phase9_fallback_execution_authorized":
                False,

            "fallback_thresholds_must_be_frozen_before_physical_tests":
                True,

            "fallback_threshold_selected":
                gate.fallback_threshold_selected,

            "safety_threshold_selected":
                gate.safety_threshold_selected,

            "threshold_role_is_validation_selected":
                True,

            "final_physical_test_may_select_threshold":
                False,

            "confirmation_may_select_threshold":
                False,
        },

        "physical_safety_metric_boundary": {
            "safe_stop_definition_present":
                False,

            "emergency_definition_present":
                False,

            "stopping_distance_definition_present":
                False,

            "control_command_definition_present":
                False,

            "cmd_vel_definition_present":
                False,

            "collision_metric_selected":
                False,

            "stopping_distance_metric_selected":
                False,

            "intervention_success_metric_selected":
                False,

            "tracking_safety_metric_selected":
                False,

            "physical_safety_acceptance_threshold_selected":
                False,

            "closed_loop_safety_metric_set_selected":
                False,
        },

        "historical_reuse_boundary": {
            "phase5_live_executor_safety_is_phase14_robot_supervisor":
                False,

            "historical_IMU_runtime_safety_is_phase14_robot_supervisor":
                False,

            "filesystem_or_capture_safety_equals_closed_loop_robot_safety":
                False,

            "historical_thresholds_adopted_for_phase14":
                False,

            "historical_robot_action_semantics_adopted":
                False,

            "historical_ood_threshold_adopted":
                False,

            "historical_embedded_status_semantics_adopted":
                False,
        },

        "upstream_evidence_boundary": {
            "phase9_runtime_suppression_available":
                False,

            "phase9_runtime_recovery_available":
                False,

            "phase9_runtime_estimator_status_available":
                False,

            "phase9_runtime_actions_assumed":
                gate.phase9_runtime_suppression_recovery_assumed,

            "phase13_resource_measurements_available":
                False,

            "phase13_resource_measurements_assumed":
                gate.phase13_resource_measurement_results_assumed,

            "phase13_onboard_resource_constraints_verified":
                False,

            "phase13_onboard_resource_constraints_assumed":
                gate.phase13_onboard_resource_constraints_assumed,

            "phase13_rq4_resource_answer_available":
                False,
        },

        "rq4_boundary": {
            "question":
                (
                    "Can the trust layer meet onboard resource constraints "
                    "and improve guarded closed-loop safety when fallback "
                    "thresholds are frozen before physical tests?"
                ),

            "resource_component_answer_available":
                False,

            "onboard_resource_constraints_verified":
                False,

            "closed_loop_safety_component_in_phase14":
                True,

            "fallback_thresholds_frozen":
                False,

            "guarded_physical_test_executed":
                False,

            "closed_loop_safety_answer_available":
                gate.rq4_closed_loop_safety_answer_available,

            "full_rq4_answer_available":
                gate.full_rq4_answer_available,
        },

        "execution_gate": {
            "supervisor_input_availability_verified":
                gate.supervisor_input_availability_verified,

            "operational_policy_selected":
                gate.operational_policy_selected,

            "controller_interface_selected":
                gate.controller_interface_selected,

            "robot_action_mapping_selected":
                gate.robot_action_mapping_selected,

            "fallback_threshold_selected":
                gate.fallback_threshold_selected,

            "safety_threshold_selected":
                gate.safety_threshold_selected,

            "physical_test_protocol_selected":
                gate.physical_test_protocol_selected,

            "physical_test_partition_instantiated":
                gate.physical_test_partition_instantiated,

            "physical_platform_identity_frozen":
                gate.physical_platform_identity_frozen,

            "physical_reference_instrumentation_frozen":
                gate.physical_reference_instrumentation_frozen,

            "robot_integration_execution_authorized":
                gate.robot_integration_execution_authorized,

            "physical_test_execution_authorized":
                gate.physical_test_execution_authorized,

            "closed_loop_safety_measurement_authorized":
                gate.closed_loop_safety_measurement_authorized,

            "closed_loop_safety_claim_authorized":
                gate.closed_loop_safety_claim_authorized,
        },

        "protected_scientific_boundaries": {
            "physical_robot_evidence_claimed":
                False,

            "closed_loop_safety_improvement_claimed":
                False,

            "phase9_runtime_actions_assumed":
                gate.phase9_runtime_suppression_recovery_assumed,

            "phase13_resource_measurement_results_assumed":
                gate.phase13_resource_measurement_results_assumed,

            "phase13_onboard_resource_constraints_assumed":
                gate.phase13_onboard_resource_constraints_assumed,

            "validation_data_opened":
                gate.validation_data_opened,

            "confirmation_data_used":
                gate.confirmation_data_used,

            "final_confirmation_execution_authorized":
                gate.final_confirmation_execution_authorized,

            "ate_rpe_computation_authorized":
                False,

            "final_scoring_authorized":
                False,
        },

        "next_phase_policy": {
            "phase15_software_preparation_may_proceed_after_phase14_checkpoint":
                True,

            "phase15_may_assume_phase14_physical_tests_executed":
                False,

            "phase15_may_assume_closed_loop_safety_answer_available":
                False,

            "phase15_may_assume_full_rq4_answer_available":
                False,

            "final_confirmation_execution_authorized":
                False,

            "deferred_phase5_through_phase14_empirical_obligations_remain_binding":
                True,
        },

        "source_bindings": {
            "phase13_freeze_sha256":
                phase13_freeze_sha256,

            "phase13_contract_sha256":
                phase13_contract_sha256,

            "phase9_freeze_sha256":
                phase9_freeze_sha256,

            "phase9_contract_sha256":
                phase9_contract_sha256,

            "master_context_sha256":
                master_context_sha256,

            "phase_plan_sha256":
                phase_plan_sha256,

            "data_protocol_sha256":
                data_protocol_sha256,

            "dataset_registry_sha256":
                dataset_registry_sha256,

            "runtime_integration_sha256":
                runtime_integration_sha256,

            "phase5_live_executor_safety_config_sha256":
                live_executor_config_sha256,

            "phase5_live_executor_safety_module_sha256":
                live_executor_module_sha256,

            "frontier_report_sha256":
                frontier_report_sha256,

            "frontier_json_sha256":
                frontier_json_sha256,

            "basis_report_sha256":
                basis_report_sha256,

            "basis_json_sha256":
                basis_json_sha256,
        },
    }


def validate_contract_manifest(
    payload: Mapping[str, Any],
) -> None:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise SupervisoryPhysicalIntegrationContractError(
            "Phase-14 contract must be a mapping"
        )

    if payload.get(
        "schema"
    ) != SCHEMA:
        raise SupervisoryPhysicalIntegrationContractError(
            "unexpected Phase-14 schema"
        )

    if payload[
        "lifecycle_status"
    ] != (
        Phase14Lifecycle
        .CONTRACT_IMPLEMENTED_ROBOT_SEMANTICS_UNSELECTED
        .value
    ):
        raise SupervisoryPhysicalIntegrationContractError(
            "unexpected Phase-14 lifecycle"
        )

    scope = payload[
        "phase_scope"
    ]

    if scope[
        "phase"
    ] != 14:
        raise SupervisoryPhysicalIntegrationContractError(
            "unexpected phase"
        )

    if scope[
        "name"
    ] != "guarded_real_robot_integration_and_supervisory_testing":
        raise SupervisoryPhysicalIntegrationContractError(
            "unexpected Phase-14 scope"
        )

    architecture = payload[
        "supervisor_architecture"
    ]

    if architecture[
        "learned_health_model_is_robot_controller"
    ] is not False:
        raise SupervisoryPhysicalIntegrationContractError(
            "health model may not become the robot controller"
        )

    if architecture[
        "separate_rule_based_supervisory_layer_required"
    ] is not True:
        raise SupervisoryPhysicalIntegrationContractError(
            "rule-based supervisor requirement lost"
        )

    if architecture[
        "physical_experiments_must_remain_guarded"
    ] is not True:
        raise SupervisoryPhysicalIntegrationContractError(
            "guarded physical-experiment requirement lost"
        )

    inputs = payload[
        "supervisor_input_schema"
    ]

    if inputs[
        "candidate_inputs"
    ] != list(
        SUPERVISOR_INPUT_IDENTITIES
    ):
        raise SupervisoryPhysicalIntegrationContractError(
            "authoritative supervisor input identities changed"
        )

    if inputs[
        "candidate_input_count"
    ] != 6:
        raise SupervisoryPhysicalIntegrationContractError(
            "unexpected supervisor input count"
        )

    if inputs[
        "candidate_input_identity_implies_runtime_readiness"
    ] is not False:
        raise SupervisoryPhysicalIntegrationContractError(
            "input identity cannot imply runtime readiness"
        )

    if inputs[
        "all_candidate_inputs_runtime_verified"
    ] is not False:
        raise SupervisoryPhysicalIntegrationContractError(
            "supervisor inputs are not runtime verified"
        )

    policies = payload[
        "planned_policy_comparisons"
    ]

    if policies[
        "identities"
    ] != list(
        POLICY_COMPARISON_IDENTITIES
    ):
        raise SupervisoryPhysicalIntegrationContractError(
            "planned policy comparison identities changed"
        )

    if policies[
        "identity_count"
    ] != 4:
        raise SupervisoryPhysicalIntegrationContractError(
            "unexpected policy comparison count"
        )

    for key in (
        "identities_are_selected_operational_policy",
        "identities_define_robot_command_semantics",
        "nominal_continuation_action_semantics_selected",
        "always_stop_action_semantics_selected",
        "health_triggered_operational_rule_selected",
        "oracle_health_is_runtime_available_signal",
        "policy_comparison_execution_selected",
        "operational_policy_selected",
    ):
        if policies[
            key
        ] is not False:
            raise SupervisoryPhysicalIntegrationContractError(
                f"{key} must remain false"
            )

    if policies[
        "oracle_health_role_is_planned_comparison_only"
    ] is not True:
        raise SupervisoryPhysicalIntegrationContractError(
            "oracle-health boundary lost"
        )

    actions = payload[
        "robot_action_semantics_boundary"
    ]

    for key, value in actions.items():
        if key.endswith(
            "_selected"
        ):
            if value is not False:
                raise SupervisoryPhysicalIntegrationContractError(
                    f"{key} must remain false"
                )
        elif value is not None:
            raise SupervisoryPhysicalIntegrationContractError(
                f"{key} must remain unselected"
            )

    platform = payload[
        "physical_platform_boundary"
    ]

    if platform[
        "eventual_platform_role"
    ] != EVENTUAL_PHYSICAL_PLATFORM_ROLE:
        raise SupervisoryPhysicalIntegrationContractError(
            "eventual platform role changed"
        )

    if platform[
        "provisional_dataset_identity"
    ] != "KIOS_QUADRUPED":
        raise SupervisoryPhysicalIntegrationContractError(
            "provisional physical dataset identity changed"
        )

    if platform[
        "local_readiness"
    ] != "not_collected":
        raise SupervisoryPhysicalIntegrationContractError(
            "local physical dataset readiness changed"
        )

    for key, value in platform.items():
        if key in {
            "eventual_platform_role",
            "provisional_dataset_identity",
            "local_readiness",
        }:
            continue

        if key.endswith(
            "_frozen"
        ) or key.endswith(
            "_verified"
        ) or key == "physical_execution_ready":
            if value is not False:
                raise SupervisoryPhysicalIntegrationContractError(
                    f"{key} must remain false"
                )
        else:
            if value is not None:
                raise SupervisoryPhysicalIntegrationContractError(
                    f"{key} must remain unselected"
                )

    partition = payload[
        "physical_partition_boundary"
    ]

    true_partition_keys = {
        "development_calibration_runs_separate_from_final_held_out_physical_tests",
        "base_trajectory_derivatives_remain_in_one_partition",
    }

    for key, value in partition.items():
        if key in true_partition_keys:
            if value is not True:
                raise SupervisoryPhysicalIntegrationContractError(
                    f"{key} must remain true"
                )
        elif value is not False:
            raise SupervisoryPhysicalIntegrationContractError(
                f"{key} must remain false"
            )

    fallback = payload[
        "fallback_and_threshold_boundary"
    ]

    true_fallback_keys = {
        "fallback_thresholds_must_be_frozen_before_physical_tests",
        "threshold_role_is_validation_selected",
    }

    for key, value in fallback.items():
        if key in true_fallback_keys:
            if value is not True:
                raise SupervisoryPhysicalIntegrationContractError(
                    f"{key} must remain true"
                )
        elif value is not False:
            raise SupervisoryPhysicalIntegrationContractError(
                f"{key} must remain false"
            )

    metrics = payload[
        "physical_safety_metric_boundary"
    ]

    if set(
        metrics.values()
    ) != {
        False,
    }:
        raise SupervisoryPhysicalIntegrationContractError(
            "physical safety metrics must remain unselected"
        )

    reuse = payload[
        "historical_reuse_boundary"
    ]

    if set(
        reuse.values()
    ) != {
        False,
    }:
        raise SupervisoryPhysicalIntegrationContractError(
            "historical safety semantics were adopted"
        )

    upstream = payload[
        "upstream_evidence_boundary"
    ]

    if set(
        upstream.values()
    ) != {
        False,
    }:
        raise SupervisoryPhysicalIntegrationContractError(
            "unavailable upstream runtime evidence was assumed"
        )

    rq4 = payload[
        "rq4_boundary"
    ]

    if rq4[
        "closed_loop_safety_component_in_phase14"
    ] is not True:
        raise SupervisoryPhysicalIntegrationContractError(
            "RQ4 Phase-14 boundary lost"
        )

    for key in (
        "resource_component_answer_available",
        "onboard_resource_constraints_verified",
        "fallback_thresholds_frozen",
        "guarded_physical_test_executed",
        "closed_loop_safety_answer_available",
        "full_rq4_answer_available",
    ):
        if rq4[
            key
        ] is not False:
            raise SupervisoryPhysicalIntegrationContractError(
                f"{key} must remain false"
            )

    if set(
        payload[
            "execution_gate"
        ].values()
    ) != {
        False,
    }:
        raise SupervisoryPhysicalIntegrationContractError(
            "Phase-14 execution gate must remain closed"
        )

    protected = payload[
        "protected_scientific_boundaries"
    ]

    if set(
        protected.values()
    ) != {
        False,
    }:
        raise SupervisoryPhysicalIntegrationContractError(
            "protected Phase-14 scientific boundary changed"
        )

    next_phase = payload[
        "next_phase_policy"
    ]

    if next_phase[
        "phase15_software_preparation_may_proceed_after_phase14_checkpoint"
    ] is not True:
        raise SupervisoryPhysicalIntegrationContractError(
            "Phase-15 software-preparation boundary lost"
        )

    if next_phase[
        "deferred_phase5_through_phase14_empirical_obligations_remain_binding"
    ] is not True:
        raise SupervisoryPhysicalIntegrationContractError(
            "deferred empirical obligations were lost"
        )

    for key in (
        "phase15_may_assume_phase14_physical_tests_executed",
        "phase15_may_assume_closed_loop_safety_answer_available",
        "phase15_may_assume_full_rq4_answer_available",
        "final_confirmation_execution_authorized",
    ):
        if next_phase[
            key
        ] is not False:
            raise SupervisoryPhysicalIntegrationContractError(
                f"{key} must remain false"
            )
