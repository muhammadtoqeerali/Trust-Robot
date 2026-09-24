"""TRUST-ROBOT Phase-9 suppression/recovery/status contract.

Authoritative Phase-9 semantics:

- hard modality suppression must not be a single-frame arbitrary decision;
- hysteresis uses:
    * an unusable-probability entry threshold;
    * a consecutive-window entry requirement;
    * a lower recovery threshold;
    * a consecutive-window recovery requirement;
- before suppressing a modality, remaining factor support must be assessed;
- when remaining support is insufficient, report a degraded or unavailable
  estimator state instead of forcing a nominal estimate;
- no unsupported observability guarantee may be claimed.

This module freezes the architecture only.

It does not select numerical thresholds, window counts, support sufficiency
criteria, observability tests, degraded-versus-unavailable rules, timeouts,
fallback policies, or any runtime suppression/recovery decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


SCHEMA = (
    "TRUST_ROBOT_PHASE9_SUPPRESSION_RECOVERY_STATUS_CONTRACT_V1"
)


class SuppressionRecoveryContractError(ValueError):
    """Raised when the Phase-9 scientific contract is violated."""


class SuppressionRecoveryLifecycle(str, Enum):
    CONTRACT_IMPLEMENTED_PARAMETERS_UNSELECTED = (
        "contract_implemented_parameters_unselected"
    )


class InsufficientSupportReport(str, Enum):
    DEGRADED_ESTIMATOR_STATE = (
        "degraded_estimator_state"
    )

    UNAVAILABLE_ESTIMATOR_STATE = (
        "unavailable_estimator_state"
    )


INSUFFICIENT_SUPPORT_REPORT_OPTIONS = tuple(
    InsufficientSupportReport
)


@dataclass(frozen=True)
class CurrentSuppressionRecoveryGate:
    unusable_probability_input_available: bool = False

    suppression_entry_threshold_selected: bool = False
    suppression_entry_window_count_selected: bool = False

    recovery_threshold_selected: bool = False
    recovery_window_count_selected: bool = False

    remaining_factor_support_definition_selected: bool = False
    remaining_factor_support_assessment_available: bool = False

    degraded_vs_unavailable_rule_selected: bool = False

    suppression_execution_authorized: bool = False
    recovery_execution_authorized: bool = False
    runtime_status_execution_authorized: bool = False

    fallback_policy_selected: bool = False
    fallback_execution_authorized: bool = False

    validation_data_opened: bool = False
    confirmation_data_used: bool = False

    def __post_init__(self) -> None:
        for field_name in self.__dataclass_fields__:
            if getattr(
                self,
                field_name,
            ) is not False:
                raise SuppressionRecoveryContractError(
                    f"{field_name} must remain false in the "
                    "current Phase-9 evidence state"
                )


CURRENT_SUPPRESSION_RECOVERY_GATE = (
    CurrentSuppressionRecoveryGate()
)


def insufficient_support_report_names() -> tuple[str, ...]:
    return tuple(
        item.value
        for item in INSUFFICIENT_SUPPORT_REPORT_OPTIONS
    )


def assert_suppression_execution_authorized(
    gate: CurrentSuppressionRecoveryGate = (
        CURRENT_SUPPRESSION_RECOVERY_GATE
    ),
) -> None:
    if gate.suppression_execution_authorized is not True:
        raise SuppressionRecoveryContractError(
            "Phase-9 hard suppression is not authorized: "
            "hysteresis parameters and remaining-support semantics "
            "remain unselected"
        )


def assert_recovery_execution_authorized(
    gate: CurrentSuppressionRecoveryGate = (
        CURRENT_SUPPRESSION_RECOVERY_GATE
    ),
) -> None:
    if gate.recovery_execution_authorized is not True:
        raise SuppressionRecoveryContractError(
            "Phase-9 recovery is not authorized: "
            "recovery threshold/window semantics remain unselected"
        )


def assert_runtime_status_execution_authorized(
    gate: CurrentSuppressionRecoveryGate = (
        CURRENT_SUPPRESSION_RECOVERY_GATE
    ),
) -> None:
    if gate.runtime_status_execution_authorized is not True:
        raise SuppressionRecoveryContractError(
            "Phase-9 estimator-status execution is not authorized: "
            "remaining-support and degraded-versus-unavailable rules "
            "remain unselected"
        )


def assert_fallback_execution_authorized(
    gate: CurrentSuppressionRecoveryGate = (
        CURRENT_SUPPRESSION_RECOVERY_GATE
    ),
) -> None:
    if gate.fallback_execution_authorized is not True:
        raise SuppressionRecoveryContractError(
            "fallback execution is not authorized by the current "
            "TRUST-ROBOT evidence state"
        )


def build_contract_manifest(
    *,
    phase8_freeze_sha256: str,
    phase7_freeze_sha256: str,
    phase6_freeze_sha256: str,
    phase5_freeze_sha256: str,
    phase5_health_semantics_sha256: str,
    phase8_factor_conditioning_config_sha256: str,
    master_context_sha256: str,
    phase_plan_sha256: str,
    frontier_report_sha256: str,
    frontier_json_sha256: str,
) -> dict[str, Any]:
    gate = CURRENT_SUPPRESSION_RECOVERY_GATE

    return {
        "schema":
            SCHEMA,

        "lifecycle_status":
            SuppressionRecoveryLifecycle
            .CONTRACT_IMPLEMENTED_PARAMETERS_UNSELECTED
            .value,

        "phase_scope": {
            "phase":
                9,

            "name":
                "suppression_recovery_status",

            "purpose":
                "hysteretic_modality_availability_and_estimator_status",

            "hard_suppression_in_scope":
                True,

            "recovery_in_scope":
                True,

            "estimator_support_status_in_scope":
                True,

            "fallback_policy_defined_by_authoritative_phase9_section":
                False,
        },

        "hysteresis_architecture": {
            "single_frame_hard_suppression_allowed":
                False,

            "entry_signal":
                "unusable_probability",

            "entry_threshold_value":
                None,

            "entry_threshold_selected":
                gate.suppression_entry_threshold_selected,

            "entry_consecutive_window_count":
                None,

            "entry_consecutive_window_count_selected":
                gate.suppression_entry_window_count_selected,

            "recovery_threshold_relation_to_entry":
                "lower",

            "recovery_threshold_value":
                None,

            "recovery_threshold_selected":
                gate.recovery_threshold_selected,

            "recovery_consecutive_window_count":
                None,

            "recovery_consecutive_window_count_selected":
                gate.recovery_window_count_selected,

            "hysteresis_numeric_execution_authorized":
                False,

            "default_threshold_created":
                False,

            "default_window_count_created":
                False,
        },

        "remaining_factor_support": {
            "assessment_required_before_hard_suppression":
                True,

            "assessment_definition":
                "unselected",

            "assessment_definition_selected":
                gate.remaining_factor_support_definition_selected,

            "assessment_available":
                gate.remaining_factor_support_assessment_available,

            "minimum_active_modality_count":
                None,

            "minimum_active_modality_count_selected":
                False,

            "observability_test":
                "unselected",

            "observability_test_selected":
                False,

            "unsupported_observability_guarantee_allowed":
                False,
        },

        "insufficient_support_reporting": {
            "required_reporting_options":
                list(
                    insufficient_support_report_names()
                ),

            "degraded_vs_unavailable_rule":
                "unselected",

            "degraded_vs_unavailable_rule_selected":
                gate.degraded_vs_unavailable_rule_selected,

            "nominal_estimate_may_be_forced_when_support_insufficient":
                False,

            "runtime_status_execution_authorized":
                gate.runtime_status_execution_authorized,

            "runtime_status_output":
                "disabled",
        },

        "execution_gate": {
            "unusable_probability_input_available":
                gate.unusable_probability_input_available,

            "phase8_numeric_factor_scale_available":
                False,

            "suppression_execution_authorized":
                gate.suppression_execution_authorized,

            "recovery_execution_authorized":
                gate.recovery_execution_authorized,

            "runtime_status_execution_authorized":
                gate.runtime_status_execution_authorized,

            "hard_suppression_performed":
                False,

            "recovery_performed":
                False,
        },

        "health_availability_separation": {
            "phase5_health_state_is_suppression_command":
                False,

            "availability_is_health_label":
                False,

            "missing_measurement_is_health_state":
                False,

            "suppression_action_requires_phase9_policy":
                True,
        },

        "fallback_boundary": {
            "fallback_appears_in_broader_project_safety_context":
                True,

            "fallback_defined_by_authoritative_phase9_section":
                False,

            "fallback_policy":
                "unselected",

            "fallback_policy_selected":
                gate.fallback_policy_selected,

            "fallback_threshold":
                None,

            "fallback_threshold_selected":
                False,

            "fallback_execution_authorized":
                gate.fallback_execution_authorized,

            "fallback_executed":
                False,
        },

        "selection_boundary": {
            "suppression_entry_threshold_selected":
                False,

            "suppression_entry_window_count_selected":
                False,

            "recovery_threshold_selected":
                False,

            "recovery_window_count_selected":
                False,

            "remaining_support_definition_selected":
                False,

            "degraded_vs_unavailable_rule_selected":
                False,

            "validation_data_opened":
                gate.validation_data_opened,

            "confirmation_data_used":
                gate.confirmation_data_used,

            "confirmation_may_select_suppression_threshold":
                False,

            "confirmation_may_select_recovery_threshold":
                False,

            "confirmation_may_select_window_counts":
                False,

            "confirmation_may_select_support_rule":
                False,
        },

        "protected_scientific_boundaries": {
            "phase8_numeric_factor_scale_assumed":
                False,

            "unsupported_observability_guarantee_claimed":
                False,

            "nominal_estimate_forced_under_insufficient_support":
                False,

            "fallback_policy_invented":
                False,

            "timeout_selected":
                False,

            "new_sync_parameter_selected":
                False,

            "new_transform_selected":
                False,

            "ate_rpe_computation_authorized":
                False,

            "final_scoring_authorized":
                False,
        },

        "runtime_outputs": {
            "modality_suppression_output":
                "disabled",

            "modality_recovery_output":
                "disabled",

            "estimator_support_status_output":
                "disabled",

            "fallback_output":
                "disabled",
        },

        "source_bindings": {
            "phase8_freeze_sha256":
                phase8_freeze_sha256,

            "phase7_freeze_sha256":
                phase7_freeze_sha256,

            "phase6_freeze_sha256":
                phase6_freeze_sha256,

            "phase5_freeze_sha256":
                phase5_freeze_sha256,

            "phase5_health_semantics_sha256":
                phase5_health_semantics_sha256,

            "phase8_factor_conditioning_config_sha256":
                phase8_factor_conditioning_config_sha256,

            "master_context_sha256":
                master_context_sha256,

            "phase_plan_sha256":
                phase_plan_sha256,

            "frontier_report_sha256":
                frontier_report_sha256,

            "frontier_json_sha256":
                frontier_json_sha256,
        },
    }


def validate_contract_manifest(
    payload: Mapping[str, Any],
) -> None:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise SuppressionRecoveryContractError(
            "Phase-9 contract must be a mapping"
        )

    if payload.get(
        "schema"
    ) != SCHEMA:
        raise SuppressionRecoveryContractError(
            "unexpected Phase-9 schema"
        )

    if payload[
        "lifecycle_status"
    ] != (
        SuppressionRecoveryLifecycle
        .CONTRACT_IMPLEMENTED_PARAMETERS_UNSELECTED
        .value
    ):
        raise SuppressionRecoveryContractError(
            "unexpected Phase-9 lifecycle"
        )

    scope = payload[
        "phase_scope"
    ]

    if scope[
        "phase"
    ] != 9:
        raise SuppressionRecoveryContractError(
            "unexpected Phase-9 phase"
        )

    if scope[
        "fallback_policy_defined_by_authoritative_phase9_section"
    ] is not False:
        raise SuppressionRecoveryContractError(
            "fallback was incorrectly invented into the Phase-9 section"
        )

    hysteresis = payload[
        "hysteresis_architecture"
    ]

    if hysteresis[
        "single_frame_hard_suppression_allowed"
    ] is not False:
        raise SuppressionRecoveryContractError(
            "single-frame hard suppression is forbidden"
        )

    if hysteresis[
        "entry_signal"
    ] != "unusable_probability":
        raise SuppressionRecoveryContractError(
            "authoritative entry signal changed"
        )

    if hysteresis[
        "entry_threshold_value"
    ] is not None:
        raise SuppressionRecoveryContractError(
            "entry threshold was selected unexpectedly"
        )

    if hysteresis[
        "entry_consecutive_window_count"
    ] is not None:
        raise SuppressionRecoveryContractError(
            "entry window count was selected unexpectedly"
        )

    if hysteresis[
        "recovery_threshold_relation_to_entry"
    ] != "lower":
        raise SuppressionRecoveryContractError(
            "recovery hysteresis relation changed"
        )

    if hysteresis[
        "recovery_threshold_value"
    ] is not None:
        raise SuppressionRecoveryContractError(
            "recovery threshold was selected unexpectedly"
        )

    if hysteresis[
        "recovery_consecutive_window_count"
    ] is not None:
        raise SuppressionRecoveryContractError(
            "recovery window count was selected unexpectedly"
        )

    for key in (
        "entry_threshold_selected",
        "entry_consecutive_window_count_selected",
        "recovery_threshold_selected",
        "recovery_consecutive_window_count_selected",
        "hysteresis_numeric_execution_authorized",
        "default_threshold_created",
        "default_window_count_created",
    ):
        if hysteresis[
            key
        ] is not False:
            raise SuppressionRecoveryContractError(
                f"{key} must remain false"
            )

    support = payload[
        "remaining_factor_support"
    ]

    if support[
        "assessment_required_before_hard_suppression"
    ] is not True:
        raise SuppressionRecoveryContractError(
            "remaining support assessment must precede suppression"
        )

    if support[
        "assessment_definition"
    ] != "unselected":
        raise SuppressionRecoveryContractError(
            "remaining-support assessment was invented"
        )

    if support[
        "minimum_active_modality_count"
    ] is not None:
        raise SuppressionRecoveryContractError(
            "minimum modality count was invented"
        )

    if support[
        "observability_test"
    ] != "unselected":
        raise SuppressionRecoveryContractError(
            "observability test was invented"
        )

    if support[
        "unsupported_observability_guarantee_allowed"
    ] is not False:
        raise SuppressionRecoveryContractError(
            "unsupported observability guarantee enabled"
        )

    reporting = payload[
        "insufficient_support_reporting"
    ]

    if reporting[
        "required_reporting_options"
    ] != list(
        insufficient_support_report_names()
    ):
        raise SuppressionRecoveryContractError(
            "insufficient-support reporting options changed"
        )

    if reporting[
        "degraded_vs_unavailable_rule"
    ] != "unselected":
        raise SuppressionRecoveryContractError(
            "degraded/unavailable rule was invented"
        )

    if reporting[
        "degraded_vs_unavailable_rule_selected"
    ] is not False:
        raise SuppressionRecoveryContractError(
            "degraded/unavailable rule must remain unselected"
        )

    if reporting[
        "nominal_estimate_may_be_forced_when_support_insufficient"
    ] is not False:
        raise SuppressionRecoveryContractError(
            "nominal output cannot be forced under insufficient support"
        )

    if reporting[
        "runtime_status_execution_authorized"
    ] is not False:
        raise SuppressionRecoveryContractError(
            "runtime status execution must remain blocked"
        )

    execution = payload[
        "execution_gate"
    ]

    if set(
        execution.values()
    ) != {
        False,
    }:
        raise SuppressionRecoveryContractError(
            "Phase-9 execution gate must remain closed"
        )

    separation = payload[
        "health_availability_separation"
    ]

    if separation != {
        "phase5_health_state_is_suppression_command": False,
        "availability_is_health_label": False,
        "missing_measurement_is_health_state": False,
        "suppression_action_requires_phase9_policy": True,
    }:
        raise SuppressionRecoveryContractError(
            "health/availability/action separation changed"
        )

    fallback = payload[
        "fallback_boundary"
    ]

    if fallback[
        "fallback_policy"
    ] != "unselected":
        raise SuppressionRecoveryContractError(
            "fallback policy was invented"
        )

    if fallback[
        "fallback_threshold"
    ] is not None:
        raise SuppressionRecoveryContractError(
            "fallback threshold was invented"
        )

    for key in (
        "fallback_policy_selected",
        "fallback_threshold_selected",
        "fallback_execution_authorized",
        "fallback_executed",
    ):
        if fallback[
            key
        ] is not False:
            raise SuppressionRecoveryContractError(
                f"{key} must remain false"
            )

    protected = payload[
        "protected_scientific_boundaries"
    ]

    if set(
        protected.values()
    ) != {
        False,
    }:
        raise SuppressionRecoveryContractError(
            "Phase-9 protected scientific boundary changed"
        )

    runtime = payload[
        "runtime_outputs"
    ]

    if set(
        runtime.values()
    ) != {
        "disabled",
    }:
        raise SuppressionRecoveryContractError(
            "Phase-9 runtime outputs must remain disabled"
        )
