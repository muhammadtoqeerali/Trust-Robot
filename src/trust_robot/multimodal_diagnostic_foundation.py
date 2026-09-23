"""Phase-5 multimodal diagnostic foundation.

This module defines the common modality/availability/provenance contract used
before empirical health-model training.

Scientific boundary:
- camera, IMU and GNSS diagnostic feature sets are intentionally unselected;
- the frozen Phase-4 LiDAR five-feature contract is referenced, not changed;
- availability is not a health label;
- no health probability, threshold, calibration parameter or final
  localization score is produced here;
- confirmation data are not authorized for model or threshold selection.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Any, Mapping, Optional, Sequence
import json
import re


FOUNDATION_SCHEMA = (
    "TRUST_ROBOT_PHASE5_MULTIMODAL_DIAGNOSTIC_FOUNDATION_V1"
)

FOUNDATION_CONTRACT_ID = (
    "trust_robot_phase5_multimodal_diagnostic_foundation_v1"
)

AVAILABILITY_RECEIPT_SCHEMA = (
    "TRUST_ROBOT_PHASE5_MEASUREMENT_AVAILABILITY_RECEIPT_V1"
)

PHASE4_LIDAR_FREEZE_SHA256 = (
    "09a05d8491c7af7cd8122ee58d9f485d21f03d2cd50f44764d57d48726d08e88"
)

PHASE4_LIDAR_FEATURE_CONTRACT_ID = (
    "trust_robot_phase4_validated_lidar_diagnostic_feature_contract_v1"
)

HEALTH_STATES = (
    "healthy",
    "degraded",
    "unusable",
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class MultimodalDiagnosticFoundationError(ValueError):
    """Raised when a Phase-5 multimodal diagnostic contract is invalid."""


class Modality(str, Enum):
    CAMERA = "camera"
    IMU = "imu"
    LIDAR = "lidar"
    GNSS = "gnss"


class ModalityRole(str, Enum):
    CORE = "core"
    OPTIONAL = "optional"


class FeatureContractStatus(str, Enum):
    VALIDATED_PHASE4 = "validated_phase4_feature_contract"
    INTERFACE_ONLY = "interface_only_feature_contract_unselected"


class AvailabilityState(str, Enum):
    OBSERVED_PRESENT = "observed_present"
    OBSERVED_ABSENT = "observed_absent"
    UNRESOLVED = "unresolved"


class SplitRole(str, Enum):
    TRAIN = "train"
    VALIDATION = "validation"
    CONFIRMATION = "confirmation_test"
    UNSPECIFIED = "unspecified"


@dataclass(frozen=True)
class DiagnosticFeatureSpec:
    name: str
    unit: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise MultimodalDiagnosticFoundationError(
                "diagnostic feature name must be non-empty"
            )

        if not isinstance(self.unit, str) or not self.unit.strip():
            raise MultimodalDiagnosticFoundationError(
                "diagnostic feature unit must be non-empty"
            )


@dataclass(frozen=True)
class ModalityAdapterContract:
    modality: Modality
    role: ModalityRole
    known_source_stream_candidates: tuple[str, ...]
    selected_source_stream_id: Optional[str]
    feature_contract_status: FeatureContractStatus
    feature_contract_id: Optional[str]
    feature_specs: tuple[DiagnosticFeatureSpec, ...]
    physical_validation_deferred: bool
    health_training_authorized: bool

    def __post_init__(self) -> None:
        if not self.known_source_stream_candidates:
            raise MultimodalDiagnosticFoundationError(
                "known source stream candidates must not be empty"
            )

        for source in self.known_source_stream_candidates:
            if not isinstance(source, str) or not source.strip():
                raise MultimodalDiagnosticFoundationError(
                    "source stream candidates must be non-empty strings"
                )

        if self.health_training_authorized is not False:
            raise MultimodalDiagnosticFoundationError(
                "health training is not authorized by the foundation"
            )

        if self.modality is Modality.LIDAR:
            if (
                self.feature_contract_status
                is not FeatureContractStatus.VALIDATED_PHASE4
            ):
                raise MultimodalDiagnosticFoundationError(
                    "LiDAR must bind the frozen Phase-4 feature contract"
                )

            if (
                self.feature_contract_id
                != PHASE4_LIDAR_FEATURE_CONTRACT_ID
            ):
                raise MultimodalDiagnosticFoundationError(
                    "unexpected LiDAR feature contract id"
                )

            if self.selected_source_stream_id != "/velodyne_points":
                raise MultimodalDiagnosticFoundationError(
                    "LiDAR source must remain the frozen /velodyne_points stream"
                )

            if self.feature_specs != LIDAR_FEATURE_SPECS:
                raise MultimodalDiagnosticFoundationError(
                    "LiDAR feature contract changed"
                )

        else:
            if (
                self.feature_contract_status
                is not FeatureContractStatus.INTERFACE_ONLY
            ):
                raise MultimodalDiagnosticFoundationError(
                    "non-LiDAR feature contracts are not selected"
                )

            if self.feature_contract_id is not None:
                raise MultimodalDiagnosticFoundationError(
                    "non-LiDAR feature contract id must remain unset"
                )

            if self.selected_source_stream_id is not None:
                raise MultimodalDiagnosticFoundationError(
                    "non-LiDAR diagnostic source selection remains unset"
                )

            if self.feature_specs:
                raise MultimodalDiagnosticFoundationError(
                    "non-LiDAR feature specifications remain empty"
                )


@dataclass(frozen=True)
class MeasurementAvailabilityReceipt:
    modality: Modality
    source_id: str
    trajectory_or_session_id: str
    split_role: SplitRole
    availability_state: AvailabilityState
    evidence_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise MultimodalDiagnosticFoundationError(
                "source_id must be non-empty"
            )

        if (
            not isinstance(self.trajectory_or_session_id, str)
            or not self.trajectory_or_session_id.strip()
        ):
            raise MultimodalDiagnosticFoundationError(
                "trajectory_or_session_id must be non-empty"
            )

        _require_sha256(
            self.evidence_sha256,
            "evidence_sha256",
        )


LIDAR_FEATURE_SPECS = (
    DiagnosticFeatureSpec(
        name="source_point_count",
        unit="count",
    ),
    DiagnosticFeatureSpec(
        name="target_point_count",
        unit="count",
    ),
    DiagnosticFeatureSpec(
        name="fixed_point_iterations",
        unit="count",
    ),
    DiagnosticFeatureSpec(
        name="final_correspondence_count",
        unit="count",
    ),
    DiagnosticFeatureSpec(
        name="final_nearest_neighbor_rmse_m",
        unit="m",
    ),
)


def _require_sha256(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise MultimodalDiagnosticFoundationError(
            f"{field_name} must be a lowercase SHA-256 digest"
        )

    return value


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_content_sha256(payload: Mapping[str, Any]) -> str:
    return sha256(
        _canonical_json_bytes(payload)
    ).hexdigest()


def camera_adapter_contract() -> ModalityAdapterContract:
    return ModalityAdapterContract(
        modality=Modality.CAMERA,
        role=ModalityRole.CORE,
        known_source_stream_candidates=(
            "/camera/color/image_raw/compressed",
        ),
        selected_source_stream_id=None,
        feature_contract_status=FeatureContractStatus.INTERFACE_ONLY,
        feature_contract_id=None,
        feature_specs=(),
        physical_validation_deferred=True,
        health_training_authorized=False,
    )


def imu_adapter_contract() -> ModalityAdapterContract:
    return ModalityAdapterContract(
        modality=Modality.IMU,
        role=ModalityRole.CORE,
        known_source_stream_candidates=(
            "/camera/imu",
            "/handsfree/imu",
        ),
        selected_source_stream_id=None,
        feature_contract_status=FeatureContractStatus.INTERFACE_ONLY,
        feature_contract_id=None,
        feature_specs=(),
        physical_validation_deferred=True,
        health_training_authorized=False,
    )


def lidar_adapter_contract() -> ModalityAdapterContract:
    return ModalityAdapterContract(
        modality=Modality.LIDAR,
        role=ModalityRole.CORE,
        known_source_stream_candidates=(
            "/velodyne_points",
        ),
        selected_source_stream_id="/velodyne_points",
        feature_contract_status=FeatureContractStatus.VALIDATED_PHASE4,
        feature_contract_id=PHASE4_LIDAR_FEATURE_CONTRACT_ID,
        feature_specs=LIDAR_FEATURE_SPECS,
        physical_validation_deferred=True,
        health_training_authorized=False,
    )


def gnss_adapter_contract() -> ModalityAdapterContract:
    return ModalityAdapterContract(
        modality=Modality.GNSS,
        role=ModalityRole.OPTIONAL,
        known_source_stream_candidates=(
            "/ublox/fix",
            "/ublox/navstatus",
        ),
        selected_source_stream_id=None,
        feature_contract_status=FeatureContractStatus.INTERFACE_ONLY,
        feature_contract_id=None,
        feature_specs=(),
        physical_validation_deferred=True,
        health_training_authorized=False,
    )


def modality_adapter_contracts() -> tuple[ModalityAdapterContract, ...]:
    return (
        camera_adapter_contract(),
        imu_adapter_contract(),
        lidar_adapter_contract(),
        gnss_adapter_contract(),
    )


def adapter_contract_for(
    modality: Modality | str,
) -> ModalityAdapterContract:
    try:
        normalized = (
            modality
            if isinstance(modality, Modality)
            else Modality(modality)
        )
    except (TypeError, ValueError) as exc:
        raise MultimodalDiagnosticFoundationError(
            f"unsupported modality: {modality!r}"
        ) from exc

    for contract in modality_adapter_contracts():
        if contract.modality is normalized:
            return contract

    raise MultimodalDiagnosticFoundationError(
        f"no adapter contract for modality {normalized.value}"
    )


def _feature_payload(
    feature: DiagnosticFeatureSpec,
) -> dict[str, str]:
    return {
        "name": feature.name,
        "unit": feature.unit,
    }


def _adapter_payload(
    contract: ModalityAdapterContract,
) -> dict[str, Any]:
    return {
        "modality":
            contract.modality.value,

        "role":
            contract.role.value,

        "known_source_stream_candidates":
            list(
                contract.known_source_stream_candidates
            ),

        "selected_source_stream_id":
            contract.selected_source_stream_id,

        "feature_contract_status":
            contract.feature_contract_status.value,

        "feature_contract_id":
            contract.feature_contract_id,

        "feature_specs": [
            _feature_payload(feature)
            for feature in contract.feature_specs
        ],

        "physical_validation_deferred":
            contract.physical_validation_deferred,

        "health_training_authorized":
            contract.health_training_authorized,
    }


def build_foundation_manifest() -> dict[str, Any]:
    return {
        "schema":
            FOUNDATION_SCHEMA,

        "contract_id":
            FOUNDATION_CONTRACT_ID,

        "scope": {
            "core_modalities": [
                Modality.CAMERA.value,
                Modality.IMU.value,
                Modality.LIDAR.value,
            ],

            "optional_modalities": [
                Modality.GNSS.value,
            ],

            "shared_health_states":
                list(HEALTH_STATES),

            "availability_is_health_label":
                False,

            "do_not_fabricate_missing_modalities":
                True,
        },

        "frozen_lidar_binding": {
            "phase4_freeze_sha256":
                PHASE4_LIDAR_FREEZE_SHA256,

            "feature_contract_id":
                PHASE4_LIDAR_FEATURE_CONTRACT_ID,

            "feature_names": [
                feature.name
                for feature in LIDAR_FEATURE_SPECS
            ],

            "feature_units": [
                feature.unit
                for feature in LIDAR_FEATURE_SPECS
            ],

            "feature_selection_reopened":
                False,
        },

        "modality_contracts": [
            _adapter_payload(contract)
            for contract in modality_adapter_contracts()
        ],

        "scientific_boundary": {
            "camera_feature_contract_selected":
                False,

            "imu_feature_contract_selected":
                False,

            "gnss_feature_contract_selected":
                False,

            "lidar_feature_contract_changed":
                False,

            "health_state_output_enabled":
                False,

            "health_probability_output_enabled":
                False,

            "health_threshold_selected":
                False,

            "calibration_temperature_selected":
                False,

            "classifier_model_selected":
                False,

            "classifier_training_authorized":
                False,

            "real_health_label_count":
                0,

            "final_localization_error_used_as_health_supervision":
                False,

            "ate_rpe_computation_authorized":
                False,

            "confirmation_data_selection_authorized":
                False,
        },

        "physical_validation": {
            "camera":
                "deferred",

            "imu":
                "deferred",

            "lidar":
                "phase4_diagnostic_contract_validated_"
                "health_supervision_deferred",

            "gnss":
                "optional_deferred",
        },
    }


def validate_foundation_manifest(
    payload: Mapping[str, Any],
) -> None:
    if not isinstance(payload, Mapping):
        raise MultimodalDiagnosticFoundationError(
            "foundation manifest must be a mapping"
        )

    expected = build_foundation_manifest()

    if _canonical_json_bytes(payload) != _canonical_json_bytes(expected):
        raise MultimodalDiagnosticFoundationError(
            "foundation manifest does not match the frozen candidate contract"
        )


def build_measurement_availability_receipt(
    *,
    modality: Modality | str,
    source_id: str,
    trajectory_or_session_id: str,
    split_role: SplitRole | str,
    availability_state: AvailabilityState | str,
    evidence_sha256: str,
) -> MeasurementAvailabilityReceipt:
    try:
        normalized_modality = (
            modality
            if isinstance(modality, Modality)
            else Modality(modality)
        )

        normalized_split = (
            split_role
            if isinstance(split_role, SplitRole)
            else SplitRole(split_role)
        )

        normalized_availability = (
            availability_state
            if isinstance(
                availability_state,
                AvailabilityState,
            )
            else AvailabilityState(
                availability_state
            )
        )
    except (TypeError, ValueError) as exc:
        raise MultimodalDiagnosticFoundationError(
            "invalid modality, split role, or availability state"
        ) from exc

    adapter_contract_for(
        normalized_modality
    )

    return MeasurementAvailabilityReceipt(
        modality=normalized_modality,
        source_id=source_id,
        trajectory_or_session_id=trajectory_or_session_id,
        split_role=normalized_split,
        availability_state=normalized_availability,
        evidence_sha256=evidence_sha256,
    )


def measurement_availability_receipt_payload(
    receipt: MeasurementAvailabilityReceipt,
) -> dict[str, Any]:
    contract = adapter_contract_for(
        receipt.modality
    )

    return {
        "schema":
            AVAILABILITY_RECEIPT_SCHEMA,

        "foundation_contract_id":
            FOUNDATION_CONTRACT_ID,

        "modality":
            receipt.modality.value,

        "modality_role":
            contract.role.value,

        "source_id":
            receipt.source_id,

        "trajectory_or_session_id":
            receipt.trajectory_or_session_id,

        "split_role":
            receipt.split_role.value,

        "availability_state":
            receipt.availability_state.value,

        "evidence_sha256":
            receipt.evidence_sha256,

        "health_label_assigned":
            False,

        "health_probability_emitted":
            False,

        "classifier_training_authorized":
            False,

        "final_localization_error_used":
            False,

        "confirmation_used_for_selection":
            False,
    }


def measurement_availability_receipt_content_sha256(
    receipt: MeasurementAvailabilityReceipt,
) -> str:
    return canonical_content_sha256(
        measurement_availability_receipt_payload(
            receipt
        )
    )


def validate_measurement_availability_receipt_payload(
    payload: Mapping[str, Any],
) -> None:
    if not isinstance(payload, Mapping):
        raise MultimodalDiagnosticFoundationError(
            "availability receipt must be a mapping"
        )

    exact_keys = {
        "schema",
        "foundation_contract_id",
        "modality",
        "modality_role",
        "source_id",
        "trajectory_or_session_id",
        "split_role",
        "availability_state",
        "evidence_sha256",
        "health_label_assigned",
        "health_probability_emitted",
        "classifier_training_authorized",
        "final_localization_error_used",
        "confirmation_used_for_selection",
    }

    if set(payload) != exact_keys:
        raise MultimodalDiagnosticFoundationError(
            "availability receipt has unexpected keys"
        )

    if payload["schema"] != AVAILABILITY_RECEIPT_SCHEMA:
        raise MultimodalDiagnosticFoundationError(
            "unexpected availability receipt schema"
        )

    if payload["foundation_contract_id"] != FOUNDATION_CONTRACT_ID:
        raise MultimodalDiagnosticFoundationError(
            "unexpected foundation contract id"
        )

    try:
        modality = Modality(
            payload["modality"]
        )

        split_role = SplitRole(
            payload["split_role"]
        )

        availability_state = AvailabilityState(
            payload["availability_state"]
        )
    except (TypeError, ValueError) as exc:
        raise MultimodalDiagnosticFoundationError(
            "invalid receipt enum value"
        ) from exc

    contract = adapter_contract_for(
        modality
    )

    if payload["modality_role"] != contract.role.value:
        raise MultimodalDiagnosticFoundationError(
            "modality role does not match adapter contract"
        )

    rebuilt = build_measurement_availability_receipt(
        modality=modality,
        source_id=payload["source_id"],
        trajectory_or_session_id=payload[
            "trajectory_or_session_id"
        ],
        split_role=split_role,
        availability_state=availability_state,
        evidence_sha256=payload[
            "evidence_sha256"
        ],
    )

    expected = measurement_availability_receipt_payload(
        rebuilt
    )

    if _canonical_json_bytes(payload) != _canonical_json_bytes(expected):
        raise MultimodalDiagnosticFoundationError(
            "availability receipt violates the fail-closed contract"
        )
