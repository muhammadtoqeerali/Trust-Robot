"""Phase-5 camera/IMU diagnostic-channel architecture.

This module freezes the *kinds* of evidence required by the TRUST-ROBOT
persistent modality-health pathway without inventing exact camera or IMU
numeric diagnostic features.

Persistent health evidence channels:
1. low-level signal summaries;
2. front-end diagnostics;
3. residual-history evidence.

Current innovation remains a separate short-horizon factor-conditioning input;
this contract does not silently merge it into persistent modality health.

Phase-3 corruption families are recorded only as controlled stressor families.
They are neither diagnostic features nor health labels.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping
from hashlib import sha256
import json

from .multimodal_diagnostic_foundation import (
    Modality,
)


SCHEMA = (
    "TRUST_ROBOT_PHASE5_CAMERA_IMU_DIAGNOSTIC_CHANNEL_CONTRACT_V1"
)


class DiagnosticChannelContractError(ValueError):
    """Raised when the diagnostic-channel contract is violated."""


class DiagnosticChannelKind(str, Enum):
    LOW_LEVEL_SIGNAL_SUMMARY = (
        "low_level_signal_summary"
    )

    FRONTEND_DIAGNOSTIC = (
        "frontend_diagnostic"
    )

    RESIDUAL_HISTORY = (
        "residual_history"
    )


class ChannelImplementationStatus(str, Enum):
    BASIS_SUPPORTED_FEATURES_UNSELECTED = (
        "basis_supported_features_unselected"
    )

    REQUIRED_INTERFACE_NOT_IMPLEMENTED = (
        "required_interface_not_implemented"
    )


class EvidenceUseRole(str, Enum):
    PERSISTENT_HEALTH_INPUT_CANDIDATE = (
        "persistent_health_input_candidate"
    )

    SHORT_HORIZON_FACTOR_CONDITIONING_ONLY = (
        "short_horizon_factor_conditioning_only"
    )

    CONTROLLED_STRESSOR_ONLY = (
        "controlled_stressor_only"
    )


@dataclass(frozen=True)
class DiagnosticChannelSpec:
    modality: Modality
    channel_kind: DiagnosticChannelKind
    implementation_status: ChannelImplementationStatus
    evidence_use_role: EvidenceUseRole
    exact_feature_names: tuple[str, ...]
    basis: str

    def __post_init__(self) -> None:
        if self.modality not in (
            Modality.CAMERA,
            Modality.IMU,
        ):
            raise DiagnosticChannelContractError(
                "camera/IMU contract accepts camera and IMU only"
            )

        if (
            self.evidence_use_role
            is not EvidenceUseRole.PERSISTENT_HEALTH_INPUT_CANDIDATE
        ):
            raise DiagnosticChannelContractError(
                "persistent diagnostic channels must use the "
                "persistent-health candidate role"
            )

        if self.exact_feature_names:
            raise DiagnosticChannelContractError(
                "exact camera/IMU features are intentionally unselected"
            )

        if not self.basis.strip():
            raise DiagnosticChannelContractError(
                "channel basis must be non-empty"
            )


CAMERA_CHANNELS = (
    DiagnosticChannelSpec(
        modality=Modality.CAMERA,
        channel_kind=DiagnosticChannelKind.LOW_LEVEL_SIGNAL_SUMMARY,
        implementation_status=(
            ChannelImplementationStatus
            .BASIS_SUPPORTED_FEATURES_UNSELECTED
        ),
        evidence_use_role=(
            EvidenceUseRole
            .PERSISTENT_HEALTH_INPUT_CANDIDATE
        ),
        exact_feature_names=(),
        basis=(
            "project design requires appropriate low-level signal "
            "summaries; no exact camera scalar feature set is specified"
        ),
    ),
    DiagnosticChannelSpec(
        modality=Modality.CAMERA,
        channel_kind=DiagnosticChannelKind.FRONTEND_DIAGNOSTIC,
        implementation_status=(
            ChannelImplementationStatus
            .REQUIRED_INTERFACE_NOT_IMPLEMENTED
        ),
        evidence_use_role=(
            EvidenceUseRole
            .PERSISTENT_HEALTH_INPUT_CANDIDATE
        ),
        exact_feature_names=(),
        basis=(
            "project design names visual relative-motion / reprojection "
            "information; no validated visual front-end diagnostic "
            "implementation exists in the current TRUST-ROBOT frontier"
        ),
    ),
    DiagnosticChannelSpec(
        modality=Modality.CAMERA,
        channel_kind=DiagnosticChannelKind.RESIDUAL_HISTORY,
        implementation_status=(
            ChannelImplementationStatus
            .REQUIRED_INTERFACE_NOT_IMPLEMENTED
        ),
        evidence_use_role=(
            EvidenceUseRole
            .PERSISTENT_HEALTH_INPUT_CANDIDATE
        ),
        exact_feature_names=(),
        basis=(
            "project design requires residual-history evidence; "
            "camera residual-history implementation is not yet present"
        ),
    ),
)


IMU_CHANNELS = (
    DiagnosticChannelSpec(
        modality=Modality.IMU,
        channel_kind=DiagnosticChannelKind.LOW_LEVEL_SIGNAL_SUMMARY,
        implementation_status=(
            ChannelImplementationStatus
            .BASIS_SUPPORTED_FEATURES_UNSELECTED
        ),
        evidence_use_role=(
            EvidenceUseRole
            .PERSISTENT_HEALTH_INPUT_CANDIDATE
        ),
        exact_feature_names=(),
        basis=(
            "project design requires appropriate low-level signal "
            "summaries; no exact IMU scalar feature set is specified"
        ),
    ),
    DiagnosticChannelSpec(
        modality=Modality.IMU,
        channel_kind=DiagnosticChannelKind.FRONTEND_DIAGNOSTIC,
        implementation_status=(
            ChannelImplementationStatus
            .REQUIRED_INTERFACE_NOT_IMPLEMENTED
        ),
        evidence_use_role=(
            EvidenceUseRole
            .PERSISTENT_HEALTH_INPUT_CANDIDATE
        ),
        exact_feature_names=(),
        basis=(
            "project design names IMU preintegration; no validated "
            "IMU-preintegration diagnostic implementation exists in "
            "the current TRUST-ROBOT frontier"
        ),
    ),
    DiagnosticChannelSpec(
        modality=Modality.IMU,
        channel_kind=DiagnosticChannelKind.RESIDUAL_HISTORY,
        implementation_status=(
            ChannelImplementationStatus
            .REQUIRED_INTERFACE_NOT_IMPLEMENTED
        ),
        evidence_use_role=(
            EvidenceUseRole
            .PERSISTENT_HEALTH_INPUT_CANDIDATE
        ),
        exact_feature_names=(),
        basis=(
            "project design requires residual-history evidence; "
            "IMU residual-history implementation is not yet present"
        ),
    ),
)


CAMERA_CONTROLLED_STRESSOR_FAMILIES = (
    "camera_blur",
    "camera_exposure_degradation",
)

IMU_CONTROLLED_STRESSOR_FAMILIES = (
    "bias_or_drift",
)


CURRENT_INNOVATION_CONTRACT = {
    "role":
        EvidenceUseRole
        .SHORT_HORIZON_FACTOR_CONDITIONING_ONLY
        .value,

    "persistent_health_input_selected":
        False,

    "separation_required":
        True,

    "numeric_definition_selected_here":
        False,
}


def channel_specs_for(
    modality: Modality,
) -> tuple[DiagnosticChannelSpec, ...]:
    if modality is Modality.CAMERA:
        return CAMERA_CHANNELS

    if modality is Modality.IMU:
        return IMU_CHANNELS

    raise DiagnosticChannelContractError(
        "diagnostic channel contract is camera/IMU only"
    )


def _spec_payload(
    spec: DiagnosticChannelSpec,
) -> dict[str, Any]:
    return {
        "modality":
            spec.modality.value,

        "channel_kind":
            spec.channel_kind.value,

        "implementation_status":
            spec.implementation_status.value,

        "evidence_use_role":
            spec.evidence_use_role.value,

        "exact_feature_names":
            list(
                spec.exact_feature_names
            ),

        "basis":
            spec.basis,
    }


def canonical_json_bytes(
    payload: Mapping[str, Any],
) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def content_sha256(
    payload: Mapping[str, Any],
) -> str:
    return sha256(
        canonical_json_bytes(
            payload
        )
    ).hexdigest()


def build_contract_manifest(
    *,
    train_source_evidence_manifest_sha256: str,
    train_source_evidence_content_sha256: str,
    feature_basis_report_sha256: str,
    feature_basis_json_sha256: str,
    phase3_corruption_taxonomy_sha256: str,
    phase4_lidar_freeze_sha256: str,
) -> dict[str, Any]:
    return {
        "schema":
            SCHEMA,

        "scope": {
            "core_modalities":
                [
                    "camera",
                    "imu",
                    "lidar",
                ],

            "camera_imu_contract_scope":
                [
                    "camera",
                    "imu",
                ],

            "lidar_phase4_contract_reopened":
                False,

            "gnss_optional_contract_changed":
                False,
        },

        "persistent_health_evidence_channels": {
            "required_channel_kinds": [
                DiagnosticChannelKind
                .LOW_LEVEL_SIGNAL_SUMMARY
                .value,

                DiagnosticChannelKind
                .FRONTEND_DIAGNOSTIC
                .value,

                DiagnosticChannelKind
                .RESIDUAL_HISTORY
                .value,
            ],

            "camera": [
                _spec_payload(
                    spec
                )
                for spec in CAMERA_CHANNELS
            ],

            "imu": [
                _spec_payload(
                    spec
                )
                for spec in IMU_CHANNELS
            ],
        },

        "current_innovation_separation":
            dict(
                CURRENT_INNOVATION_CONTRACT
            ),

        "controlled_stressor_families": {
            "camera": [
                {
                    "name":
                        name,

                    "role":
                        EvidenceUseRole
                        .CONTROLLED_STRESSOR_ONLY
                        .value,

                    "is_diagnostic_feature":
                        False,

                    "is_health_label":
                        False,
                }
                for name
                in CAMERA_CONTROLLED_STRESSOR_FAMILIES
            ],

            "imu": [
                {
                    "name":
                        name,

                    "role":
                        EvidenceUseRole
                        .CONTROLLED_STRESSOR_ONLY
                        .value,

                    "is_diagnostic_feature":
                        False,

                    "is_health_label":
                        False,
                }
                for name
                in IMU_CONTROLLED_STRESSOR_FAMILIES
            ],
        },

        "estimator_state_concepts": {
            "imu_gyroscope_bias_named_by_project":
                True,

            "imu_accelerometer_bias_named_by_project":
                True,

            "bias_state_is_automatically_health_feature":
                False,

            "bias_state_is_automatically_health_label":
                False,

            "imu_preintegration_named_by_project":
                True,

            "visual_relative_motion_reprojection_named_by_project":
                True,
        },

        "feature_selection_boundary": {
            "camera_exact_feature_names":
                [],

            "imu_exact_feature_names":
                [],

            "camera_feature_contract_selected":
                False,

            "imu_feature_contract_selected":
                False,

            "camera_numeric_low_level_summary_selected":
                False,

            "imu_numeric_low_level_summary_selected":
                False,

            "visual_frontend_diagnostics_implemented":
                False,

            "imu_preintegration_diagnostics_implemented":
                False,

            "camera_residual_history_implemented":
                False,

            "imu_residual_history_implemented":
                False,

            "current_innovation_selected_as_persistent_health_input":
                False,
        },

        "scientific_boundary": {
            "health_label_assigned":
                False,

            "health_probability_emitted":
                False,

            "health_threshold_selected":
                False,

            "classifier_model_selected":
                False,

            "classifier_training_authorized":
                False,

            "calibration_parameter_selected":
                False,

            "physical_measurement_time_selected":
                False,

            "cross_modal_synchronization_selected":
                False,

            "reference_data_used":
                False,

            "validation_data_used":
                False,

            "confirmation_data_used":
                False,

            "ate_rpe_computed":
                False,

            "final_score_computed":
                False,
        },

        "source_bindings": {
            "train_source_evidence_manifest_sha256":
                train_source_evidence_manifest_sha256,

            "train_source_evidence_content_sha256":
                train_source_evidence_content_sha256,

            "feature_basis_report_sha256":
                feature_basis_report_sha256,

            "feature_basis_json_sha256":
                feature_basis_json_sha256,

            "phase3_corruption_taxonomy_sha256":
                phase3_corruption_taxonomy_sha256,

            "phase4_lidar_freeze_sha256":
                phase4_lidar_freeze_sha256,
        },
    }


def validate_contract_manifest(
    payload: Mapping[str, Any],
) -> None:
    if not isinstance(payload, Mapping):
        raise DiagnosticChannelContractError(
            "contract manifest must be a mapping"
        )

    if payload.get(
        "schema"
    ) != SCHEMA:
        raise DiagnosticChannelContractError(
            "unexpected schema"
        )

    channels = payload[
        "persistent_health_evidence_channels"
    ]

    required = [
        "low_level_signal_summary",
        "frontend_diagnostic",
        "residual_history",
    ]

    if channels[
        "required_channel_kinds"
    ] != required:
        raise DiagnosticChannelContractError(
            "persistent health channel kinds changed"
        )

    for modality in (
        "camera",
        "imu",
    ):
        specs = channels[
            modality
        ]

        if len(specs) != 3:
            raise DiagnosticChannelContractError(
                f"{modality} must expose exactly three evidence channels"
            )

        if [
            item[
                "channel_kind"
            ]
            for item in specs
        ] != required:
            raise DiagnosticChannelContractError(
                f"{modality} diagnostic channel order changed"
            )

        for item in specs:
            if item[
                "exact_feature_names"
            ]:
                raise DiagnosticChannelContractError(
                    f"{modality} exact features were selected unexpectedly"
                )

            if (
                item[
                    "evidence_use_role"
                ]
                !=
                "persistent_health_input_candidate"
            ):
                raise DiagnosticChannelContractError(
                    "persistent channel evidence role changed"
                )

    separation = payload[
        "current_innovation_separation"
    ]

    if separation != CURRENT_INNOVATION_CONTRACT:
        raise DiagnosticChannelContractError(
            "current innovation separation changed"
        )

    for modality in (
        "camera",
        "imu",
    ):
        for stressor in payload[
            "controlled_stressor_families"
        ][
            modality
        ]:
            if (
                stressor["role"]
                != "controlled_stressor_only"
                or stressor[
                    "is_diagnostic_feature"
                ] is not False
                or stressor[
                    "is_health_label"
                ] is not False
            ):
                raise DiagnosticChannelContractError(
                    "controlled stressor was promoted into a feature or label"
                )

    selection = payload[
        "feature_selection_boundary"
    ]

    false_keys = (
        "camera_feature_contract_selected",
        "imu_feature_contract_selected",
        "camera_numeric_low_level_summary_selected",
        "imu_numeric_low_level_summary_selected",
        "visual_frontend_diagnostics_implemented",
        "imu_preintegration_diagnostics_implemented",
        "camera_residual_history_implemented",
        "imu_residual_history_implemented",
        "current_innovation_selected_as_persistent_health_input",
    )

    for key in false_keys:
        if selection[key] is not False:
            raise DiagnosticChannelContractError(
                f"{key} must remain false"
            )

    if selection[
        "camera_exact_feature_names"
    ]:
        raise DiagnosticChannelContractError(
            "camera exact feature names must remain empty"
        )

    if selection[
        "imu_exact_feature_names"
    ]:
        raise DiagnosticChannelContractError(
            "IMU exact feature names must remain empty"
        )

    scientific = payload[
        "scientific_boundary"
    ]

    for key, value in scientific.items():
        if value is not False:
            raise DiagnosticChannelContractError(
                f"scientific boundary {key} must remain false"
            )
