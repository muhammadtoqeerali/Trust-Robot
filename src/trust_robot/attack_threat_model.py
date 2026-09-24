"""TRUST-ROBOT Phase-12 explicit attack / threat-model contract.

Phase 12:
    Explicit attack evaluation.
    Threat-model-bounded RQ3 evidence.

This module binds the proposal-defined planned attack taxonomy and the
mandatory fields of any future attack protocol.

It does not instantiate a threat model or attack protocol. It does not choose
an attacker knowledge model, writable modality, writable field, duration,
budget, objective, protected source, identifiability assumption, attack
target, attack schedule, threshold, or execution condition.

Attack taxonomy identity is not attack execution authorization.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


SCHEMA = (
    "TRUST_ROBOT_PHASE12_THREAT_MODEL_CONTRACT_V1"
)

PLANNED_ATTACK_IDENTITIES = (
    "false-data injection / spoofing",
    "bounded adversarial image or point-cloud perturbation",
    "replay",
    "timestamp manipulation",
    "coordinated two-modality corruption",
    "adaptive white-box digital evasion",
)

REQUIRED_ATTACK_PROTOCOL_FIELDS = (
    "attacker knowledge",
    "writable modality/modalities",
    "writable fields",
    "attack duration",
    "magnitude/rate/norm budget",
    "objective",
    "protected-source assumptions",
    "identifiability assumptions",
)

RQ3_ATTACK_CLASSES = (
    "single_sensor",
    "coordinated",
    "adaptive",
)

NATIVE_PHASE3_FAMILIES = (
    "EVENT_GAP",
    "EVENT_REPEAT",
    "TIMESTAMP_STEP_SHIFT",
)

PHASE3_FUTURE_ATTACK_RELATED_CANDIDATES = (
    "lidar_geometric_perturbation",
    "replay",
    "calibration_perturbation",
    "threat_model_bounded_spoofing",
)


class ThreatModelContractError(ValueError):
    """Raised when the Phase-12 fail-closed contract is violated."""


class Phase12Lifecycle(str, Enum):
    CONTRACT_IMPLEMENTED_PROTOCOLS_UNINSTANTIATED = (
        "contract_implemented_protocols_uninstantiated"
    )


@dataclass(frozen=True)
class CurrentPhase12Gate:
    threat_model_selected: bool = False
    attacker_knowledge_model_selected: bool = False
    attack_goal_selected: bool = False

    writable_modalities_selected: bool = False
    writable_fields_selected: bool = False
    protected_source_assumptions_selected: bool = False
    identifiability_assumptions_selected: bool = False

    attack_family_selected: bool = False
    attack_target_pipeline_layer_selected: bool = False

    attack_duration_selected: bool = False
    attack_budget_selected: bool = False
    attack_magnitude_selected: bool = False
    attack_rate_selected: bool = False
    attack_norm_selected: bool = False
    attack_schedule_selected: bool = False
    attack_seed_schedule_selected: bool = False
    attack_threshold_selected: bool = False

    single_sensor_operational_definition_selected: bool = False
    coordinated_operational_definition_selected: bool = False
    adaptive_operational_definition_selected: bool = False

    phase3_corruption_reuse_authorized: bool = False
    phase10_controlled_fault_reuse_authorized: bool = False

    synthetic_attack_execution_authorized: bool = False
    physical_attack_execution_authorized: bool = False
    attack_evaluation_authorized: bool = False

    validation_data_opened: bool = False
    confirmation_data_used: bool = False

    def __post_init__(self) -> None:
        for field_name in self.__dataclass_fields__:
            if getattr(
                self,
                field_name,
            ) is not False:
                raise ThreatModelContractError(
                    f"{field_name} must remain false in the "
                    "current Phase-12 evidence state"
                )


CURRENT_PHASE12_GATE = CurrentPhase12Gate()


def planned_attack_identities() -> tuple[str, ...]:
    return PLANNED_ATTACK_IDENTITIES


def required_attack_protocol_fields() -> tuple[str, ...]:
    return REQUIRED_ATTACK_PROTOCOL_FIELDS


def rq3_attack_classes() -> tuple[str, ...]:
    return RQ3_ATTACK_CLASSES


def assert_synthetic_attack_execution_authorized(
    gate: CurrentPhase12Gate = CURRENT_PHASE12_GATE,
) -> None:
    if gate.synthetic_attack_execution_authorized is not True:
        raise ThreatModelContractError(
            "synthetic attack execution is not authorized: "
            "no complete explicit threat model has been frozen"
        )


def assert_physical_attack_execution_authorized(
    gate: CurrentPhase12Gate = CURRENT_PHASE12_GATE,
) -> None:
    if gate.physical_attack_execution_authorized is not True:
        raise ThreatModelContractError(
            "physical attack execution is not authorized"
        )


def assert_attack_evaluation_authorized(
    gate: CurrentPhase12Gate = CURRENT_PHASE12_GATE,
) -> None:
    if gate.attack_evaluation_authorized is not True:
        raise ThreatModelContractError(
            "attack evaluation is not authorized"
        )


def build_contract_manifest(
    *,
    phase11_freeze_sha256: str,
    master_context_sha256: str,
    phase_plan_sha256: str,
    frontier_report_sha256: str,
    frontier_json_sha256: str,
    basis_report_sha256: str,
    basis_json_sha256: str,
    phase3_freeze_sha256: str,
    phase3_taxonomy_sha256: str,
    phase3_selection_sha256: str,
    phase10_contract_sha256: str,
    phase10_freeze_sha256: str,
    data_protocol_sha256: str,
) -> dict[str, Any]:
    gate = CURRENT_PHASE12_GATE

    return {
        "schema":
            SCHEMA,

        "lifecycle_status":
            Phase12Lifecycle
            .CONTRACT_IMPLEMENTED_PROTOCOLS_UNINSTANTIATED
            .value,

        "phase_scope": {
            "phase":
                12,

            "name":
                "explicit_attack_evaluation",

            "evidence_role":
                "threat_model_bounded_RQ3_evidence",
        },

        "evidence_category_separation": {
            "fault_evaluation_separate_from_attack_evaluation":
                True,

            "environmental_nonattack_degradation_separate_from_attack_evaluation":
                True,

            "controlled_fault_truth_is_attack_truth":
                False,

            "synthetic_corruption_identity_is_attack_identity":
                False,
        },

        "planned_attack_taxonomy": {
            "identities":
                list(
                    planned_attack_identities()
                ),

            "identity_count":
                len(
                    PLANNED_ATTACK_IDENTITIES
                ),

            "taxonomy_is_selected_threat_model":
                False,

            "taxonomy_identity_is_executable_attack_protocol":
                False,

            "taxonomy_identity_is_empirical_attack_evidence":
                False,
        },

        "attack_protocol_schema": {
            "required_fields":
                list(
                    required_attack_protocol_fields()
                ),

            "required_field_count":
                len(
                    REQUIRED_ATTACK_PROTOCOL_FIELDS
                ),

            "instantiated_protocols":
                [],

            "instantiated_protocol_count":
                0,

            "complete_explicit_threat_model_required_before_execution":
                True,
        },

        "rq3_boundary": {
            "question":
                (
                    "Under explicitly stated identifiability assumptions, "
                    "does auxiliary cross-modal and kinematic/temporal "
                    "consistency improve handling of single-sensor, "
                    "coordinated, and adaptive attacks?"
                ),

            "attack_classes":
                list(
                    rq3_attack_classes()
                ),

            "identifiability_assumptions_required":
                True,

            "cross_modal_and_kinematic_temporal_consistency_named":
                True,

            "single_sensor_operational_definition_selected":
                gate.single_sensor_operational_definition_selected,

            "coordinated_operational_definition_selected":
                gate.coordinated_operational_definition_selected,

            "adaptive_operational_definition_selected":
                gate.adaptive_operational_definition_selected,

            "phase7_numeric_auxiliary_consistency_available":
                False,

            "rq3_executable":
                False,

            "rq3_answer_available":
                False,
        },

        "source_attribution_boundary": {
            "successful_source_attribution_may_be_claimed_without_sufficient_uncompromised_information":
                False,

            "sufficient_uncompromised_information_verified":
                False,

            "source_attribution_claim_authorized":
                False,
        },

        "selection_boundary": {
            "threat_model":
                None,

            "threat_model_selected":
                gate.threat_model_selected,

            "attacker_knowledge_model":
                None,

            "attacker_knowledge_model_selected":
                gate.attacker_knowledge_model_selected,

            "attack_goal":
                None,

            "attack_goal_selected":
                gate.attack_goal_selected,

            "writable_modalities":
                [],

            "writable_modalities_selected":
                gate.writable_modalities_selected,

            "writable_fields":
                [],

            "writable_fields_selected":
                gate.writable_fields_selected,

            "protected_source_assumptions":
                [],

            "protected_source_assumptions_selected":
                gate.protected_source_assumptions_selected,

            "identifiability_assumptions":
                [],

            "identifiability_assumptions_selected":
                gate.identifiability_assumptions_selected,

            "attack_family":
                None,

            "attack_family_selected":
                gate.attack_family_selected,

            "attack_target_pipeline_layer":
                None,

            "attack_target_pipeline_layer_selected":
                gate.attack_target_pipeline_layer_selected,
        },

        "attack_operating_point_boundary": {
            "attack_duration":
                None,

            "attack_duration_selected":
                gate.attack_duration_selected,

            "attack_budget":
                None,

            "attack_budget_selected":
                gate.attack_budget_selected,

            "attack_magnitude":
                None,

            "attack_magnitude_selected":
                gate.attack_magnitude_selected,

            "attack_rate":
                None,

            "attack_rate_selected":
                gate.attack_rate_selected,

            "attack_norm":
                None,

            "attack_norm_selected":
                gate.attack_norm_selected,

            "attack_schedule":
                None,

            "attack_schedule_selected":
                gate.attack_schedule_selected,

            "attack_seed_schedule":
                None,

            "attack_seed_schedule_selected":
                gate.attack_seed_schedule_selected,

            "attack_threshold":
                None,

            "attack_threshold_selected":
                gate.attack_threshold_selected,

            "budgets_and_thresholds_must_be_fixed_before_held_out_testing":
                True,

            "held_out_testing_may_select_attack_budget":
                False,

            "held_out_testing_may_select_attack_threshold":
                False,
        },

        "phase3_reuse_boundary": {
            "currently_frozen_native_families":
                list(
                    NATIVE_PHASE3_FAMILIES
                ),

            "future_attack_related_candidate_mechanisms_not_implemented":
                list(
                    PHASE3_FUTURE_ATTACK_RELATED_CANDIDATES
                ),

            "phase3_attack_context_requires_explicit_threat_model":
                True,

            "phase3_taxonomy_identity_is_phase12_protocol":
                False,

            "phase3_selection_policy_is_phase12_threat_model":
                False,

            "phase3_corruption_reuse_authorized":
                gate.phase3_corruption_reuse_authorized,

            "native_phase3_family_execution_authorized_for_phase12":
                False,
        },

        "phase10_reuse_boundary": {
            "phase10_controlled_fault_reuse_authorized":
                gate.phase10_controlled_fault_reuse_authorized,

            "phase10_fault_truth_is_phase12_attack_truth":
                False,

            "phase10_experiment_results_available":
                False,
        },

        "execution_gate": {
            "complete_threat_model_instantiated":
                False,

            "synthetic_attack_execution_authorized":
                gate.synthetic_attack_execution_authorized,

            "physical_attack_execution_authorized":
                gate.physical_attack_execution_authorized,

            "attack_evaluation_authorized":
                gate.attack_evaluation_authorized,

            "synthetic_attack_executed":
                False,

            "physical_attack_executed":
                False,

            "attack_evaluation_executed":
                False,
        },

        "protected_scientific_boundaries": {
            "attack_resilience_claim_authorized":
                False,

            "source_attribution_claim_authorized":
                False,

            "phase11_cross_dataset_evidence_assumed":
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
            "phase11_freeze_sha256":
                phase11_freeze_sha256,

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

            "phase3_freeze_sha256":
                phase3_freeze_sha256,

            "phase3_taxonomy_sha256":
                phase3_taxonomy_sha256,

            "phase3_selection_sha256":
                phase3_selection_sha256,

            "phase10_contract_sha256":
                phase10_contract_sha256,

            "phase10_freeze_sha256":
                phase10_freeze_sha256,

            "data_protocol_sha256":
                data_protocol_sha256,
        },
    }


def validate_contract_manifest(
    payload: Mapping[str, Any],
) -> None:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise ThreatModelContractError(
            "Phase-12 contract must be a mapping"
        )

    if payload.get(
        "schema"
    ) != SCHEMA:
        raise ThreatModelContractError(
            "unexpected Phase-12 schema"
        )

    if payload[
        "lifecycle_status"
    ] != (
        Phase12Lifecycle
        .CONTRACT_IMPLEMENTED_PROTOCOLS_UNINSTANTIATED
        .value
    ):
        raise ThreatModelContractError(
            "unexpected Phase-12 lifecycle"
        )

    scope = payload[
        "phase_scope"
    ]

    if scope[
        "phase"
    ] != 12:
        raise ThreatModelContractError(
            "unexpected phase"
        )

    if scope[
        "name"
    ] != "explicit_attack_evaluation":
        raise ThreatModelContractError(
            "unexpected Phase-12 scope"
        )

    separation = payload[
        "evidence_category_separation"
    ]

    if separation[
        "fault_evaluation_separate_from_attack_evaluation"
    ] is not True:
        raise ThreatModelContractError(
            "fault/attack evidence separation lost"
        )

    if separation[
        "environmental_nonattack_degradation_separate_from_attack_evaluation"
    ] is not True:
        raise ThreatModelContractError(
            "environmental/attack evidence separation lost"
        )

    if separation[
        "controlled_fault_truth_is_attack_truth"
    ] is not False:
        raise ThreatModelContractError(
            "controlled fault truth cannot become attack truth"
        )

    taxonomy = payload[
        "planned_attack_taxonomy"
    ]

    if taxonomy[
        "identities"
    ] != list(
        PLANNED_ATTACK_IDENTITIES
    ):
        raise ThreatModelContractError(
            "planned attack taxonomy changed"
        )

    if taxonomy[
        "identity_count"
    ] != 6:
        raise ThreatModelContractError(
            "unexpected planned attack count"
        )

    for key in (
        "taxonomy_is_selected_threat_model",
        "taxonomy_identity_is_executable_attack_protocol",
        "taxonomy_identity_is_empirical_attack_evidence",
    ):
        if taxonomy[
            key
        ] is not False:
            raise ThreatModelContractError(
                f"{key} must remain false"
            )

    protocol = payload[
        "attack_protocol_schema"
    ]

    if protocol[
        "required_fields"
    ] != list(
        REQUIRED_ATTACK_PROTOCOL_FIELDS
    ):
        raise ThreatModelContractError(
            "required attack-protocol fields changed"
        )

    if protocol[
        "required_field_count"
    ] != 8:
        raise ThreatModelContractError(
            "unexpected attack-protocol field count"
        )

    if protocol[
        "instantiated_protocols"
    ] != []:
        raise ThreatModelContractError(
            "attack protocol instantiated unexpectedly"
        )

    if protocol[
        "instantiated_protocol_count"
    ] != 0:
        raise ThreatModelContractError(
            "attack protocol count must remain zero"
        )

    if protocol[
        "complete_explicit_threat_model_required_before_execution"
    ] is not True:
        raise ThreatModelContractError(
            "explicit threat-model requirement lost"
        )

    rq3 = payload[
        "rq3_boundary"
    ]

    if rq3[
        "attack_classes"
    ] != list(
        RQ3_ATTACK_CLASSES
    ):
        raise ThreatModelContractError(
            "RQ3 attack classes changed"
        )

    if rq3[
        "identifiability_assumptions_required"
    ] is not True:
        raise ThreatModelContractError(
            "RQ3 identifiability requirement lost"
        )

    for key in (
        "single_sensor_operational_definition_selected",
        "coordinated_operational_definition_selected",
        "adaptive_operational_definition_selected",
        "phase7_numeric_auxiliary_consistency_available",
        "rq3_executable",
        "rq3_answer_available",
    ):
        if rq3[
            key
        ] is not False:
            raise ThreatModelContractError(
                f"{key} must remain false"
            )

    attribution = payload[
        "source_attribution_boundary"
    ]

    if set(
        attribution.values()
    ) != {
        False,
    }:
        raise ThreatModelContractError(
            "source-attribution boundary must remain closed"
        )

    selection = payload[
        "selection_boundary"
    ]

    nullable = (
        "threat_model",
        "attacker_knowledge_model",
        "attack_goal",
        "attack_family",
        "attack_target_pipeline_layer",
    )

    for key in nullable:
        if selection[
            key
        ] is not None:
            raise ThreatModelContractError(
                f"{key} was selected unexpectedly"
            )

    list_values = (
        "writable_modalities",
        "writable_fields",
        "protected_source_assumptions",
        "identifiability_assumptions",
    )

    for key in list_values:
        if selection[
            key
        ] != []:
            raise ThreatModelContractError(
                f"{key} must remain empty"
            )

    for key, value in selection.items():
        if key.endswith(
            "_selected"
        ) and value is not False:
            raise ThreatModelContractError(
                f"{key} must remain false"
            )

    operating = payload[
        "attack_operating_point_boundary"
    ]

    for key in (
        "attack_duration",
        "attack_budget",
        "attack_magnitude",
        "attack_rate",
        "attack_norm",
        "attack_schedule",
        "attack_seed_schedule",
        "attack_threshold",
    ):
        if operating[
            key
        ] is not None:
            raise ThreatModelContractError(
                f"{key} was selected unexpectedly"
            )

    for key, value in operating.items():
        if key.endswith(
            "_selected"
        ) and value is not False:
            raise ThreatModelContractError(
                f"{key} must remain false"
            )

    if operating[
        "budgets_and_thresholds_must_be_fixed_before_held_out_testing"
    ] is not True:
        raise ThreatModelContractError(
            "pre-held-out freeze rule lost"
        )

    if operating[
        "held_out_testing_may_select_attack_budget"
    ] is not False:
        raise ThreatModelContractError(
            "held-out test cannot select attack budget"
        )

    if operating[
        "held_out_testing_may_select_attack_threshold"
    ] is not False:
        raise ThreatModelContractError(
            "held-out test cannot select attack threshold"
        )

    phase3 = payload[
        "phase3_reuse_boundary"
    ]

    if phase3[
        "currently_frozen_native_families"
    ] != list(
        NATIVE_PHASE3_FAMILIES
    ):
        raise ThreatModelContractError(
            "native Phase-3 family identity changed"
        )

    if phase3[
        "future_attack_related_candidate_mechanisms_not_implemented"
    ] != list(
        PHASE3_FUTURE_ATTACK_RELATED_CANDIDATES
    ):
        raise ThreatModelContractError(
            "Phase-3 future attack candidate inventory changed"
        )

    if phase3[
        "phase3_attack_context_requires_explicit_threat_model"
    ] is not True:
        raise ThreatModelContractError(
            "Phase-3 threat-model requirement lost"
        )

    for key in (
        "phase3_taxonomy_identity_is_phase12_protocol",
        "phase3_selection_policy_is_phase12_threat_model",
        "phase3_corruption_reuse_authorized",
        "native_phase3_family_execution_authorized_for_phase12",
    ):
        if phase3[
            key
        ] is not False:
            raise ThreatModelContractError(
                f"{key} must remain false"
            )

    phase10 = payload[
        "phase10_reuse_boundary"
    ]

    if set(
        phase10.values()
    ) != {
        False,
    }:
        raise ThreatModelContractError(
            "Phase-10 fault evidence cannot become Phase-12 attack evidence"
        )

    execution = payload[
        "execution_gate"
    ]

    if set(
        execution.values()
    ) != {
        False,
    }:
        raise ThreatModelContractError(
            "Phase-12 execution gate must remain closed"
        )

    protected = payload[
        "protected_scientific_boundaries"
    ]

    if set(
        protected.values()
    ) != {
        False,
    }:
        raise ThreatModelContractError(
            "protected Phase-12 scientific boundary changed"
        )
