"""M2DGR camera/IMU raw-observation adaptation for Phase 5.

This layer preserves directly observed serialized-message provenance and timing
fields without selecting diagnostic features or inferring physical timing.

Important boundaries:
- bag record time is transport/container time only;
- header timestamp presence does not prove physical capture semantics;
- no fixed offset, interpolation or synchronization mapping is selected;
- camera and IMU diagnostic feature contracts remain unselected;
- no healthy/degraded/unusable label or probability is emitted.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping, Optional
import json
import re

from .multimodal_diagnostic_foundation import (
    Modality,
    SplitRole,
    adapter_contract_for,
)


SCHEMA = (
    "TRUST_ROBOT_PHASE5_CAMERA_IMU_RAW_OBSERVATION_RECEIPT_V1"
)

ADAPTER_ID = (
    "trust_robot_phase5_m2dgr_camera_imu_raw_observation_adapter_v1"
)

CAMERA_STREAM_ID = "/camera/color/image_raw/compressed"

IMU_STREAM_IDS = (
    "/camera/imu",
    "/handsfree/imu",
)

SUPPORTED_STREAMS = (
    CAMERA_STREAM_ID,
    *IMU_STREAM_IDS,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class CameraImuObservationAdapterError(ValueError):
    """Raised when a raw camera/IMU observation receipt is invalid."""


@dataclass(frozen=True)
class RawObservationReceipt:
    modality: Modality
    source_stream_id: str
    trajectory_or_session_id: str
    split_role: SplitRole
    message_index: int
    serialized_payload_size_bytes: int
    serialized_payload_sha256: str
    bag_record_time_ns: int
    header_stamp_ns: Optional[int]
    message_type: str

    def __post_init__(self) -> None:
        if self.modality not in (
            Modality.CAMERA,
            Modality.IMU,
        ):
            raise CameraImuObservationAdapterError(
                "adapter supports camera and IMU only"
            )

        _validate_stream_for_modality(
            self.modality,
            self.source_stream_id,
        )

        if (
            not isinstance(self.trajectory_or_session_id, str)
            or not self.trajectory_or_session_id.strip()
        ):
            raise CameraImuObservationAdapterError(
                "trajectory_or_session_id must be non-empty"
            )

        _exact_nonnegative_int(
            self.message_index,
            "message_index",
        )

        _exact_nonnegative_int(
            self.serialized_payload_size_bytes,
            "serialized_payload_size_bytes",
        )

        _sha256(
            self.serialized_payload_sha256,
            "serialized_payload_sha256",
        )

        _exact_nonnegative_int(
            self.bag_record_time_ns,
            "bag_record_time_ns",
        )

        if self.header_stamp_ns is not None:
            _exact_nonnegative_int(
                self.header_stamp_ns,
                "header_stamp_ns",
            )

        if not isinstance(self.message_type, str) or not self.message_type.strip():
            raise CameraImuObservationAdapterError(
                "message_type must be non-empty"
            )


def _exact_nonnegative_int(value: int, field: str) -> int:
    if type(value) is not int or value < 0:
        raise CameraImuObservationAdapterError(
            f"{field} must be an exact non-negative integer"
        )

    return value


def _sha256(value: str, field: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise CameraImuObservationAdapterError(
            f"{field} must be a lowercase SHA-256 digest"
        )

    return value


def _canonical_json(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def content_sha256(payload: Mapping[str, Any]) -> str:
    return sha256(
        _canonical_json(payload)
    ).hexdigest()


def _validate_stream_for_modality(
    modality: Modality,
    source_stream_id: str,
) -> None:
    if modality is Modality.CAMERA:
        if source_stream_id != CAMERA_STREAM_ID:
            raise CameraImuObservationAdapterError(
                "camera observation must use the known M2DGR color stream"
            )

    elif modality is Modality.IMU:
        if source_stream_id not in IMU_STREAM_IDS:
            raise CameraImuObservationAdapterError(
                "IMU observation must use a known M2DGR IMU stream"
            )

    else:
        raise CameraImuObservationAdapterError(
            "unsupported modality"
        )


def modality_for_stream(
    source_stream_id: str,
) -> Modality:
    if source_stream_id == CAMERA_STREAM_ID:
        return Modality.CAMERA

    if source_stream_id in IMU_STREAM_IDS:
        return Modality.IMU

    raise CameraImuObservationAdapterError(
        f"unsupported source stream: {source_stream_id!r}"
    )


def build_raw_observation_receipt(
    *,
    source_stream_id: str,
    trajectory_or_session_id: str,
    split_role: SplitRole | str,
    message_index: int,
    serialized_payload: bytes,
    bag_record_time_ns: int,
    header_stamp_ns: Optional[int],
    message_type: str,
) -> RawObservationReceipt:
    if not isinstance(serialized_payload, bytes):
        raise CameraImuObservationAdapterError(
            "serialized_payload must be bytes"
        )

    try:
        normalized_split = (
            split_role
            if isinstance(split_role, SplitRole)
            else SplitRole(split_role)
        )
    except (TypeError, ValueError) as exc:
        raise CameraImuObservationAdapterError(
            "invalid split role"
        ) from exc

    modality = modality_for_stream(
        source_stream_id
    )

    # Guard that the stream belongs to a declared common-modality adapter.
    adapter_contract_for(
        modality
    )

    return RawObservationReceipt(
        modality=modality,
        source_stream_id=source_stream_id,
        trajectory_or_session_id=trajectory_or_session_id,
        split_role=normalized_split,
        message_index=message_index,
        serialized_payload_size_bytes=len(
            serialized_payload
        ),
        serialized_payload_sha256=sha256(
            serialized_payload
        ).hexdigest(),
        bag_record_time_ns=bag_record_time_ns,
        header_stamp_ns=header_stamp_ns,
        message_type=message_type,
    )


def receipt_payload(
    receipt: RawObservationReceipt,
) -> dict[str, Any]:
    return {
        "schema":
            SCHEMA,

        "adapter_id":
            ADAPTER_ID,

        "modality":
            receipt.modality.value,

        "source_stream_id":
            receipt.source_stream_id,

        "trajectory_or_session_id":
            receipt.trajectory_or_session_id,

        "split_role":
            receipt.split_role.value,

        "message_index":
            receipt.message_index,

        "message_type":
            receipt.message_type,

        "serialized_payload_size_bytes":
            receipt.serialized_payload_size_bytes,

        "serialized_payload_sha256":
            receipt.serialized_payload_sha256,

        "bag_record_time_ns":
            receipt.bag_record_time_ns,

        "header_stamp_ns":
            receipt.header_stamp_ns,

        "timing_semantics": {
            "bag_record_time_role":
                "transport_or_container_time_only",

            "header_stamp_present":
                receipt.header_stamp_ns is not None,

            "header_stamp_physical_capture_semantics_verified":
                False,

            "shared_clock_domain_verified":
                False,

            "fixed_offset_selected":
                False,

            "interpolation_rule_selected":
                False,

            "physical_measurement_time_selected":
                False,
        },

        "diagnostic_boundary": {
            "feature_contract_selected":
                False,

            "feature_vector_emitted":
                False,

            "aggregation_performed":
                False,

            "normalization_performed":
                False,
        },

        "health_boundary": {
            "health_label_assigned":
                False,

            "health_probability_emitted":
                False,

            "health_threshold_selected":
                False,

            "classifier_training_authorized":
                False,

            "final_localization_error_used":
                False,

            "confirmation_used_for_selection":
                False,
        },
    }


def receipt_content_sha256(
    receipt: RawObservationReceipt,
) -> str:
    return content_sha256(
        receipt_payload(
            receipt
        )
    )


def validate_receipt_payload(
    payload: Mapping[str, Any],
) -> None:
    if not isinstance(payload, Mapping):
        raise CameraImuObservationAdapterError(
            "receipt payload must be a mapping"
        )

    required = {
        "schema",
        "adapter_id",
        "modality",
        "source_stream_id",
        "trajectory_or_session_id",
        "split_role",
        "message_index",
        "message_type",
        "serialized_payload_size_bytes",
        "serialized_payload_sha256",
        "bag_record_time_ns",
        "header_stamp_ns",
        "timing_semantics",
        "diagnostic_boundary",
        "health_boundary",
    }

    if set(payload) != required:
        raise CameraImuObservationAdapterError(
            "receipt payload keys differ from the frozen adapter contract"
        )

    if payload["schema"] != SCHEMA:
        raise CameraImuObservationAdapterError(
            "unexpected receipt schema"
        )

    if payload["adapter_id"] != ADAPTER_ID:
        raise CameraImuObservationAdapterError(
            "unexpected adapter id"
        )

    try:
        modality = Modality(
            payload["modality"]
        )

        split_role = SplitRole(
            payload["split_role"]
        )
    except (TypeError, ValueError) as exc:
        raise CameraImuObservationAdapterError(
            "invalid modality or split role"
        ) from exc

    _validate_stream_for_modality(
        modality,
        payload["source_stream_id"],
    )

    _exact_nonnegative_int(
        payload["message_index"],
        "message_index",
    )

    _exact_nonnegative_int(
        payload["serialized_payload_size_bytes"],
        "serialized_payload_size_bytes",
    )

    _sha256(
        payload["serialized_payload_sha256"],
        "serialized_payload_sha256",
    )

    _exact_nonnegative_int(
        payload["bag_record_time_ns"],
        "bag_record_time_ns",
    )

    if payload["header_stamp_ns"] is not None:
        _exact_nonnegative_int(
            payload["header_stamp_ns"],
            "header_stamp_ns",
        )

    if (
        not isinstance(payload["message_type"], str)
        or not payload["message_type"].strip()
    ):
        raise CameraImuObservationAdapterError(
            "message_type must be non-empty"
        )

    timing = payload["timing_semantics"]

    expected_timing = {
        "bag_record_time_role":
            "transport_or_container_time_only",

        "header_stamp_present":
            payload["header_stamp_ns"] is not None,

        "header_stamp_physical_capture_semantics_verified":
            False,

        "shared_clock_domain_verified":
            False,

        "fixed_offset_selected":
            False,

        "interpolation_rule_selected":
            False,

        "physical_measurement_time_selected":
            False,
    }

    if timing != expected_timing:
        raise CameraImuObservationAdapterError(
            "timing semantics violate the fail-closed contract"
        )

    expected_diagnostic = {
        "feature_contract_selected":
            False,

        "feature_vector_emitted":
            False,

        "aggregation_performed":
            False,

        "normalization_performed":
            False,
    }

    if payload["diagnostic_boundary"] != expected_diagnostic:
        raise CameraImuObservationAdapterError(
            "diagnostic boundary violates the fail-closed contract"
        )

    expected_health = {
        "health_label_assigned":
            False,

        "health_probability_emitted":
            False,

        "health_threshold_selected":
            False,

        "classifier_training_authorized":
            False,

        "final_localization_error_used":
            False,

        "confirmation_used_for_selection":
            False,
    }

    if payload["health_boundary"] != expected_health:
        raise CameraImuObservationAdapterError(
            "health boundary violates the fail-closed contract"
        )

    # Confirmation receipts may preserve raw evidence but may not authorize
    # any selection operation.
    if split_role is SplitRole.CONFIRMATION:
        if payload["health_boundary"]["confirmation_used_for_selection"]:
            raise CameraImuObservationAdapterError(
                "confirmation data cannot be used for selection"
            )


def build_adapter_manifest() -> dict[str, Any]:
    return {
        "schema":
            "TRUST_ROBOT_PHASE5_CAMERA_IMU_OBSERVATION_ADAPTER_CANDIDATE_V1",

        "adapter_id":
            ADAPTER_ID,

        "supported_streams": {
            "camera": [
                CAMERA_STREAM_ID,
            ],

            "imu": list(
                IMU_STREAM_IDS
            ),
        },

        "raw_observation_contract": {
            "serialized_payload_preserved_by_sha256":
                True,

            "serialized_payload_size_preserved":
                True,

            "bag_record_time_preserved":
                True,

            "header_stamp_preserved_when_supplied":
                True,

            "payload_decoding_required":
                False,
        },

        "timing_boundary": {
            "bag_record_time_is_physical_measurement_time":
                False,

            "header_stamp_physical_capture_semantics_verified":
                False,

            "shared_clock_domain_verified":
                False,

            "fixed_offset_selected":
                False,

            "interpolation_rule_selected":
                False,
        },

        "diagnostic_boundary": {
            "camera_feature_contract_selected":
                False,

            "imu_feature_contract_selected":
                False,

            "feature_extraction_performed":
                False,

            "aggregation_performed":
                False,

            "normalization_performed":
                False,
        },

        "health_boundary": {
            "real_health_label_count":
                0,

            "health_state_output_enabled":
                False,

            "health_probability_output_enabled":
                False,

            "health_threshold_selected":
                False,

            "classifier_training_authorized":
                False,

            "final_localization_error_used_as_supervision":
                False,

            "confirmation_selection_authorized":
                False,
        },
    }


def validate_adapter_manifest(
    payload: Mapping[str, Any],
) -> None:
    expected = build_adapter_manifest()

    if _canonical_json(payload) != _canonical_json(expected):
        raise CameraImuObservationAdapterError(
            "adapter manifest differs from the frozen candidate contract"
        )
