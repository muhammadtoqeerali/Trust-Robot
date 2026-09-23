"""TRUST-ROBOT Phase-5 multimodal health-model software interface.

The interface is intentionally fail closed.

It freezes:
- the three health-state semantics;
- core vs optional modality roles;
- current diagnostic-input readiness;
- training/inference/calibration evidence gates;
- confirmation-test closure.

It does not select:
- a classifier architecture;
- a numeric threshold;
- a calibration temperature;
- camera or IMU exact features;
- any physical timing/alignment quantity.

No health output can be emitted while the evidence gate is closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping
import json

from .health_semantics import HealthState
from .multimodal_diagnostic_foundation import Modality


SCHEMA = (
    "TRUST_ROBOT_PHASE5_MULTIMODAL_HEALTH_MODEL_INTERFACE_V1"
)


class HealthModelInterfaceError(ValueError):
    """Raised when the Phase-5 health-model contract is violated."""


class HealthModelLifecycle(str, Enum):
    INTERFACE_IMPLEMENTED_EVIDENCE_BLOCKED = (
        "interface_implemented_evidence_blocked"
    )


class ModelSelectionStatus(str, Enum):
    UNSELECTED = "unselected"


class OutputStatus(str, Enum):
    DISABLED = "disabled"


LIDAR_PHASE4_FEATURES = (
    ("source_point_count", "count"),
    ("target_point_count", "count"),
    ("fixed_point_iterations", "count"),
    ("final_correspondence_count", "count"),
    ("final_nearest_neighbor_rmse_m", "m"),
)


CAMERA_IMU_CHANNELS = (
    "low_level_signal_summary",
    "frontend_diagnostic",
    "residual_history",
)


@dataclass(frozen=True)
class CurrentEvidenceGate:
    accepted_baseline_nominality_source_count: int = 0
    accepted_health_supervision_source_count: int = 0
    real_health_label_count: int = 0

    camera_feature_contract_selected: bool = False
    imu_feature_contract_selected: bool = False
    lidar_phase4_feature_contract_validated: bool = True

    model_architecture_selected: bool = False
    calibration_parameter_selected: bool = False
    health_threshold_selected: bool = False

    classifier_training_authorized: bool = False
    health_inference_authorized: bool = False

    confirmation_closed: bool = True
    confirmation_selection_authorized: bool = False

    physical_validation_deferred: bool = True

    def __post_init__(self) -> None:
        for field_name in (
            "accepted_baseline_nominality_source_count",
            "accepted_health_supervision_source_count",
            "real_health_label_count",
        ):
            value = getattr(
                self,
                field_name,
            )

            if type(value) is not int or value < 0:
                raise HealthModelInterfaceError(
                    f"{field_name} must be an exact non-negative integer"
                )

        required_false = (
            "camera_feature_contract_selected",
            "imu_feature_contract_selected",
            "model_architecture_selected",
            "calibration_parameter_selected",
            "health_threshold_selected",
            "classifier_training_authorized",
            "health_inference_authorized",
            "confirmation_selection_authorized",
        )

        for field_name in required_false:
            if getattr(
                self,
                field_name,
            ) is not False:
                raise HealthModelInterfaceError(
                    f"{field_name} must remain false in current Phase-5 state"
                )

        if self.lidar_phase4_feature_contract_validated is not True:
            raise HealthModelInterfaceError(
                "validated Phase-4 LiDAR feature contract must remain bound"
            )

        if self.confirmation_closed is not True:
            raise HealthModelInterfaceError(
                "confirmation-test split must remain closed"
            )

        if self.physical_validation_deferred is not True:
            raise HealthModelInterfaceError(
                "physical validation is currently deferred"
            )


CURRENT_EVIDENCE_GATE = CurrentEvidenceGate()


def health_state_order() -> tuple[str, ...]:
    return (
        HealthState.HEALTHY.value,
        HealthState.DEGRADED.value,
        HealthState.UNUSABLE.value,
    )


def assert_training_authorized(
    gate: CurrentEvidenceGate = CURRENT_EVIDENCE_GATE,
) -> None:
    if gate.classifier_training_authorized is not True:
        raise HealthModelInterfaceError(
            "classifier training is not authorized by current admissible evidence"
        )


def assert_inference_authorized(
    gate: CurrentEvidenceGate = CURRENT_EVIDENCE_GATE,
) -> None:
    if gate.health_inference_authorized is not True:
        raise HealthModelInterfaceError(
            "health inference is not authorized by current admissible evidence"
        )


def emit_health_state(
    *_: Any,
    gate: CurrentEvidenceGate = CURRENT_EVIDENCE_GATE,
    **__: Any,
) -> str:
    assert_inference_authorized(
        gate
    )

    raise HealthModelInterfaceError(
        "no trained and calibrated health model is bound"
    )


def build_manifest(
    *,
    health_semantics_config_sha256: str,
    health_supervision_config_sha256: str,
    multimodal_foundation_config_sha256: str,
    diagnostic_channel_config_sha256: str,
    train_source_evidence_manifest_sha256: str,
    phase4_lidar_freeze_sha256: str,
) -> dict[str, Any]:
    gate = CURRENT_EVIDENCE_GATE

    return {
        "schema":
            SCHEMA,

        "lifecycle_status":
            HealthModelLifecycle
            .INTERFACE_IMPLEMENTED_EVIDENCE_BLOCKED
            .value,

        "health_states":
            list(
                health_state_order()
            ),

        "modalities": {
            "core": [
                Modality.CAMERA.value,
                Modality.IMU.value,
                Modality.LIDAR.value,
            ],

            "optional": [
                Modality.GNSS.value,
            ],
        },

        "diagnostic_inputs": {
            "camera": {
                "required_channel_kinds":
                    list(
                        CAMERA_IMU_CHANNELS
                    ),

                "exact_feature_names":
                    [],

                "feature_contract_selected":
                    False,
            },

            "imu": {
                "required_channel_kinds":
                    list(
                        CAMERA_IMU_CHANNELS
                    ),

                "exact_feature_names":
                    [],

                "feature_contract_selected":
                    False,
            },

            "lidar": {
                "feature_contract_status":
                    "validated_phase4",

                "phase4_feature_contract_reopened":
                    False,

                "features": [
                    {
                        "name":
                            name,

                        "unit":
                            unit,
                    }
                    for name, unit in LIDAR_PHASE4_FEATURES
                ],
            },

            "gnss": {
                "role":
                    "optional",

                "exact_feature_names":
                    [],

                "feature_contract_selected":
                    False,
            },
        },

        "availability_boundary": {
            "availability_is_health_label":
                False,

            "missing_measurement_encoded_as_zero_feature_vector":
                False,
        },

        "model_selection": {
            "classifier_architecture":
                ModelSelectionStatus.UNSELECTED.value,

            "classifier_architecture_selected":
                False,

            "health_threshold":
                None,

            "health_threshold_selected":
                False,

            "calibration_parameter":
                None,

            "calibration_parameter_selected":
                False,

            "trained_model_artifact_sha256":
                None,
        },

        "runtime_output": {
            "health_state_output":
                OutputStatus.DISABLED.value,

            "health_probability_output":
                OutputStatus.DISABLED.value,

            "training_authorized":
                False,

            "inference_authorized":
                False,
        },

        "evidence_gate": {
            "accepted_baseline_nominality_source_count":
                gate.accepted_baseline_nominality_source_count,

            "accepted_health_supervision_source_count":
                gate.accepted_health_supervision_source_count,

            "real_health_label_count":
                gate.real_health_label_count,

            "camera_feature_contract_selected":
                gate.camera_feature_contract_selected,

            "imu_feature_contract_selected":
                gate.imu_feature_contract_selected,

            "lidar_phase4_feature_contract_validated":
                gate.lidar_phase4_feature_contract_validated,

            "classifier_training_authorized":
                gate.classifier_training_authorized,

            "health_inference_authorized":
                gate.health_inference_authorized,

            "physical_validation_deferred":
                gate.physical_validation_deferred,
        },

        "confirmation_boundary": {
            "confirmation_closed":
                gate.confirmation_closed,

            "confirmation_selection_authorized":
                gate.confirmation_selection_authorized,
        },

        "scientific_boundary": {
            "final_localization_error_used_as_health_supervision":
                False,

            "current_innovation_selected_as_persistent_health_input":
                False,

            "physical_measurement_time_selected":
                False,

            "cross_modal_synchronization_selected":
                False,

            "reference_data_used":
                False,

            "validation_data_used_for_current_model_selection":
                False,

            "confirmation_data_used":
                False,

            "ate_rpe_computation_authorized":
                False,

            "final_scoring_authorized":
                False,
        },

        "source_bindings": {
            "health_semantics_config_sha256":
                health_semantics_config_sha256,

            "health_supervision_config_sha256":
                health_supervision_config_sha256,

            "multimodal_foundation_config_sha256":
                multimodal_foundation_config_sha256,

            "diagnostic_channel_config_sha256":
                diagnostic_channel_config_sha256,

            "train_source_evidence_manifest_sha256":
                train_source_evidence_manifest_sha256,

            "phase4_lidar_freeze_sha256":
                phase4_lidar_freeze_sha256,
        },
    }


def validate_manifest(
    payload: Mapping[str, Any],
) -> None:
    if not isinstance(payload, Mapping):
        raise HealthModelInterfaceError(
            "health-model manifest must be a mapping"
        )

    if payload.get(
        "schema"
    ) != SCHEMA:
        raise HealthModelInterfaceError(
            "unexpected health-model schema"
        )

    if payload[
        "lifecycle_status"
    ] != (
        HealthModelLifecycle
        .INTERFACE_IMPLEMENTED_EVIDENCE_BLOCKED
        .value
    ):
        raise HealthModelInterfaceError(
            "unexpected lifecycle status"
        )

    if payload[
        "health_states"
    ] != [
        "healthy",
        "degraded",
        "unusable",
    ]:
        raise HealthModelInterfaceError(
            "health-state semantics changed"
        )

    if payload[
        "modalities"
    ] != {
        "core": [
            "camera",
            "imu",
            "lidar",
        ],
        "optional": [
            "gnss",
        ],
    }:
        raise HealthModelInterfaceError(
            "modality roles changed"
        )

    inputs = payload[
        "diagnostic_inputs"
    ]

    for modality in (
        "camera",
        "imu",
    ):
        item = inputs[
            modality
        ]

        if item[
            "required_channel_kinds"
        ] != list(
            CAMERA_IMU_CHANNELS
        ):
            raise HealthModelInterfaceError(
                f"{modality} channel architecture changed"
            )

        if item[
            "exact_feature_names"
        ]:
            raise HealthModelInterfaceError(
                f"{modality} exact features were selected unexpectedly"
            )

        if item[
            "feature_contract_selected"
        ] is not False:
            raise HealthModelInterfaceError(
                f"{modality} feature contract must remain unselected"
            )

    lidar = inputs[
        "lidar"
    ]

    if lidar[
        "feature_contract_status"
    ] != "validated_phase4":
        raise HealthModelInterfaceError(
            "LiDAR Phase-4 diagnostic status changed"
        )

    if lidar[
        "phase4_feature_contract_reopened"
    ] is not False:
        raise HealthModelInterfaceError(
            "LiDAR Phase-4 contract cannot be reopened here"
        )

    expected_lidar = [
        {
            "name": name,
            "unit": unit,
        }
        for name, unit
        in LIDAR_PHASE4_FEATURES
    ]

    if lidar[
        "features"
    ] != expected_lidar:
        raise HealthModelInterfaceError(
            "LiDAR Phase-4 features changed"
        )

    gnss = inputs[
        "gnss"
    ]

    if (
        gnss["role"] != "optional"
        or gnss["exact_feature_names"]
        or gnss["feature_contract_selected"] is not False
    ):
        raise HealthModelInterfaceError(
            "optional GNSS boundary changed"
        )

    availability = payload[
        "availability_boundary"
    ]

    if availability != {
        "availability_is_health_label": False,
        "missing_measurement_encoded_as_zero_feature_vector": False,
    }:
        raise HealthModelInterfaceError(
            "availability/health separation changed"
        )

    model = payload[
        "model_selection"
    ]

    if model != {
        "classifier_architecture": "unselected",
        "classifier_architecture_selected": False,
        "health_threshold": None,
        "health_threshold_selected": False,
        "calibration_parameter": None,
        "calibration_parameter_selected": False,
        "trained_model_artifact_sha256": None,
    }:
        raise HealthModelInterfaceError(
            "model selection occurred unexpectedly"
        )

    runtime = payload[
        "runtime_output"
    ]

    if runtime != {
        "health_state_output": "disabled",
        "health_probability_output": "disabled",
        "training_authorized": False,
        "inference_authorized": False,
    }:
        raise HealthModelInterfaceError(
            "runtime health output must remain disabled"
        )

    evidence = payload[
        "evidence_gate"
    ]

    if evidence != {
        "accepted_baseline_nominality_source_count": 0,
        "accepted_health_supervision_source_count": 0,
        "real_health_label_count": 0,
        "camera_feature_contract_selected": False,
        "imu_feature_contract_selected": False,
        "lidar_phase4_feature_contract_validated": True,
        "classifier_training_authorized": False,
        "health_inference_authorized": False,
        "physical_validation_deferred": True,
    }:
        raise HealthModelInterfaceError(
            "current evidence gate changed"
        )

    confirmation = payload[
        "confirmation_boundary"
    ]

    if confirmation != {
        "confirmation_closed": True,
        "confirmation_selection_authorized": False,
    }:
        raise HealthModelInterfaceError(
            "confirmation boundary changed"
        )

    scientific = payload[
        "scientific_boundary"
    ]

    for key, value in scientific.items():
        if value is not False:
            raise HealthModelInterfaceError(
                f"scientific boundary {key} must remain false"
            )
