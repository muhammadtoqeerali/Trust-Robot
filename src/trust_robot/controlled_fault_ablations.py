"""TRUST-ROBOT Phase-10 controlled-fault / causal-ablation contract.

Phase-10 role:
    Causal ablations and controlled faults.
    Same-backbone RQ1/RQ2 evidence.

RQ1 asks whether explicitly supervised and calibrated
healthy/degraded/unusable modality probabilities outperform fair,
validation-calibrated proxy reliability scores.

RQ2 asks whether health-aware factor weighting improves
localization/state-estimation robustness and graceful degradation under
increasing fault severity.

This module freezes the experiment architecture and admissible native
corruption bindings only. It executes no experiment and selects no numeric
fault severity, severity grid, attack budget, schedule, ablation variant,
proxy score, seed schedule, physical fault, metric, or held-out operating
point.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


SCHEMA = (
    "TRUST_ROBOT_PHASE10_CONTROLLED_FAULT_ABLATION_CONTRACT_V1"
)

NATIVE_PHASE3_FAMILIES = (
    "EVENT_GAP",
    "EVENT_REPEAT",
    "TIMESTAMP_STEP_SHIFT",
)


class ControlledFaultAblationContractError(ValueError):
    """Raised when the Phase-10 scientific contract is violated."""


class Phase10Lifecycle(str, Enum):
    CONTRACT_IMPLEMENTED_EXPERIMENTS_UNSELECTED = (
        "contract_implemented_experiments_unselected"
    )


class EvidenceQuestion(str, Enum):
    RQ1 = "RQ1"
    RQ2 = "RQ2"


@dataclass(frozen=True)
class CurrentPhase10Gate:
    same_backbone_operational_definition_selected: bool = False
    rq1_proxy_reliability_definition_selected: bool = False
    rq1_comparison_variants_selected: bool = False
    rq2_comparison_variants_selected: bool = False

    numeric_fault_severity_selected: bool = False
    severity_grid_selected: bool = False
    attack_budget_selected: bool = False
    fault_schedule_selected: bool = False
    fault_duration_selected: bool = False
    fault_probability_selected: bool = False
    partition_seed_schedule_selected: bool = False

    phase3_native_fault_execution_authorized: bool = False
    controlled_availability_execution_authorized: bool = False
    physical_fault_execution_authorized: bool = False
    phase10_experiment_execution_authorized: bool = False

    validation_data_opened: bool = False
    confirmation_data_used: bool = False

    def __post_init__(self) -> None:
        for field_name in self.__dataclass_fields__:
            if getattr(
                self,
                field_name,
            ) is not False:
                raise ControlledFaultAblationContractError(
                    f"{field_name} must remain false in the "
                    "current Phase-10 evidence state"
                )


CURRENT_PHASE10_GATE = CurrentPhase10Gate()


def native_phase3_family_names() -> tuple[str, ...]:
    return NATIVE_PHASE3_FAMILIES


def assert_phase10_experiment_execution_authorized(
    gate: CurrentPhase10Gate = CURRENT_PHASE10_GATE,
) -> None:
    if gate.phase10_experiment_execution_authorized is not True:
        raise ControlledFaultAblationContractError(
            "Phase-10 experiment execution is not authorized: "
            "same-backbone comparison semantics, fault operating points, "
            "and required upstream runtime evidence remain unselected"
        )


def assert_native_fault_execution_authorized(
    gate: CurrentPhase10Gate = CURRENT_PHASE10_GATE,
) -> None:
    if gate.phase3_native_fault_execution_authorized is not True:
        raise ControlledFaultAblationContractError(
            "native Phase-3 corruption execution is not authorized "
            "for Phase-10 evidence"
        )


def assert_physical_fault_execution_authorized(
    gate: CurrentPhase10Gate = CURRENT_PHASE10_GATE,
) -> None:
    if gate.physical_fault_execution_authorized is not True:
        raise ControlledFaultAblationContractError(
            "physical controlled-fault execution is not authorized"
        )


def build_contract_manifest(
    *,
    phase9_freeze_sha256: str,
    phase3_freeze_sha256: str,
    phase3_taxonomy_sha256: str,
    phase3_selection_sha256: str,
    phase3_module_sha256: str,
    phase3_selection_module_sha256: str,
    controlled_availability_config_sha256: str,
    controlled_availability_module_sha256: str,
    controlled_availability_audit_sha256: str,
    master_context_sha256: str,
    phase_plan_sha256: str,
    frontier_report_sha256: str,
    frontier_json_sha256: str,
    scope_report_sha256: str,
    scope_json_sha256: str,
    rq_basis_report_sha256: str,
    rq_basis_json_sha256: str,
) -> dict[str, Any]:
    gate = CURRENT_PHASE10_GATE

    return {
        "schema":
            SCHEMA,

        "lifecycle_status":
            Phase10Lifecycle
            .CONTRACT_IMPLEMENTED_EXPERIMENTS_UNSELECTED
            .value,

        "phase_scope": {
            "phase":
                10,

            "name":
                "causal_ablations_and_controlled_faults",

            "evidence_role":
                "same_backbone_RQ1_RQ2_evidence",

            "numbered_master_section_10_is_phase_plan_phase10":
                False,

            "numbered_master_section_10_role":
                "safety_supervision_conceptual_section",
        },

        "research_questions": {
            "RQ1":
                (
                    "Can explicitly supervised and calibrated "
                    "healthy/degraded/unusable modality probabilities "
                    "outperform fair validation-calibrated proxy "
                    "reliability scores?"
                ),

            "RQ2":
                (
                    "Does health-aware factor weighting improve "
                    "localization/state-estimation robustness and graceful "
                    "degradation under increasing fault severity?"
                ),
        },

        "same_backbone_boundary": {
            "requirement_named_by_phase_plan":
                True,

            "operational_definition":
                "unselected",

            "operational_definition_selected":
                gate.same_backbone_operational_definition_selected,

            "ablation_variants":
                [],

            "ablation_variants_selected":
                False,

            "undeclared_pipeline_changes_allowed":
                False,
        },

        "rq1_ablation_boundary": {
            "supervised_calibrated_health_probability_path_named":
                True,

            "fair_validation_calibrated_proxy_path_named":
                True,

            "proxy_reliability_definition":
                "unselected",

            "proxy_reliability_definition_selected":
                gate.rq1_proxy_reliability_definition_selected,

            "comparison_variants_selected":
                gate.rq1_comparison_variants_selected,

            "empirical_phase5_health_model_available":
                False,

            "empirical_phase6_calibration_available":
                False,

            "rq1_executable":
                False,
        },

        "rq2_ablation_boundary": {
            "health_aware_factor_weighting_named":
                True,

            "increasing_fault_severity_named":
                True,

            "comparison_variants_selected":
                gate.rq2_comparison_variants_selected,

            "phase8_numeric_factor_conditioning_available":
                False,

            "phase9_runtime_suppression_available":
                False,

            "phase9_runtime_recovery_available":
                False,

            "phase9_runtime_estimator_status_available":
                False,

            "rq2_executable":
                False,
        },

        "native_phase3_binding": {
            "native_families":
                list(
                    native_phase3_family_names()
                ),

            "native_family_expansion_selected":
                False,

            "selection_policy_bound":
                True,

            "synthetic_truth_is_health_label":
                False,

            "synthetic_truth_is_physical_fault_proof":
                False,

            "synthetic_truth_is_runtime_causal_evidence":
                False,

            "execution_authorized":
                gate.phase3_native_fault_execution_authorized,
        },

        "fault_parameter_boundary": {
            "numeric_fault_severity":
                None,

            "numeric_fault_severity_selected":
                gate.numeric_fault_severity_selected,

            "severity_grid":
                None,

            "severity_grid_selected":
                gate.severity_grid_selected,

            "attack_budget":
                None,

            "attack_budget_selected":
                gate.attack_budget_selected,

            "fault_schedule":
                None,

            "fault_schedule_selected":
                gate.fault_schedule_selected,

            "fault_duration":
                None,

            "fault_duration_selected":
                gate.fault_duration_selected,

            "fault_probability":
                None,

            "fault_probability_selected":
                gate.fault_probability_selected,

            "partition_seed_schedule":
                None,

            "partition_seed_schedule_selected":
                gate.partition_seed_schedule_selected,

            "silent_severity_default_allowed":
                False,

            "silent_attack_budget_default_allowed":
                False,

            "performance_based_corruption_selection_allowed":
                False,
        },

        "fault_injection_rules": {
            "scientifically_appropriate_layer_required":
                True,

            "raw_sensor_and_factor_level_corruption_equivalent":
                False,

            "clean_and_corrupted_derivatives_remain_same_partition":
                True,

            "random_seeds_may_be_reused_across_partitions":
                False,

            "held_out_test_may_select_severity_levels":
                False,

            "held_out_test_may_select_attack_budgets":
                False,
        },

        "controlled_availability_binding": {
            "interface_named":
                True,

            "controlled_supervision_kind":
                "measurement_availability",

            "accepted_health_supervision_source":
                False,

            "real_health_label_count":
                0,

            "absence_of_intervention_alone_proves_healthy":
                False,

            "execution_authorized":
                gate.controlled_availability_execution_authorized,
        },

        "execution_gate": {
            "phase10_experiment_execution_authorized":
                gate.phase10_experiment_execution_authorized,

            "native_phase3_fault_execution_authorized":
                gate.phase3_native_fault_execution_authorized,

            "controlled_availability_execution_authorized":
                gate.controlled_availability_execution_authorized,

            "physical_fault_execution_authorized":
                gate.physical_fault_execution_authorized,

            "controlled_fault_experiment_executed":
                False,

            "causal_ablation_executed":
                False,

            "physical_fault_executed":
                False,
        },

        "data_selection_boundary": {
            "validation_data_opened":
                gate.validation_data_opened,

            "confirmation_data_used":
                gate.confirmation_data_used,

            "confirmation_may_select_ablation_variants":
                False,

            "confirmation_may_select_fault_severity":
                False,

            "confirmation_may_select_severity_grid":
                False,

            "confirmation_may_select_fault_schedule":
                False,

            "confirmation_may_select_seed_schedule":
                False,

            "validation_metric_may_select_corruption_conditions":
                False,
        },

        "evaluation_boundary": {
            "localization_state_estimation_separate":
                True,

            "modality_health_discrimination_separate":
                True,

            "calibration_quality_separate":
                True,

            "controlled_fault_robustness_separate":
                True,

            "graceful_degradation_separate":
                True,

            "estimator_availability_failure_separate":
                True,

            "single_undocumented_aggregate_score_allowed":
                False,

            "ate_rpe_computation_authorized":
                False,

            "final_scoring_authorized":
                False,
        },

        "source_bindings": {
            "phase9_freeze_sha256":
                phase9_freeze_sha256,

            "phase3_freeze_sha256":
                phase3_freeze_sha256,

            "phase3_taxonomy_sha256":
                phase3_taxonomy_sha256,

            "phase3_selection_sha256":
                phase3_selection_sha256,

            "phase3_module_sha256":
                phase3_module_sha256,

            "phase3_selection_module_sha256":
                phase3_selection_module_sha256,

            "controlled_availability_config_sha256":
                controlled_availability_config_sha256,

            "controlled_availability_module_sha256":
                controlled_availability_module_sha256,

            "controlled_availability_audit_sha256":
                controlled_availability_audit_sha256,

            "master_context_sha256":
                master_context_sha256,

            "phase_plan_sha256":
                phase_plan_sha256,

            "frontier_report_sha256":
                frontier_report_sha256,

            "frontier_json_sha256":
                frontier_json_sha256,

            "scope_report_sha256":
                scope_report_sha256,

            "scope_json_sha256":
                scope_json_sha256,

            "rq_basis_report_sha256":
                rq_basis_report_sha256,

            "rq_basis_json_sha256":
                rq_basis_json_sha256,
        },
    }


def validate_contract_manifest(
    payload: Mapping[str, Any],
) -> None:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise ControlledFaultAblationContractError(
            "Phase-10 contract must be a mapping"
        )

    if payload.get(
        "schema"
    ) != SCHEMA:
        raise ControlledFaultAblationContractError(
            "unexpected Phase-10 schema"
        )

    if payload[
        "lifecycle_status"
    ] != (
        Phase10Lifecycle
        .CONTRACT_IMPLEMENTED_EXPERIMENTS_UNSELECTED
        .value
    ):
        raise ControlledFaultAblationContractError(
            "unexpected Phase-10 lifecycle"
        )

    scope = payload[
        "phase_scope"
    ]

    if scope[
        "phase"
    ] != 10:
        raise ControlledFaultAblationContractError(
            "unexpected phase"
        )

    if scope[
        "evidence_role"
    ] != "same_backbone_RQ1_RQ2_evidence":
        raise ControlledFaultAblationContractError(
            "Phase-10 evidence role changed"
        )

    if scope[
        "numbered_master_section_10_is_phase_plan_phase10"
    ] is not False:
        raise ControlledFaultAblationContractError(
            "numbered safety-supervision section was confused with Phase 10"
        )

    same_backbone = payload[
        "same_backbone_boundary"
    ]

    if same_backbone[
        "operational_definition"
    ] != "unselected":
        raise ControlledFaultAblationContractError(
            "same-backbone operational definition was invented"
        )

    if same_backbone[
        "operational_definition_selected"
    ] is not False:
        raise ControlledFaultAblationContractError(
            "same-backbone definition must remain unselected"
        )

    if same_backbone[
        "ablation_variants"
    ] != []:
        raise ControlledFaultAblationContractError(
            "ablation variants were selected unexpectedly"
        )

    if same_backbone[
        "ablation_variants_selected"
    ] is not False:
        raise ControlledFaultAblationContractError(
            "ablation variants must remain unselected"
        )

    rq1 = payload[
        "rq1_ablation_boundary"
    ]

    if rq1[
        "proxy_reliability_definition"
    ] != "unselected":
        raise ControlledFaultAblationContractError(
            "RQ1 proxy definition was invented"
        )

    if rq1[
        "proxy_reliability_definition_selected"
    ] is not False:
        raise ControlledFaultAblationContractError(
            "RQ1 proxy definition must remain unselected"
        )

    if rq1[
        "rq1_executable"
    ] is not False:
        raise ControlledFaultAblationContractError(
            "RQ1 cannot execute in current evidence state"
        )

    rq2 = payload[
        "rq2_ablation_boundary"
    ]

    if rq2[
        "rq2_executable"
    ] is not False:
        raise ControlledFaultAblationContractError(
            "RQ2 cannot execute in current evidence state"
        )

    native = payload[
        "native_phase3_binding"
    ]

    if native[
        "native_families"
    ] != list(
        NATIVE_PHASE3_FAMILIES
    ):
        raise ControlledFaultAblationContractError(
            "native Phase-3 family set changed"
        )

    if native[
        "native_family_expansion_selected"
    ] is not False:
        raise ControlledFaultAblationContractError(
            "new Phase-10 fault family selected unexpectedly"
        )

    if native[
        "selection_policy_bound"
    ] is not True:
        raise ControlledFaultAblationContractError(
            "Phase-3 selection policy binding lost"
        )

    for key in (
        "synthetic_truth_is_health_label",
        "synthetic_truth_is_physical_fault_proof",
        "synthetic_truth_is_runtime_causal_evidence",
        "execution_authorized",
    ):
        if native[
            key
        ] is not False:
            raise ControlledFaultAblationContractError(
                f"{key} must remain false"
            )

    fault = payload[
        "fault_parameter_boundary"
    ]

    nullable = (
        "numeric_fault_severity",
        "severity_grid",
        "attack_budget",
        "fault_schedule",
        "fault_duration",
        "fault_probability",
        "partition_seed_schedule",
    )

    for key in nullable:
        if fault[
            key
        ] is not None:
            raise ControlledFaultAblationContractError(
                f"{key} was selected unexpectedly"
            )

    selected_keys = (
        "numeric_fault_severity_selected",
        "severity_grid_selected",
        "attack_budget_selected",
        "fault_schedule_selected",
        "fault_duration_selected",
        "fault_probability_selected",
        "partition_seed_schedule_selected",
        "silent_severity_default_allowed",
        "silent_attack_budget_default_allowed",
        "performance_based_corruption_selection_allowed",
    )

    for key in selected_keys:
        if fault[
            key
        ] is not False:
            raise ControlledFaultAblationContractError(
                f"{key} must remain false"
            )

    rules = payload[
        "fault_injection_rules"
    ]

    if rules[
        "scientifically_appropriate_layer_required"
    ] is not True:
        raise ControlledFaultAblationContractError(
            "fault injection layer requirement lost"
        )

    if rules[
        "raw_sensor_and_factor_level_corruption_equivalent"
    ] is not False:
        raise ControlledFaultAblationContractError(
            "raw and factor-level corruptions cannot be treated as equivalent"
        )

    if rules[
        "clean_and_corrupted_derivatives_remain_same_partition"
    ] is not True:
        raise ControlledFaultAblationContractError(
            "split provenance rule lost"
        )

    if rules[
        "random_seeds_may_be_reused_across_partitions"
    ] is not False:
        raise ControlledFaultAblationContractError(
            "cross-partition seed reuse cannot be enabled"
        )

    availability = payload[
        "controlled_availability_binding"
    ]

    if availability[
        "accepted_health_supervision_source"
    ] is not False:
        raise ControlledFaultAblationContractError(
            "controlled availability was promoted to accepted supervision"
        )

    if availability[
        "real_health_label_count"
    ] != 0:
        raise ControlledFaultAblationContractError(
            "real health labels unexpectedly appeared"
        )

    if availability[
        "execution_authorized"
    ] is not False:
        raise ControlledFaultAblationContractError(
            "controlled availability execution unexpectedly authorized"
        )

    execution = payload[
        "execution_gate"
    ]

    if set(
        execution.values()
    ) != {
        False,
    }:
        raise ControlledFaultAblationContractError(
            "Phase-10 execution gate must remain closed"
        )

    selection = payload[
        "data_selection_boundary"
    ]

    if set(
        selection.values()
    ) != {
        False,
    }:
        raise ControlledFaultAblationContractError(
            "Phase-10 selection boundary changed"
        )

    evaluation = payload[
        "evaluation_boundary"
    ]

    if evaluation[
        "single_undocumented_aggregate_score_allowed"
    ] is not False:
        raise ControlledFaultAblationContractError(
            "undocumented aggregate score cannot be enabled"
        )

    if evaluation[
        "ate_rpe_computation_authorized"
    ] is not False:
        raise ControlledFaultAblationContractError(
            "ATE/RPE remains unauthorized"
        )

    if evaluation[
        "final_scoring_authorized"
    ] is not False:
        raise ControlledFaultAblationContractError(
            "final scoring remains unauthorized"
        )
