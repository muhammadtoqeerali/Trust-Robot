"""TRUST-ROBOT Phase-13 resource-evaluation contract.

The authoritative project requires two resource-cost views:

1. complete-system cost
2. incremental trust-layer overhead

Expected evidence families are:

- mean latency
- P95 latency
- deadline misses
- throughput
- processor utilization where measurable
- peak memory
- storage
- average power
- peak power
- energy per update or trajectory

This module freezes those evidence requirements and their required metadata.
It deliberately does not choose a measurement clock, deadline, throughput
definition, memory method, power method, energy method, warm-up duration,
repetition count, aggregation protocol, hardware profile, or real-time
acceptance threshold.

Historical IMU-reliability resource instrumentation is not automatically
adopted as TRUST-ROBOT Phase-13 policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


SCHEMA = (
    "TRUST_ROBOT_PHASE13_RESOURCE_EVALUATION_CONTRACT_V1"
)

COST_VIEWS = (
    "complete_system_cost",
    "incremental_trust_layer_overhead",
)

RESOURCE_EVIDENCE_FAMILIES = (
    "mean_latency",
    "p95_latency",
    "deadline_misses",
    "throughput",
    "processor_utilization_where_measurable",
    "peak_memory",
    "storage",
    "average_power",
    "peak_power",
    "energy_per_update_or_trajectory",
)

REQUIRED_MEASUREMENT_METADATA = (
    "hardware_versions",
    "software_versions",
    "power_clock_mode",
    "sensor_rates",
    "estimator_window_size",
    "warmup_policy",
    "measurement_method",
)


class ResourceEvaluationContractError(ValueError):
    """Raised when the current Phase-13 evidence boundary is violated."""


class Phase13Lifecycle(str, Enum):
    CONTRACT_IMPLEMENTED_MEASUREMENT_POLICY_UNSELECTED = (
        "contract_implemented_measurement_policy_unselected"
    )


@dataclass(frozen=True)
class CurrentPhase13Gate:
    exact_latency_definition_selected: bool = False
    timing_clock_source_selected: bool = False
    deadline_definition_selected: bool = False
    throughput_definition_selected: bool = False

    processor_utilization_measurement_selected: bool = False
    peak_memory_measurement_selected: bool = False
    storage_scope_selected: bool = False

    power_measurement_method_selected: bool = False
    energy_measurement_method_selected: bool = False
    energy_unit_scope_update_vs_trajectory_selected: bool = False

    measurement_scope_boundaries_selected: bool = False

    warmup_policy_selected: bool = False
    repetition_policy_selected: bool = False
    aggregation_policy_selected: bool = False

    hardware_profile_frozen: bool = False
    software_runtime_profile_frozen: bool = False
    power_clock_mode_frozen: bool = False
    sensor_rate_profile_frozen: bool = False
    estimator_window_size_frozen: bool = False
    measurement_method_frozen: bool = False

    cpu_specific_metric_selected: bool = False
    gpu_specific_metric_selected: bool = False
    real_time_acceptance_threshold_selected: bool = False

    resource_measurement_execution_authorized: bool = False
    resource_claim_authorized: bool = False
    rq4_resource_answer_available: bool = False

    phase14_closed_loop_safety_evidence_assumed: bool = False

    validation_data_opened: bool = False
    confirmation_data_used: bool = False

    def __post_init__(self) -> None:
        for field_name in self.__dataclass_fields__:
            if getattr(
                self,
                field_name,
            ) is not False:
                raise ResourceEvaluationContractError(
                    f"{field_name} must remain false in the "
                    "current Phase-13 evidence state"
                )


CURRENT_PHASE13_GATE = CurrentPhase13Gate()


def cost_views() -> tuple[str, ...]:
    return COST_VIEWS


def resource_evidence_families() -> tuple[str, ...]:
    return RESOURCE_EVIDENCE_FAMILIES


def required_measurement_metadata() -> tuple[str, ...]:
    return REQUIRED_MEASUREMENT_METADATA


def assert_resource_measurement_authorized(
    gate: CurrentPhase13Gate = CURRENT_PHASE13_GATE,
) -> None:
    if gate.resource_measurement_execution_authorized is not True:
        raise ResourceEvaluationContractError(
            "resource measurement execution is not authorized: "
            "the concrete Phase-13 measurement protocol is unselected"
        )


def assert_resource_claim_authorized(
    gate: CurrentPhase13Gate = CURRENT_PHASE13_GATE,
) -> None:
    if gate.resource_claim_authorized is not True:
        raise ResourceEvaluationContractError(
            "resource claim is not authorized"
        )


def build_contract_manifest(
    *,
    phase12_freeze_sha256: str,
    master_context_sha256: str,
    phase_plan_sha256: str,
    frontier_report_sha256: str,
    frontier_json_sha256: str,
    basis_report_sha256: str,
    basis_json_sha256: str,
    runtime_protocol_sha256: str,
    runtime_integration_sha256: str,
    embedded_ledger_sha256: str,
    embedded_reference_sha256: str,
    portable_c_sha256: str,
    build_blocker_sha256: str,
    paper_matrix_sha256: str,
    project_config_sha256: str,
    historical_benchmark_sha256: str,
    historical_builder_sha256: str,
) -> dict[str, Any]:
    gate = CURRENT_PHASE13_GATE

    return {
        "schema":
            SCHEMA,

        "lifecycle_status":
            Phase13Lifecycle
            .CONTRACT_IMPLEMENTED_MEASUREMENT_POLICY_UNSELECTED
            .value,

        "phase_scope": {
            "phase":
                13,

            "name":
                "resource_evaluation",

            "evidence_role":
                (
                    "latency_memory_throughput_power_and_"
                    "computational_resource_evidence"
                ),
        },

        "evaluation_family_boundary": {
            "resource_evidence_is_separate_evaluation_family":
                True,

            "may_be_collapsed_into_undocumented_aggregate_score":
                False,
        },

        "cost_views": {
            "required":
                list(
                    cost_views()
                ),

            "required_count":
                len(
                    COST_VIEWS
                ),

            "complete_system_cost_measurement_available":
                False,

            "incremental_trust_layer_overhead_measurement_available":
                False,
        },

        "resource_evidence_schema": {
            "required_families":
                list(
                    resource_evidence_families()
                ),

            "required_family_count":
                len(
                    RESOURCE_EVIDENCE_FAMILIES
                ),

            "families_are_measurement_results":
                False,

            "families_define_required_future_evidence":
                True,

            "processor_utilization_is_conditional_where_measurable":
                True,
        },

        "measurement_metadata_schema": {
            "required_fields":
                list(
                    required_measurement_metadata()
                ),

            "required_field_count":
                len(
                    REQUIRED_MEASUREMENT_METADATA
                ),

            "values_currently_frozen":
                False,
        },

        "measurement_policy_boundary": {
            "exact_latency_definition":
                None,

            "exact_latency_definition_selected":
                gate.exact_latency_definition_selected,

            "timing_clock_source":
                None,

            "timing_clock_source_selected":
                gate.timing_clock_source_selected,

            "deadline_definition":
                None,

            "deadline_definition_selected":
                gate.deadline_definition_selected,

            "throughput_definition":
                None,

            "throughput_definition_selected":
                gate.throughput_definition_selected,

            "processor_utilization_measurement":
                None,

            "processor_utilization_measurement_selected":
                gate.processor_utilization_measurement_selected,

            "peak_memory_measurement":
                None,

            "peak_memory_measurement_selected":
                gate.peak_memory_measurement_selected,

            "storage_scope":
                None,

            "storage_scope_selected":
                gate.storage_scope_selected,

            "power_measurement_method":
                None,

            "power_measurement_method_selected":
                gate.power_measurement_method_selected,

            "energy_measurement_method":
                None,

            "energy_measurement_method_selected":
                gate.energy_measurement_method_selected,

            "energy_unit_scope_update_vs_trajectory":
                None,

            "energy_unit_scope_update_vs_trajectory_selected":
                gate.energy_unit_scope_update_vs_trajectory_selected,

            "measurement_scope_boundaries":
                None,

            "measurement_scope_boundaries_selected":
                gate.measurement_scope_boundaries_selected,

            "warmup_policy":
                None,

            "warmup_policy_selected":
                gate.warmup_policy_selected,

            "repetition_policy":
                None,

            "repetition_policy_selected":
                gate.repetition_policy_selected,

            "aggregation_policy":
                None,

            "aggregation_policy_selected":
                gate.aggregation_policy_selected,

            "cpu_specific_metric":
                None,

            "cpu_specific_metric_selected":
                gate.cpu_specific_metric_selected,

            "gpu_specific_metric":
                None,

            "gpu_specific_metric_selected":
                gate.gpu_specific_metric_selected,

            "real_time_acceptance_threshold":
                None,

            "real_time_acceptance_threshold_selected":
                gate.real_time_acceptance_threshold_selected,
        },

        "measurement_environment_boundary": {
            "hardware_profile":
                None,

            "hardware_profile_frozen":
                gate.hardware_profile_frozen,

            "software_runtime_profile":
                None,

            "software_runtime_profile_frozen":
                gate.software_runtime_profile_frozen,

            "power_clock_mode":
                None,

            "power_clock_mode_frozen":
                gate.power_clock_mode_frozen,

            "sensor_rate_profile":
                None,

            "sensor_rate_profile_frozen":
                gate.sensor_rate_profile_frozen,

            "estimator_window_size":
                None,

            "estimator_window_size_frozen":
                gate.estimator_window_size_frozen,

            "measurement_method":
                None,

            "measurement_method_frozen":
                gate.measurement_method_frozen,
        },

        "historical_resource_reuse_boundary": {
            "historical_protocol_exists":
                True,

            "historical_protocol_identity":
                "RUNTIME_RESOURCE_OVERHEAD_PROTOCOL_V1",

            "historical_protocol_is_TRUST_ROBOT_phase13_protocol":
                False,

            "historical_numeric_latency_targets_adopted":
                False,

            "historical_warmup_iteration_count_adopted":
                False,

            "historical_repetition_count_adopted":
                False,

            "historical_latency_clock_method_adopted":
                False,

            "historical_median_primary_statistic_adopted":
                False,

            "historical_rss_method_adopted":
                False,

            "historical_tracemalloc_method_adopted":
                False,

            "historical_reference_host_results_adopted":
                False,

            "historical_stm32_claims_adopted":
                False,

            "legacy_IMU_HAR_resource_semantics_adopted":
                False,

            "historical_project_latency_targets_adopted":
                False,

            "legacy_instrumentation_may_inform_future_engineering_implementation_only_after_explicit_phase13_binding":
                True,
        },

        "platform_claim_boundary": {
            "reference_host_measurement_equals_onboard_robot_measurement":
                False,

            "reference_host_measurement_equals_stm32_measurement":
                False,

            "host_python_or_native_measurement_may_be_relabelled_as_stm32":
                False,

            "stm32_latency_claim_authorized":
                False,

            "stm32_energy_claim_authorized":
                False,

            "stm32_flash_claim_authorized":
                False,

            "stm32_ram_claim_authorized":
                False,

            "stm32_cycles_claim_authorized":
                False,

            "target_specific_resource_claim_requires_target_specific_measurement":
                True,

            "onboard_robot_resource_claim_requires_onboard_robot_measurement":
                True,
        },

        "rq4_boundary": {
            "question":
                (
                    "Can the trust layer meet onboard resource constraints "
                    "and improve guarded closed-loop safety when fallback "
                    "thresholds are frozen before physical tests?"
                ),

            "resource_component_in_phase13":
                True,

            "closed_loop_safety_component_deferred_to_phase14":
                True,

            "onboard_resource_constraints_instantiated":
                False,

            "fallback_thresholds_frozen":
                False,

            "resource_answer_available":
                gate.rq4_resource_answer_available,

            "closed_loop_safety_evidence_assumed":
                gate.phase14_closed_loop_safety_evidence_assumed,
        },

        "execution_gate": {
            "measurement_policy_complete":
                False,

            "measurement_environment_frozen":
                False,

            "resource_measurement_execution_authorized":
                gate.resource_measurement_execution_authorized,

            "resource_claim_authorized":
                gate.resource_claim_authorized,

            "resource_measurement_executed":
                False,

            "empirical_resource_evidence_complete":
                False,
        },

        "protected_scientific_boundaries": {
            "phase12_attack_results_assumed":
                False,

            "phase14_closed_loop_safety_results_assumed":
                False,

            "validation_data_opened":
                gate.validation_data_opened,

            "confirmation_data_used":
                gate.confirmation_data_used,

            "ate_rpe_computation_authorized":
                False,

            "final_scoring_authorized":
                False,
        },

        "source_bindings": {
            "phase12_freeze_sha256":
                phase12_freeze_sha256,

            "master_context_sha256":
                master_context_sha256,

            "phase_plan_sha256":
                phase_plan_sha256,

            "frontier_report_sha256":
                frontier_report_sha256,

            "frontier_json_sha256":
                frontier_json_sha256,

            "basis_report_sha256":
                basis_report_sha256,

            "basis_json_sha256":
                basis_json_sha256,

            "historical_runtime_resource_protocol_sha256":
                runtime_protocol_sha256,

            "historical_runtime_integration_sha256":
                runtime_integration_sha256,

            "embedded_evidence_ledger_sha256":
                embedded_ledger_sha256,

            "embedded_reference_path_sha256":
                embedded_reference_sha256,

            "portable_c_contract_sha256":
                portable_c_sha256,

            "embedded_build_blocker_sha256":
                build_blocker_sha256,

            "paper_claim_matrix_sha256":
                paper_matrix_sha256,

            "historical_project_config_sha256":
                project_config_sha256,

            "historical_resource_benchmark_sha256":
                historical_benchmark_sha256,

            "historical_resource_protocol_builder_sha256":
                historical_builder_sha256,
        },
    }


def validate_contract_manifest(
    payload: Mapping[str, Any],
) -> None:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise ResourceEvaluationContractError(
            "Phase-13 contract must be a mapping"
        )

    if payload.get(
        "schema"
    ) != SCHEMA:
        raise ResourceEvaluationContractError(
            "unexpected Phase-13 schema"
        )

    if payload[
        "lifecycle_status"
    ] != (
        Phase13Lifecycle
        .CONTRACT_IMPLEMENTED_MEASUREMENT_POLICY_UNSELECTED
        .value
    ):
        raise ResourceEvaluationContractError(
            "unexpected Phase-13 lifecycle"
        )

    scope = payload[
        "phase_scope"
    ]

    if scope[
        "phase"
    ] != 13:
        raise ResourceEvaluationContractError(
            "unexpected phase"
        )

    if scope[
        "name"
    ] != "resource_evaluation":
        raise ResourceEvaluationContractError(
            "unexpected Phase-13 scope"
        )

    family = payload[
        "evaluation_family_boundary"
    ]

    if family[
        "resource_evidence_is_separate_evaluation_family"
    ] is not True:
        raise ResourceEvaluationContractError(
            "resource evidence must remain a separate evaluation family"
        )

    if family[
        "may_be_collapsed_into_undocumented_aggregate_score"
    ] is not False:
        raise ResourceEvaluationContractError(
            "resource evidence may not be collapsed into an undocumented score"
        )

    views = payload[
        "cost_views"
    ]

    if views[
        "required"
    ] != list(
        COST_VIEWS
    ):
        raise ResourceEvaluationContractError(
            "authoritative resource cost views changed"
        )

    if views[
        "required_count"
    ] != 2:
        raise ResourceEvaluationContractError(
            "unexpected resource cost-view count"
        )

    if views[
        "complete_system_cost_measurement_available"
    ] is not False:
        raise ResourceEvaluationContractError(
            "complete-system measurement is not yet available"
        )

    if views[
        "incremental_trust_layer_overhead_measurement_available"
    ] is not False:
        raise ResourceEvaluationContractError(
            "incremental trust-layer measurement is not yet available"
        )

    evidence = payload[
        "resource_evidence_schema"
    ]

    if evidence[
        "required_families"
    ] != list(
        RESOURCE_EVIDENCE_FAMILIES
    ):
        raise ResourceEvaluationContractError(
            "authoritative resource evidence family changed"
        )

    if evidence[
        "required_family_count"
    ] != 10:
        raise ResourceEvaluationContractError(
            "unexpected resource evidence family count"
        )

    if evidence[
        "families_are_measurement_results"
    ] is not False:
        raise ResourceEvaluationContractError(
            "required evidence names cannot be treated as measured results"
        )

    if evidence[
        "families_define_required_future_evidence"
    ] is not True:
        raise ResourceEvaluationContractError(
            "future evidence requirement lost"
        )

    metadata = payload[
        "measurement_metadata_schema"
    ]

    if metadata[
        "required_fields"
    ] != list(
        REQUIRED_MEASUREMENT_METADATA
    ):
        raise ResourceEvaluationContractError(
            "required measurement metadata changed"
        )

    if metadata[
        "required_field_count"
    ] != 7:
        raise ResourceEvaluationContractError(
            "unexpected measurement metadata field count"
        )

    if metadata[
        "values_currently_frozen"
    ] is not False:
        raise ResourceEvaluationContractError(
            "measurement metadata values are not frozen"
        )

    policy = payload[
        "measurement_policy_boundary"
    ]

    value_keys = (
        "exact_latency_definition",
        "timing_clock_source",
        "deadline_definition",
        "throughput_definition",
        "processor_utilization_measurement",
        "peak_memory_measurement",
        "storage_scope",
        "power_measurement_method",
        "energy_measurement_method",
        "energy_unit_scope_update_vs_trajectory",
        "measurement_scope_boundaries",
        "warmup_policy",
        "repetition_policy",
        "aggregation_policy",
        "cpu_specific_metric",
        "gpu_specific_metric",
        "real_time_acceptance_threshold",
    )

    for key in value_keys:
        if policy[
            key
        ] is not None:
            raise ResourceEvaluationContractError(
                f"{key} was selected unexpectedly"
            )

    for key, value in policy.items():
        if key.endswith(
            "_selected"
        ) and value is not False:
            raise ResourceEvaluationContractError(
                f"{key} must remain false"
            )

    environment = payload[
        "measurement_environment_boundary"
    ]

    for key, value in environment.items():
        if key.endswith(
            "_frozen"
        ):
            if value is not False:
                raise ResourceEvaluationContractError(
                    f"{key} must remain false"
                )
        elif value is not None:
            raise ResourceEvaluationContractError(
                f"{key} must remain unselected"
            )

    reuse = payload[
        "historical_resource_reuse_boundary"
    ]

    if reuse[
        "historical_protocol_exists"
    ] is not True:
        raise ResourceEvaluationContractError(
            "historical protocol inventory lost"
        )

    if reuse[
        "historical_protocol_identity"
    ] != "RUNTIME_RESOURCE_OVERHEAD_PROTOCOL_V1":
        raise ResourceEvaluationContractError(
            "historical protocol identity changed"
        )

    if reuse[
        "legacy_instrumentation_may_inform_future_engineering_implementation_only_after_explicit_phase13_binding"
    ] is not True:
        raise ResourceEvaluationContractError(
            "explicit future binding requirement lost"
        )

    for key, value in reuse.items():
        if key in {
            "historical_protocol_exists",
            "historical_protocol_identity",
            "legacy_instrumentation_may_inform_future_engineering_implementation_only_after_explicit_phase13_binding",
        }:
            continue

        if value is not False:
            raise ResourceEvaluationContractError(
                f"{key} must remain false"
            )

    platform = payload[
        "platform_claim_boundary"
    ]

    true_keys = {
        "target_specific_resource_claim_requires_target_specific_measurement",
        "onboard_robot_resource_claim_requires_onboard_robot_measurement",
    }

    for key, value in platform.items():
        if key in true_keys:
            if value is not True:
                raise ResourceEvaluationContractError(
                    f"{key} must remain true"
                )
        elif value is not False:
            raise ResourceEvaluationContractError(
                f"{key} must remain false"
            )

    rq4 = payload[
        "rq4_boundary"
    ]

    if rq4[
        "resource_component_in_phase13"
    ] is not True:
        raise ResourceEvaluationContractError(
            "RQ4 resource boundary lost"
        )

    if rq4[
        "closed_loop_safety_component_deferred_to_phase14"
    ] is not True:
        raise ResourceEvaluationContractError(
            "Phase-14 safety separation lost"
        )

    for key in (
        "onboard_resource_constraints_instantiated",
        "fallback_thresholds_frozen",
        "resource_answer_available",
        "closed_loop_safety_evidence_assumed",
    ):
        if rq4[
            key
        ] is not False:
            raise ResourceEvaluationContractError(
                f"{key} must remain false"
            )

    if set(
        payload[
            "execution_gate"
        ].values()
    ) != {
        False,
    }:
        raise ResourceEvaluationContractError(
            "Phase-13 execution gate must remain closed"
        )

    if set(
        payload[
            "protected_scientific_boundaries"
        ].values()
    ) != {
        False,
    }:
        raise ResourceEvaluationContractError(
            "protected Phase-13 scientific boundary changed"
        )
