"""TRUST-ROBOT Phase-8 factor-conditioning software contract.

Authoritative conceptual equations:

    w_m(t) = p_H_m(t) + alpha_m * p_D_m(t)

    lambda_m = clip(w_m * q_m, epsilon_m, 1)

The project states that alpha_m is selected on validation data.

Current standardized innovation provides the separate bounded short-horizon
conditioning pathway q_m.

The persistent health pathway and current-innovation pathway must remain
scientifically distinguishable.

This module freezes those interfaces and equations only.

It does NOT select alpha_m, epsilon_m, a standardized-innovation definition,
q_m, a factor scale, an information scaling operation, or covariance inflation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


SCHEMA = (
    "TRUST_ROBOT_PHASE8_FACTOR_CONDITIONING_CONTRACT_V1"
)

HEALTH_WEIGHT_FORMULA = (
    "w_m(t) = p_H_m(t) + alpha_m * p_D_m(t)"
)

FINAL_FACTOR_SCALE_FORMULA = (
    "lambda_m = clip(w_m * q_m, epsilon_m, 1)"
)


class FactorConditioningContractError(ValueError):
    """Raised when the Phase-8 scientific contract is violated."""


class FactorConditioningLifecycle(str, Enum):
    CONTRACT_IMPLEMENTED_INPUTS_UNAVAILABLE = (
        "contract_implemented_inputs_unavailable"
    )


class FactorConditioningPathway(str, Enum):
    PERSISTENT_HEALTH = "persistent_health"
    CURRENT_INNOVATION = "current_innovation"


PATHWAYS = tuple(
    FactorConditioningPathway
)


@dataclass(frozen=True)
class CurrentFactorConditioningGate:
    health_probability_input_available: bool = False

    calibrated_health_probability_input_available: bool = False

    alpha_selected: bool = False

    standardized_innovation_definition_selected: bool = False

    q_definition_selected: bool = False

    q_value_available: bool = False

    epsilon_selected: bool = False

    phase7_numeric_auxiliary_evidence_available: bool = False

    factor_scale_execution_authorized: bool = False

    information_rescaling_authorized: bool = False

    covariance_inflation_authorized: bool = False

    validation_data_opened: bool = False

    confirmation_data_used: bool = False

    def __post_init__(self) -> None:
        for field_name in self.__dataclass_fields__:
            if getattr(
                self,
                field_name,
            ) is not False:
                raise FactorConditioningContractError(
                    f"{field_name} must remain false in the "
                    "current Phase-8 evidence state"
                )


CURRENT_FACTOR_CONDITIONING_GATE = (
    CurrentFactorConditioningGate()
)


def pathway_names() -> tuple[str, ...]:
    return tuple(
        item.value
        for item in PATHWAYS
    )


def assert_factor_scale_execution_authorized(
    gate: CurrentFactorConditioningGate = (
        CURRENT_FACTOR_CONDITIONING_GATE
    ),
) -> None:
    if gate.factor_scale_execution_authorized is not True:
        raise FactorConditioningContractError(
            "Phase-8 factor-scale execution is not authorized: "
            "required calibrated health and innovation-conditioning "
            "inputs/parameters remain unavailable or unselected"
        )


def assert_information_rescaling_authorized(
    gate: CurrentFactorConditioningGate = (
        CURRENT_FACTOR_CONDITIONING_GATE
    ),
) -> None:
    if gate.information_rescaling_authorized is not True:
        raise FactorConditioningContractError(
            "factor-information rescaling is not authorized by the "
            "current Phase-8 evidence state"
        )


def assert_covariance_inflation_authorized(
    gate: CurrentFactorConditioningGate = (
        CURRENT_FACTOR_CONDITIONING_GATE
    ),
) -> None:
    if gate.covariance_inflation_authorized is not True:
        raise FactorConditioningContractError(
            "factor covariance inflation is not authorized by the "
            "current Phase-8 evidence state"
        )


def build_contract_manifest(
    *,
    phase7_freeze_sha256: str,
    phase6_freeze_sha256: str,
    phase5_freeze_sha256: str,
    health_model_config_sha256: str,
    calibration_config_sha256: str,
    master_context_sha256: str,
    phase_plan_sha256: str,
    frontier_report_sha256: str,
    frontier_json_sha256: str,
) -> dict[str, Any]:
    gate = CURRENT_FACTOR_CONDITIONING_GATE

    return {
        "schema":
            SCHEMA,

        "lifecycle_status":
            FactorConditioningLifecycle
            .CONTRACT_IMPLEMENTED_INPUTS_UNAVAILABLE
            .value,

        "phase_scope": {
            "phase":
                8,

            "name":
                "factor_conditioning",

            "purpose":
                (
                    "health_aware_factor_weighting_with_"
                    "bounded_innovation_conditioning"
                ),

            "phase9_suppression_recovery_status_in_scope":
                False,

            "historical_reliability_weighting_adopted":
                False,
        },

        "authoritative_equations": {
            "health_weight":
                HEALTH_WEIGHT_FORMULA,

            "final_factor_scale":
                FINAL_FACTOR_SCALE_FORMULA,

            "health_weight_equation_is_conceptual":
                True,

            "factor_scale_equation_is_conceptual":
                True,

            "numeric_execution_authorized":
                False,
        },

        "pathway_separation": {
            "pathways":
                list(
                    pathway_names()
                ),

            "persistent_health_pathway_distinct":
                True,

            "current_innovation_pathway_distinct":
                True,

            "collapse_to_single_unexplained_reliability_score_allowed":
                False,
        },

        "persistent_health_pathway": {
            "requires_health_probabilities":
                True,

            "requires_calibrated_health_probabilities_for_runtime":
                True,

            "health_probability_input_available":
                gate.health_probability_input_available,

            "calibrated_health_probability_input_available":
                gate.calibrated_health_probability_input_available,

            "healthy_probability_symbol":
                "p_H_m(t)",

            "degraded_probability_symbol":
                "p_D_m(t)",

            "alpha_symbol":
                "alpha_m",

            "alpha_selection_partition":
                "validation",

            "alpha_value":
                None,

            "alpha_selected":
                gate.alpha_selected,

            "health_weight_value_available":
                False,

            "default_alpha_created":
                False,
        },

        "current_innovation_pathway": {
            "standardized_innovation_named_by_project":
                True,

            "role":
                "bounded_short_horizon_factor_conditioning",

            "q_symbol":
                "q_m",

            "standardized_innovation_definition":
                "unselected",

            "standardized_innovation_definition_selected":
                gate.standardized_innovation_definition_selected,

            "q_definition":
                "unselected",

            "q_definition_selected":
                gate.q_definition_selected,

            "q_value":
                None,

            "q_value_available":
                gate.q_value_available,

            "default_q_created":
                False,
        },

        "factor_scale": {
            "lambda_symbol":
                "lambda_m",

            "epsilon_symbol":
                "epsilon_m",

            "epsilon_selection_policy":
                "unselected",

            "epsilon_value":
                None,

            "epsilon_selected":
                gate.epsilon_selected,

            "upper_clip_bound_from_authoritative_equation":
                1,

            "factor_scale_value_available":
                False,

            "factor_scale_execution_authorized":
                gate.factor_scale_execution_authorized,

            "default_epsilon_created":
                False,
        },

        "estimator_conditioning_semantics": {
            "factor_information_rescaling_named_by_project":
                True,

            "equivalent_covariance_inflation_named_by_project":
                True,

            "information_rescaling_authorized":
                gate.information_rescaling_authorized,

            "covariance_inflation_authorized":
                gate.covariance_inflation_authorized,

            "information_rescaling_implemented":
                False,

            "covariance_inflation_implemented":
                False,

            "estimator_factor_modified":
                False,
        },

        "upstream_evidence_gate": {
            "phase5_empirical_health_model_complete":
                False,

            "phase6_empirical_probability_calibration_complete":
                False,

            "phase7_numeric_auxiliary_evidence_available":
                gate.phase7_numeric_auxiliary_evidence_available,

            "runtime_health_probabilities_available":
                False,

            "runtime_calibrated_health_probabilities_available":
                False,
        },

        "selection_boundary": {
            "alpha_selected_on_validation":
                False,

            "epsilon_selection_policy_selected":
                False,

            "q_definition_selected":
                False,

            "standardized_innovation_definition_selected":
                False,

            "validation_data_opened":
                gate.validation_data_opened,

            "confirmation_data_used":
                gate.confirmation_data_used,

            "confirmation_may_select_alpha":
                False,

            "confirmation_may_select_epsilon":
                False,

            "confirmation_may_select_q_definition":
                False,
        },

        "phase9_boundary": {
            "suppression_threshold_selected":
                False,

            "recovery_threshold_selected":
                False,

            "fallback_threshold_selected":
                False,

            "hysteresis_implemented":
                False,

            "modality_suppression_implemented":
                False,

            "modality_recovery_implemented":
                False,

            "estimator_status_logic_implemented":
                False,
        },

        "scientific_boundary": {
            "health_state_threshold_selected":
                False,

            "source_attribution_performed":
                False,

            "new_sync_parameter_selected":
                False,

            "new_transform_selected":
                False,

            "new_interpolation_rule_selected":
                False,

            "ate_rpe_computation_authorized":
                False,

            "final_scoring_authorized":
                False,
        },

        "runtime_output": {
            "health_weight_output":
                "disabled",

            "innovation_conditioning_output":
                "disabled",

            "factor_scale_output":
                "disabled",

            "information_rescaling_output":
                "disabled",

            "covariance_inflation_output":
                "disabled",
        },

        "source_bindings": {
            "phase7_freeze_sha256":
                phase7_freeze_sha256,

            "phase6_freeze_sha256":
                phase6_freeze_sha256,

            "phase5_freeze_sha256":
                phase5_freeze_sha256,

            "health_model_config_sha256":
                health_model_config_sha256,

            "calibration_config_sha256":
                calibration_config_sha256,

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
        raise FactorConditioningContractError(
            "Phase-8 contract must be a mapping"
        )

    if payload.get(
        "schema"
    ) != SCHEMA:
        raise FactorConditioningContractError(
            "unexpected Phase-8 schema"
        )

    if payload[
        "lifecycle_status"
    ] != (
        FactorConditioningLifecycle
        .CONTRACT_IMPLEMENTED_INPUTS_UNAVAILABLE
        .value
    ):
        raise FactorConditioningContractError(
            "unexpected Phase-8 lifecycle"
        )

    scope = payload[
        "phase_scope"
    ]

    if scope[
        "phase"
    ] != 8:
        raise FactorConditioningContractError(
            "unexpected Phase-8 phase number"
        )

    if scope[
        "phase9_suppression_recovery_status_in_scope"
    ] is not False:
        raise FactorConditioningContractError(
            "Phase-9 behavior leaked into Phase 8"
        )

    equations = payload[
        "authoritative_equations"
    ]

    if equations[
        "health_weight"
    ] != HEALTH_WEIGHT_FORMULA:
        raise FactorConditioningContractError(
            "health-weight equation changed"
        )

    if equations[
        "final_factor_scale"
    ] != FINAL_FACTOR_SCALE_FORMULA:
        raise FactorConditioningContractError(
            "factor-scale equation changed"
        )

    if equations[
        "numeric_execution_authorized"
    ] is not False:
        raise FactorConditioningContractError(
            "numeric factor conditioning unexpectedly authorized"
        )

    separation = payload[
        "pathway_separation"
    ]

    if separation[
        "pathways"
    ] != list(
        pathway_names()
    ):
        raise FactorConditioningContractError(
            "Phase-8 pathway inventory changed"
        )

    if separation[
        "persistent_health_pathway_distinct"
    ] is not True:
        raise FactorConditioningContractError(
            "persistent-health pathway separation lost"
        )

    if separation[
        "current_innovation_pathway_distinct"
    ] is not True:
        raise FactorConditioningContractError(
            "current-innovation pathway separation lost"
        )

    if separation[
        "collapse_to_single_unexplained_reliability_score_allowed"
    ] is not False:
        raise FactorConditioningContractError(
            "unexplained reliability-score collapse was enabled"
        )

    health = payload[
        "persistent_health_pathway"
    ]

    if health[
        "alpha_selection_partition"
    ] != "validation":
        raise FactorConditioningContractError(
            "alpha_m must remain validation-selected"
        )

    if health[
        "alpha_value"
    ] is not None:
        raise FactorConditioningContractError(
            "alpha_m was selected unexpectedly"
        )

    if health[
        "alpha_selected"
    ] is not False:
        raise FactorConditioningContractError(
            "alpha_m selection must remain false"
        )

    if health[
        "default_alpha_created"
    ] is not False:
        raise FactorConditioningContractError(
            "default alpha_m is forbidden"
        )

    innovation = payload[
        "current_innovation_pathway"
    ]

    if innovation[
        "standardized_innovation_definition"
    ] != "unselected":
        raise FactorConditioningContractError(
            "standardized innovation was selected unexpectedly"
        )

    if innovation[
        "q_definition"
    ] != "unselected":
        raise FactorConditioningContractError(
            "q_m definition was selected unexpectedly"
        )

    if innovation[
        "q_value"
    ] is not None:
        raise FactorConditioningContractError(
            "q_m value was created unexpectedly"
        )

    if innovation[
        "default_q_created"
    ] is not False:
        raise FactorConditioningContractError(
            "default q_m is forbidden"
        )

    scale = payload[
        "factor_scale"
    ]

    if scale[
        "epsilon_selection_policy"
    ] != "unselected":
        raise FactorConditioningContractError(
            "epsilon selection policy was invented"
        )

    if scale[
        "epsilon_value"
    ] is not None:
        raise FactorConditioningContractError(
            "epsilon_m was selected unexpectedly"
        )

    if scale[
        "epsilon_selected"
    ] is not False:
        raise FactorConditioningContractError(
            "epsilon_m selection must remain false"
        )

    if scale[
        "upper_clip_bound_from_authoritative_equation"
    ] != 1:
        raise FactorConditioningContractError(
            "authoritative upper clip bound changed"
        )

    if scale[
        "factor_scale_execution_authorized"
    ] is not False:
        raise FactorConditioningContractError(
            "factor-scale execution must remain disabled"
        )

    estimator = payload[
        "estimator_conditioning_semantics"
    ]

    for key in (
        "information_rescaling_authorized",
        "covariance_inflation_authorized",
        "information_rescaling_implemented",
        "covariance_inflation_implemented",
        "estimator_factor_modified",
    ):
        if estimator[
            key
        ] is not False:
            raise FactorConditioningContractError(
                f"{key} must remain false"
            )

    upstream = payload[
        "upstream_evidence_gate"
    ]

    if set(
        upstream.values()
    ) != {
        False,
    }:
        raise FactorConditioningContractError(
            "Phase-8 upstream evidence gate must remain closed"
        )

    phase9 = payload[
        "phase9_boundary"
    ]

    if set(
        phase9.values()
    ) != {
        False,
    }:
        raise FactorConditioningContractError(
            "Phase-9 policy leaked into Phase 8"
        )

    scientific = payload[
        "scientific_boundary"
    ]

    if set(
        scientific.values()
    ) != {
        False,
    }:
        raise FactorConditioningContractError(
            "Phase-8 protected scientific boundary changed"
        )

    runtime = payload[
        "runtime_output"
    ]

    if set(
        runtime.values()
    ) != {
        "disabled",
    }:
        raise FactorConditioningContractError(
            "Phase-8 runtime outputs must remain disabled"
        )
