"""TRUST-ROBOT Phase-11 cross-dataset compatibility contract.

Phase 11:
    Cross-dataset evaluation.
    Generalization/stress evidence.

This layer binds project-declared dataset roles without converting those
declarations into local readiness, modality compatibility, reference
compatibility, timing/frame validity, split selection, recalibration
authorization, or evaluation authorization.

EuRoC and TUM-VI are declared project datasets. Their presence here is a
role-binding statement, not an experimental-selection or readiness claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


SCHEMA = (
    "TRUST_ROBOT_PHASE11_CROSS_DATASET_COMPATIBILITY_CONTRACT_V1"
)

PRIMARY_DATASET = "M2DGR"

DECLARED_NONPRIMARY_DATASETS = (
    "EuRoC",
    "TUM_VI",
)

PROPOSAL_LEVEL_COMMON_MODALITIES = (
    "camera",
    "imu",
)


class CrossDatasetCompatibilityContractError(ValueError):
    """Raised when Phase-11 fail-closed boundaries are violated."""


class Phase11Lifecycle(str, Enum):
    CONTRACT_IMPLEMENTED_LOCAL_READINESS_UNVERIFIED = (
        "contract_implemented_local_readiness_unverified"
    )


@dataclass(frozen=True)
class CurrentPhase11Gate:
    secondary_dataset_selected: bool = False
    secondary_dataset_data_open_authorized: bool = False

    cross_dataset_adapter_implemented: bool = False
    modality_compatibility_verified: bool = False
    reference_compatibility_verified: bool = False
    timing_semantics_verified: bool = False
    frame_semantics_verified: bool = False

    secondary_dataset_split_selected: bool = False
    reference_family_selected: bool = False

    cross_dataset_recalibration_authorized: bool = False
    cross_dataset_model_refit_authorized: bool = False
    cross_dataset_threshold_refit_authorized: bool = False
    cross_dataset_calibration_refit_authorized: bool = False

    cross_dataset_alignment_selected: bool = False
    cross_dataset_association_selected: bool = False
    cross_dataset_interpolation_selected: bool = False

    cross_dataset_evaluation_authorized: bool = False

    validation_data_opened: bool = False
    confirmation_data_used: bool = False

    def __post_init__(self) -> None:
        for field_name in self.__dataclass_fields__:
            if getattr(
                self,
                field_name,
            ) is not False:
                raise CrossDatasetCompatibilityContractError(
                    f"{field_name} must remain false in the "
                    "current Phase-11 evidence state"
                )


CURRENT_PHASE11_GATE = CurrentPhase11Gate()


def declared_nonprimary_datasets() -> tuple[str, ...]:
    return DECLARED_NONPRIMARY_DATASETS


def proposal_level_common_modalities() -> tuple[str, ...]:
    return PROPOSAL_LEVEL_COMMON_MODALITIES


def assert_secondary_dataset_data_open_authorized(
    gate: CurrentPhase11Gate = CURRENT_PHASE11_GATE,
) -> None:
    if gate.secondary_dataset_data_open_authorized is not True:
        raise CrossDatasetCompatibilityContractError(
            "secondary-dataset data opening is not authorized: "
            "local readiness has not been established"
        )


def assert_cross_dataset_recalibration_authorized(
    gate: CurrentPhase11Gate = CURRENT_PHASE11_GATE,
) -> None:
    if gate.cross_dataset_recalibration_authorized is not True:
        raise CrossDatasetCompatibilityContractError(
            "cross-dataset recalibration is not authorized"
        )


def assert_cross_dataset_evaluation_authorized(
    gate: CurrentPhase11Gate = CURRENT_PHASE11_GATE,
) -> None:
    if gate.cross_dataset_evaluation_authorized is not True:
        raise CrossDatasetCompatibilityContractError(
            "cross-dataset evaluation is not authorized"
        )


def build_contract_manifest(
    *,
    phase10_freeze_sha256: str,
    master_context_sha256: str,
    phase_plan_sha256: str,
    frontier_report_sha256: str,
    frontier_json_sha256: str,
    role_resolution_report_sha256: str,
    role_resolution_json_sha256: str,
    dataset_registry_sha256: str,
    data_protocol_sha256: str,
    decisions_sha256: str,
    local_paths_sha256: str,
    local_paths_example_sha256: str,
) -> dict[str, Any]:
    gate = CURRENT_PHASE11_GATE

    return {
        "schema":
            SCHEMA,

        "lifecycle_status":
            Phase11Lifecycle
            .CONTRACT_IMPLEMENTED_LOCAL_READINESS_UNVERIFIED
            .value,

        "phase_scope": {
            "phase":
                11,

            "name":
                "cross_dataset_evaluation",

            "evidence_role":
                "generalization_stress_evidence",
        },

        "dataset_role_separation": {
            "proposal_level_role_equals_local_readiness":
                False,

            "proposal_level_role_equals_evaluation_authorization":
                False,

            "dataset_role_binding_is_experiment_selection":
                False,
        },

        "primary_dataset": {
            "dataset_id":
                PRIMARY_DATASET,

            "role":
                "primary_development_benchmark",

            "local_path_present":
                True,

            "candidate_input_modalities": [
                "camera",
                "lidar",
                "imu",
            ],

            "phase11_secondary_dataset":
                False,
        },

        "declared_nonprimary_datasets": {
            "EuRoC": {
                "proposal_status":
                    "core_publicly_available",

                "project_role": [
                    "camera_imu_controlled_testing",
                    "different_platform_comparison",
                ],

                "explicit_cross_dataset_stress_role":
                    False,

                "candidate_input_modalities": [
                    "camera",
                    "imu",
                ],

                "local_readiness":
                    "unverified",

                "local_path_present":
                    False,

                "evaluation_selected":
                    False,

                "data_opened":
                    False,

                "reference_notes": [
                    "Vicon-room sequences may support 6-DoF pose reference",
                    "machine-hall Leica reference is position-only for evaluation semantics",
                ],
            },

            "TUM_VI": {
                "proposal_status":
                    "supplementary_publicly_available",

                "project_role": [
                    "cross_dataset_stress_test",
                ],

                "explicit_cross_dataset_stress_role":
                    True,

                "candidate_input_modalities": [
                    "camera",
                    "imu",
                ],

                "local_readiness":
                    "unverified",

                "local_path_present":
                    False,

                "evaluation_selected":
                    False,

                "data_opened":
                    False,

                "reference_notes": [
                    "room sequences have full-trajectory motion-capture reference",
                    "many longer sequences have only partial start/end reference",
                ],
            },
        },

        "proposal_level_modality_overlap": {
            "common_modalities_named": list(
                PROPOSAL_LEVEL_COMMON_MODALITIES
            ),

            "common_modalities_are_verified_cross_dataset_compatibility":
                False,

            "lidar_common_to_declared_nonprimary_datasets":
                False,

            "modality_compatibility_verified":
                gate.modality_compatibility_verified,

            "sensor_role_mapping_selected":
                False,
        },

        "reference_compatibility_boundary": {
            "reference_family_selected":
                gate.reference_family_selected,

            "reference_compatibility_verified":
                gate.reference_compatibility_verified,

            "score_only_supported_intervals_and_dimensions":
                True,

            "eu_ro_c_leica_rotation_may_be_treated_as_ground_truth":
                False,

            "tum_vi_partial_reference_may_be_treated_as_full_trajectory_reference":
                False,

            "reference_stream_may_also_be_estimator_input_without_independence":
                False,
        },

        "adapter_and_time_boundary": {
            "cross_dataset_adapter_implemented":
                gate.cross_dataset_adapter_implemented,

            "future_adapter_must_preserve_raw_timestamps":
                True,

            "unknown_time_offset_may_be_assumed":
                False,

            "unknown_clock_conversion_may_be_assumed":
                False,

            "interpolation_may_be_assumed":
                False,

            "timing_semantics_verified":
                gate.timing_semantics_verified,

            "frame_semantics_verified":
                gate.frame_semantics_verified,

            "alignment_selected":
                gate.cross_dataset_alignment_selected,

            "association_selected":
                gate.cross_dataset_association_selected,

            "interpolation_selected":
                gate.cross_dataset_interpolation_selected,
        },

        "split_and_transfer_boundary": {
            "secondary_dataset_split_selected":
                gate.secondary_dataset_split_selected,

            "zero_shot_transfer_defined_as_separate_reported_condition":
                True,

            "recalibrated_transfer_defined_as_separate_reported_condition":
                True,

            "cross_dataset_recalibration_authorized":
                gate.cross_dataset_recalibration_authorized,

            "recalibration_if_later_allowed_requires_calibration_only_subset":
                True,

            "recalibration_subset_must_be_disjoint_from_final_cross_dataset_testing":
                True,

            "cross_dataset_model_refit_authorized":
                gate.cross_dataset_model_refit_authorized,

            "cross_dataset_threshold_refit_authorized":
                gate.cross_dataset_threshold_refit_authorized,

            "cross_dataset_calibration_refit_authorized":
                gate.cross_dataset_calibration_refit_authorized,
        },

        "execution_gate": {
            "secondary_dataset_selected":
                gate.secondary_dataset_selected,

            "secondary_dataset_data_open_authorized":
                gate.secondary_dataset_data_open_authorized,

            "cross_dataset_adapter_implemented":
                gate.cross_dataset_adapter_implemented,

            "modality_compatibility_verified":
                gate.modality_compatibility_verified,

            "reference_compatibility_verified":
                gate.reference_compatibility_verified,

            "timing_semantics_verified":
                gate.timing_semantics_verified,

            "frame_semantics_verified":
                gate.frame_semantics_verified,

            "secondary_dataset_split_selected":
                gate.secondary_dataset_split_selected,

            "cross_dataset_evaluation_authorized":
                gate.cross_dataset_evaluation_authorized,

            "cross_dataset_evaluation_executed":
                False,
        },

        "protected_scientific_boundaries": {
            "phase10_rq1_answer_assumed":
                False,

            "phase10_rq2_answer_assumed":
                False,

            "cross_dataset_generalization_is_automatically_ood":
                False,

            "secondary_dataset_data_opened":
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
            "phase10_freeze_sha256":
                phase10_freeze_sha256,

            "master_context_sha256":
                master_context_sha256,

            "phase_plan_sha256":
                phase_plan_sha256,

            "frontier_report_sha256":
                frontier_report_sha256,

            "frontier_json_sha256":
                frontier_json_sha256,

            "role_resolution_report_sha256":
                role_resolution_report_sha256,

            "role_resolution_json_sha256":
                role_resolution_json_sha256,

            "dataset_registry_sha256":
                dataset_registry_sha256,

            "data_protocol_sha256":
                data_protocol_sha256,

            "decisions_sha256":
                decisions_sha256,

            "local_paths_sha256":
                local_paths_sha256,

            "local_paths_example_sha256":
                local_paths_example_sha256,
        },
    }


def validate_contract_manifest(
    payload: Mapping[str, Any],
) -> None:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise CrossDatasetCompatibilityContractError(
            "Phase-11 contract must be a mapping"
        )

    if payload.get(
        "schema"
    ) != SCHEMA:
        raise CrossDatasetCompatibilityContractError(
            "unexpected Phase-11 schema"
        )

    if payload[
        "lifecycle_status"
    ] != (
        Phase11Lifecycle
        .CONTRACT_IMPLEMENTED_LOCAL_READINESS_UNVERIFIED
        .value
    ):
        raise CrossDatasetCompatibilityContractError(
            "unexpected Phase-11 lifecycle"
        )

    scope = payload[
        "phase_scope"
    ]

    if scope[
        "phase"
    ] != 11:
        raise CrossDatasetCompatibilityContractError(
            "unexpected phase"
        )

    if scope[
        "name"
    ] != "cross_dataset_evaluation":
        raise CrossDatasetCompatibilityContractError(
            "unexpected Phase-11 scope"
        )

    separation = payload[
        "dataset_role_separation"
    ]

    if set(
        separation.values()
    ) != {
        False,
    }:
        raise CrossDatasetCompatibilityContractError(
            "proposal role was promoted to readiness, authorization, or selection"
        )

    primary = payload[
        "primary_dataset"
    ]

    if primary[
        "dataset_id"
    ] != PRIMARY_DATASET:
        raise CrossDatasetCompatibilityContractError(
            "primary dataset changed"
        )

    if primary[
        "local_path_present"
    ] is not True:
        raise CrossDatasetCompatibilityContractError(
            "M2DGR local-path evidence changed"
        )

    datasets = payload[
        "declared_nonprimary_datasets"
    ]

    if tuple(
        datasets.keys()
    ) != DECLARED_NONPRIMARY_DATASETS:
        raise CrossDatasetCompatibilityContractError(
            "declared non-primary dataset identity changed"
        )

    euroc = datasets[
        "EuRoC"
    ]

    if euroc[
        "local_readiness"
    ] != "unverified":
        raise CrossDatasetCompatibilityContractError(
            "EuRoC local readiness was promoted"
        )

    if euroc[
        "local_path_present"
    ] is not False:
        raise CrossDatasetCompatibilityContractError(
            "EuRoC local path unexpectedly available"
        )

    if euroc[
        "evaluation_selected"
    ] is not False:
        raise CrossDatasetCompatibilityContractError(
            "EuRoC was selected for evaluation"
        )

    tum = datasets[
        "TUM_VI"
    ]

    if tum[
        "local_readiness"
    ] != "unverified":
        raise CrossDatasetCompatibilityContractError(
            "TUM-VI local readiness was promoted"
        )

    if tum[
        "local_path_present"
    ] is not False:
        raise CrossDatasetCompatibilityContractError(
            "TUM-VI local path unexpectedly available"
        )

    if tum[
        "evaluation_selected"
    ] is not False:
        raise CrossDatasetCompatibilityContractError(
            "TUM-VI was selected for evaluation"
        )

    overlap = payload[
        "proposal_level_modality_overlap"
    ]

    if overlap[
        "common_modalities_named"
    ] != list(
        PROPOSAL_LEVEL_COMMON_MODALITIES
    ):
        raise CrossDatasetCompatibilityContractError(
            "proposal-level camera/IMU overlap changed"
        )

    if overlap[
        "common_modalities_are_verified_cross_dataset_compatibility"
    ] is not False:
        raise CrossDatasetCompatibilityContractError(
            "proposal modality overlap was promoted to verified compatibility"
        )

    if overlap[
        "modality_compatibility_verified"
    ] is not False:
        raise CrossDatasetCompatibilityContractError(
            "modality compatibility remains unverified"
        )

    reference = payload[
        "reference_compatibility_boundary"
    ]

    if reference[
        "reference_family_selected"
    ] is not False:
        raise CrossDatasetCompatibilityContractError(
            "reference family selected unexpectedly"
        )

    if reference[
        "reference_compatibility_verified"
    ] is not False:
        raise CrossDatasetCompatibilityContractError(
            "reference compatibility remains unverified"
        )

    if reference[
        "score_only_supported_intervals_and_dimensions"
    ] is not True:
        raise CrossDatasetCompatibilityContractError(
            "reference-coverage scoring restriction lost"
        )

    adapter = payload[
        "adapter_and_time_boundary"
    ]

    if adapter[
        "cross_dataset_adapter_implemented"
    ] is not False:
        raise CrossDatasetCompatibilityContractError(
            "cross-dataset adapter unexpectedly implemented"
        )

    if adapter[
        "future_adapter_must_preserve_raw_timestamps"
    ] is not True:
        raise CrossDatasetCompatibilityContractError(
            "raw timestamp preservation rule lost"
        )

    for key in (
        "unknown_time_offset_may_be_assumed",
        "unknown_clock_conversion_may_be_assumed",
        "interpolation_may_be_assumed",
        "timing_semantics_verified",
        "frame_semantics_verified",
        "alignment_selected",
        "association_selected",
        "interpolation_selected",
    ):
        if adapter[
            key
        ] is not False:
            raise CrossDatasetCompatibilityContractError(
                f"{key} must remain false"
            )

    transfer = payload[
        "split_and_transfer_boundary"
    ]

    if transfer[
        "secondary_dataset_split_selected"
    ] is not False:
        raise CrossDatasetCompatibilityContractError(
            "secondary split selected unexpectedly"
        )

    if transfer[
        "zero_shot_transfer_defined_as_separate_reported_condition"
    ] is not True:
        raise CrossDatasetCompatibilityContractError(
            "zero-shot reporting separation lost"
        )

    if transfer[
        "recalibrated_transfer_defined_as_separate_reported_condition"
    ] is not True:
        raise CrossDatasetCompatibilityContractError(
            "recalibrated-transfer reporting separation lost"
        )

    if transfer[
        "recalibration_if_later_allowed_requires_calibration_only_subset"
    ] is not True:
        raise CrossDatasetCompatibilityContractError(
            "calibration-only subset rule lost"
        )

    if transfer[
        "recalibration_subset_must_be_disjoint_from_final_cross_dataset_testing"
    ] is not True:
        raise CrossDatasetCompatibilityContractError(
            "cross-dataset anti-leakage rule lost"
        )

    for key in (
        "cross_dataset_recalibration_authorized",
        "cross_dataset_model_refit_authorized",
        "cross_dataset_threshold_refit_authorized",
        "cross_dataset_calibration_refit_authorized",
    ):
        if transfer[
            key
        ] is not False:
            raise CrossDatasetCompatibilityContractError(
                f"{key} must remain false"
            )

    if set(
        payload[
            "execution_gate"
        ].values()
    ) != {
        False,
    }:
        raise CrossDatasetCompatibilityContractError(
            "Phase-11 execution gate must remain closed"
        )

    protected = payload[
        "protected_scientific_boundaries"
    ]

    if set(
        protected.values()
    ) != {
        False,
    }:
        raise CrossDatasetCompatibilityContractError(
            "protected Phase-11 scientific boundary changed"
        )
