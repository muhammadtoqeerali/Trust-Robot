"""TRUST-ROBOT Phase-7 auxiliary consistency evidence contract.

Authoritative Phase-7 scope:
- visual motion versus LiDAR motion;
- inertial propagation versus exteroceptive odometry;
- temporal pose continuity;
- kinematic/proprioceptive motion;
- platform motion bounds;
- residual histories.

Scientific semantics:
- pairwise disagreement establishes inconsistency;
- pairwise disagreement alone does not identify the responsible modality;
- attribution may require modality-specific diagnostics, another sufficiently
  informative modality, or a trusted physical constraint;
- ambiguous cases must not receive fabricated confident attribution.

This module freezes the evidence architecture only. It does not select numeric
consistency measures, time tolerances, offsets, interpolation, transforms,
kinematic models, physical motion bounds, residual-history definitions,
factor weights, or suppression/recovery policies.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


SCHEMA = (
    "TRUST_ROBOT_PHASE7_AUXILIARY_CONSISTENCY_CONTRACT_V1"
)


class AuxiliaryConsistencyContractError(ValueError):
    """Raised when the Phase-7 auxiliary contract is violated."""


class AuxiliaryConsistencyLifecycle(str, Enum):
    CONTRACT_IMPLEMENTED_MEASURES_UNSELECTED = (
        "contract_implemented_measures_unselected"
    )


class AuxiliaryEvidenceFamily(str, Enum):
    VISUAL_MOTION_VS_LIDAR_MOTION = (
        "visual_motion_vs_lidar_motion"
    )

    INERTIAL_PROPAGATION_VS_EXTEROCEPTIVE_ODOMETRY = (
        "inertial_propagation_vs_exteroceptive_odometry"
    )

    TEMPORAL_POSE_CONTINUITY = (
        "temporal_pose_continuity"
    )

    KINEMATIC_PROPRIOCEPTIVE_MOTION = (
        "kinematic_proprioceptive_motion"
    )

    PLATFORM_MOTION_BOUNDS = (
        "platform_motion_bounds"
    )

    RESIDUAL_HISTORIES = (
        "residual_histories"
    )


class AttributionBasis(str, Enum):
    MODALITY_SPECIFIC_DIAGNOSTICS = (
        "modality_specific_diagnostics"
    )

    ANOTHER_SUFFICIENTLY_INFORMATIVE_MODALITY = (
        "another_sufficiently_informative_modality"
    )

    TRUSTED_PHYSICAL_CONSTRAINT = (
        "trusted_physical_constraint"
    )


EVIDENCE_FAMILIES = tuple(
    AuxiliaryEvidenceFamily
)


ATTRIBUTION_BASES = tuple(
    AttributionBasis
)


@dataclass(frozen=True)
class CurrentAuxiliaryConsistencyGate:
    numeric_consistency_measure_selected: bool = False

    temporal_tolerance_selected: bool = False
    time_offset_selected: bool = False
    interpolation_selected: bool = False

    cross_modal_transform_selected: bool = False

    kinematic_model_selected: bool = False
    trusted_platform_motion_bound_selected: bool = False

    residual_history_definition_selected: bool = False

    consistency_execution_authorized: bool = False
    source_attribution_authorized: bool = False

    validation_data_opened: bool = False
    confirmation_data_used: bool = False

    def __post_init__(self) -> None:
        for field_name in self.__dataclass_fields__:
            if getattr(
                self,
                field_name,
            ) is not False:
                raise AuxiliaryConsistencyContractError(
                    f"{field_name} must remain false in the "
                    "current Phase-7 evidence state"
                )


CURRENT_AUXILIARY_GATE = (
    CurrentAuxiliaryConsistencyGate()
)


def evidence_family_names() -> tuple[str, ...]:
    return tuple(
        item.value
        for item in EVIDENCE_FAMILIES
    )


def attribution_basis_names() -> tuple[str, ...]:
    return tuple(
        item.value
        for item in ATTRIBUTION_BASES
    )


def assert_consistency_execution_authorized(
    gate: CurrentAuxiliaryConsistencyGate = (
        CURRENT_AUXILIARY_GATE
    ),
) -> None:
    if gate.consistency_execution_authorized is not True:
        raise AuxiliaryConsistencyContractError(
            "Phase-7 consistency computation is not authorized: "
            "required numeric/physical definitions remain unselected"
        )


def assert_source_attribution_authorized(
    gate: CurrentAuxiliaryConsistencyGate = (
        CURRENT_AUXILIARY_GATE
    ),
) -> None:
    if gate.source_attribution_authorized is not True:
        raise AuxiliaryConsistencyContractError(
            "responsible-modality attribution is not authorized by "
            "the current auxiliary evidence state"
        )


def build_contract_manifest(
    *,
    phase6_freeze_sha256: str,
    phase5_freeze_sha256: str,
    phase5_diagnostic_channel_config_sha256: str,
    master_context_sha256: str,
    phase_plan_sha256: str,
    frontier_report_sha256: str,
    frontier_json_sha256: str,
    authoritative_scope_report_sha256: str,
    authoritative_scope_json_sha256: str,
) -> dict[str, Any]:
    gate = CURRENT_AUXILIARY_GATE

    return {
        "schema":
            SCHEMA,

        "lifecycle_status":
            AuxiliaryConsistencyLifecycle
            .CONTRACT_IMPLEMENTED_MEASURES_UNSELECTED
            .value,

        "phase_scope": {
            "phase":
                7,

            "name":
                "auxiliary_consistency",

            "purpose":
                (
                    "cross_modal_temporal_kinematic_"
                    "consistency_evidence"
                ),

            "evidence_only":
                True,

            "health_model_replacement":
                False,

            "phase8_factor_conditioning_in_scope":
                False,

            "phase9_suppression_recovery_status_in_scope":
                False,

            "ood_method_in_scope":
                False,

            "historical_imu_reliability_choices_adopted":
                False,

            "gnss_role_changed":
                False,

            "gnss_remains_optional":
                True,
        },

        "evidence_families": [
            {
                "family":
                    family.value,

                "applicability":
                    "where_applicable",

                "numeric_measure":
                    None,

                "numeric_measure_selected":
                    False,

                "execution_authorized":
                    False,
            }
            for family
            in EVIDENCE_FAMILIES
        ],

        "inconsistency_semantics": {
            "pairwise_disagreement_establishes_inconsistency":
                True,

            "pairwise_disagreement_alone_identifies_responsible_modality":
                False,

            "pairwise_disagreement_is_health_label":
                False,

            "pairwise_disagreement_is_suppression_command":
                False,
        },

        "attribution_semantics": {
            "required_support_may_include": [
                item.value
                for item in ATTRIBUTION_BASES
            ],

            "pairwise_disagreement_alone_sufficient_for_attribution":
                False,

            "source_attribution_authorized_in_current_state":
                False,

            "fabricated_confident_label_allowed":
                False,

            "ambiguous_case_must_remain_explicit":
                True,

            "estimator_degraded_reporting_named_by_project":
                True,

            "phase7_estimator_status_logic_implemented":
                False,
        },

        "measurement_definition_gate": {
            "numeric_consistency_measure_selected":
                gate.numeric_consistency_measure_selected,

            "temporal_tolerance_selected":
                gate.temporal_tolerance_selected,

            "time_offset_selected":
                gate.time_offset_selected,

            "interpolation_selected":
                gate.interpolation_selected,

            "cross_modal_transform_selected":
                gate.cross_modal_transform_selected,

            "kinematic_model_selected":
                gate.kinematic_model_selected,

            "trusted_platform_motion_bound_selected":
                gate.trusted_platform_motion_bound_selected,

            "residual_history_definition_selected":
                gate.residual_history_definition_selected,

            "consistency_execution_authorized":
                gate.consistency_execution_authorized,

            "source_attribution_authorized":
                gate.source_attribution_authorized,
        },

        "phase_boundary": {
            "current_standardized_innovation_consumed_here":
                False,

            "health_aware_factor_weight_selected_here":
                False,

            "factor_information_rescaling_implemented_here":
                False,

            "covariance_inflation_implemented_here":
                False,

            "suppression_threshold_selected_here":
                False,

            "recovery_threshold_selected_here":
                False,

            "fallback_threshold_selected_here":
                False,

            "hysteresis_implemented_here":
                False,

            "estimator_availability_logic_implemented_here":
                False,
        },

        "data_boundary": {
            "train_data_used_for_numeric_measure_selection":
                False,

            "validation_data_opened":
                gate.validation_data_opened,

            "confirmation_data_used":
                gate.confirmation_data_used,

            "reference_data_used":
                False,

            "physical_hardware_accessed":
                False,
        },

        "scientific_boundary": {
            "phase5_empirical_health_completion_assumed":
                False,

            "phase6_empirical_calibration_completion_assumed":
                False,

            "sync_proven":
                False,

            "physical_measurement_time_selected":
                False,

            "cross_modal_alignment_selected":
                False,

            "numeric_residual_threshold_selected":
                False,

            "responsible_modality_inferred":
                False,

            "health_label_assigned":
                False,

            "ate_rpe_computation_authorized":
                False,

            "final_scoring_authorized":
                False,
        },

        "source_bindings": {
            "phase6_freeze_sha256":
                phase6_freeze_sha256,

            "phase5_freeze_sha256":
                phase5_freeze_sha256,

            "phase5_diagnostic_channel_config_sha256":
                phase5_diagnostic_channel_config_sha256,

            "master_context_sha256":
                master_context_sha256,

            "phase_plan_sha256":
                phase_plan_sha256,

            "frontier_report_sha256":
                frontier_report_sha256,

            "frontier_json_sha256":
                frontier_json_sha256,

            "authoritative_scope_report_sha256":
                authoritative_scope_report_sha256,

            "authoritative_scope_json_sha256":
                authoritative_scope_json_sha256,
        },
    }


def validate_contract_manifest(
    payload: Mapping[str, Any],
) -> None:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise AuxiliaryConsistencyContractError(
            "Phase-7 contract must be a mapping"
        )

    if payload.get(
        "schema"
    ) != SCHEMA:
        raise AuxiliaryConsistencyContractError(
            "unexpected Phase-7 schema"
        )

    if payload[
        "lifecycle_status"
    ] != (
        AuxiliaryConsistencyLifecycle
        .CONTRACT_IMPLEMENTED_MEASURES_UNSELECTED
        .value
    ):
        raise AuxiliaryConsistencyContractError(
            "unexpected Phase-7 lifecycle"
        )

    scope = payload[
        "phase_scope"
    ]

    if scope != {
        "phase": 7,
        "name": "auxiliary_consistency",
        "purpose": "cross_modal_temporal_kinematic_consistency_evidence",
        "evidence_only": True,
        "health_model_replacement": False,
        "phase8_factor_conditioning_in_scope": False,
        "phase9_suppression_recovery_status_in_scope": False,
        "ood_method_in_scope": False,
        "historical_imu_reliability_choices_adopted": False,
        "gnss_role_changed": False,
        "gnss_remains_optional": True,
    }:
        raise AuxiliaryConsistencyContractError(
            "Phase-7 scope changed"
        )

    families = payload[
        "evidence_families"
    ]

    expected_names = list(
        evidence_family_names()
    )

    if [
        item[
            "family"
        ]
        for item in families
    ] != expected_names:
        raise AuxiliaryConsistencyContractError(
            "authoritative evidence families changed"
        )

    if len(
        families
    ) != 6:
        raise AuxiliaryConsistencyContractError(
            "Phase-7 must expose exactly six authoritative families"
        )

    for item in families:
        if item[
            "applicability"
        ] != "where_applicable":
            raise AuxiliaryConsistencyContractError(
                "evidence-family applicability changed"
            )

        if item[
            "numeric_measure"
        ] is not None:
            raise AuxiliaryConsistencyContractError(
                "numeric consistency measure was selected unexpectedly"
            )

        if item[
            "numeric_measure_selected"
        ] is not False:
            raise AuxiliaryConsistencyContractError(
                "numeric measure selection must remain false"
            )

        if item[
            "execution_authorized"
        ] is not False:
            raise AuxiliaryConsistencyContractError(
                "family execution must remain unauthorized"
            )

    inconsistency = payload[
        "inconsistency_semantics"
    ]

    if inconsistency != {
        "pairwise_disagreement_establishes_inconsistency": True,
        "pairwise_disagreement_alone_identifies_responsible_modality": False,
        "pairwise_disagreement_is_health_label": False,
        "pairwise_disagreement_is_suppression_command": False,
    }:
        raise AuxiliaryConsistencyContractError(
            "pairwise-disagreement semantics changed"
        )

    attribution = payload[
        "attribution_semantics"
    ]

    if attribution[
        "required_support_may_include"
    ] != list(
        attribution_basis_names()
    ):
        raise AuxiliaryConsistencyContractError(
            "authoritative attribution bases changed"
        )

    required_false = (
        "pairwise_disagreement_alone_sufficient_for_attribution",
        "source_attribution_authorized_in_current_state",
        "fabricated_confident_label_allowed",
        "phase7_estimator_status_logic_implemented",
    )

    for key in required_false:
        if attribution[
            key
        ] is not False:
            raise AuxiliaryConsistencyContractError(
                f"{key} must remain false"
            )

    if attribution[
        "ambiguous_case_must_remain_explicit"
    ] is not True:
        raise AuxiliaryConsistencyContractError(
            "ambiguous cases must remain explicit"
        )

    if attribution[
        "estimator_degraded_reporting_named_by_project"
    ] is not True:
        raise AuxiliaryConsistencyContractError(
            "authoritative estimator-degraded reporting semantics lost"
        )

    gate = payload[
        "measurement_definition_gate"
    ]

    if set(
        gate.values()
    ) != {
        False,
    }:
        raise AuxiliaryConsistencyContractError(
            "all current measurement-definition gates must remain false"
        )

    phase_boundary = payload[
        "phase_boundary"
    ]

    if set(
        phase_boundary.values()
    ) != {
        False,
    }:
        raise AuxiliaryConsistencyContractError(
            "Phase-8/9 behavior leaked into Phase 7"
        )

    data_boundary = payload[
        "data_boundary"
    ]

    if set(
        data_boundary.values()
    ) != {
        False,
    }:
        raise AuxiliaryConsistencyContractError(
            "Phase-7 data boundary changed"
        )

    scientific = payload[
        "scientific_boundary"
    ]

    if set(
        scientific.values()
    ) != {
        False,
    }:
        raise AuxiliaryConsistencyContractError(
            "Phase-7 scientific boundary changed"
        )
