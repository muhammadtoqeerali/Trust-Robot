"""TRAIN-only camera/IMU ingestion aggregation for TRUST-ROBOT Phase 5.

The layer consumes raw-observation receipts from the Phase-5 camera/IMU
adapter and creates deterministic stream-level aggregate evidence.

It does not select diagnostic features, health labels, thresholds,
synchronization offsets, interpolation rules, calibration parameters,
reference associations, ATE/RPE, or final localization scores.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Mapping, Optional
import json

from .camera_imu_observation_adapter import (
    CAMERA_STREAM_ID,
    IMU_STREAM_IDS,
    RawObservationReceipt,
    receipt_payload,
)
from .multimodal_diagnostic_foundation import (
    Modality,
    SplitRole,
)


SCHEMA = (
    "TRUST_ROBOT_PHASE5_CAMERA_IMU_TRAIN_INGESTION_V1"
)

RUN_ID = (
    "trust_robot_phase5_m2dgr_camera_imu_train_ingestion_v1"
)

FROZEN_SPLIT_SHA256 = (
    "017a388ef1ce4ad30812669632a022ca37c084871bc949693fd9c0541014238f"
)

SUPPORTED_STREAMS = (
    CAMERA_STREAM_ID,
    *IMU_STREAM_IDS,
)

TRAIN_TRAJECTORIES = (
    "Circle_01",
    "door_01",
    "gate_01",
    "hall_01",
    "hall_03",
    "hall_04",
    "hall_05",
    "lift_02",
    "lift_04",
    "room_02",
    "room_dark_01",
    "room_dark_02",
    "room_dark_03",
    "room_dark_04",
    "street_01",
    "street_010",
    "street_03",
    "street_04",
    "street_05",
    "street_07",
    "street_09",
    "walk_01",
)


class CameraImuTrainIngestionError(ValueError):
    """Raised when TRAIN-ingestion evidence violates the frozen contract."""


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


def header_stamp_ns_from_message(
    message: Any,
) -> Optional[int]:
    """Return the directly represented header stamp, if structurally present.

    No physical capture-time semantics are inferred from this value.
    """

    header = getattr(
        message,
        "header",
        None,
    )

    if header is None:
        return None

    stamp = getattr(
        header,
        "stamp",
        None,
    )

    if stamp is None:
        return None

    sec = getattr(
        stamp,
        "sec",
        getattr(
            stamp,
            "secs",
            None,
        ),
    )

    nanosec = getattr(
        stamp,
        "nanosec",
        getattr(
            stamp,
            "nsec",
            getattr(
                stamp,
                "nsecs",
                None,
            ),
        ),
    )

    if sec is None or nanosec is None:
        return None

    if type(sec) is not int or type(nanosec) is not int:
        raise CameraImuTrainIngestionError(
            "header timestamp components must be exact integers"
        )

    if sec < 0 or nanosec < 0 or nanosec >= 1_000_000_000:
        raise CameraImuTrainIngestionError(
            "header timestamp components are outside structural bounds"
        )

    return (
        sec * 1_000_000_000
        + nanosec
    )


@dataclass
class StreamAggregateBuilder:
    trajectory_id: str
    source_stream_id: str
    modality: Modality
    message_type: Optional[str] = None
    message_count: int = 0
    total_serialized_payload_bytes: int = 0
    header_stamp_present_count: int = 0
    first_bag_record_time_ns: Optional[int] = None
    last_bag_record_time_ns: Optional[int] = None
    first_header_stamp_ns: Optional[int] = None
    last_header_stamp_ns: Optional[int] = None
    _rolling_digest: Any = field(
        default_factory=sha256,
        repr=False,
    )

    def add(
        self,
        receipt: RawObservationReceipt,
    ) -> None:
        if receipt.split_role is not SplitRole.TRAIN:
            raise CameraImuTrainIngestionError(
                "TRAIN ingestion accepts TRAIN receipts only"
            )

        if receipt.trajectory_or_session_id != self.trajectory_id:
            raise CameraImuTrainIngestionError(
                "receipt trajectory differs from aggregate trajectory"
            )

        if receipt.source_stream_id != self.source_stream_id:
            raise CameraImuTrainIngestionError(
                "receipt stream differs from aggregate stream"
            )

        if receipt.modality is not self.modality:
            raise CameraImuTrainIngestionError(
                "receipt modality differs from aggregate modality"
            )

        if self.message_type is None:
            self.message_type = receipt.message_type

        elif self.message_type != receipt.message_type:
            raise CameraImuTrainIngestionError(
                "message type changed inside one trajectory stream"
            )

        if receipt.message_index != self.message_count:
            raise CameraImuTrainIngestionError(
                "message indices must be contiguous from zero"
            )

        payload = receipt_payload(
            receipt
        )

        self._rolling_digest.update(
            canonical_json_bytes(
                payload
            )
        )
        self._rolling_digest.update(
            b"\n"
        )

        self.message_count += 1
        self.total_serialized_payload_bytes += (
            receipt.serialized_payload_size_bytes
        )

        if self.first_bag_record_time_ns is None:
            self.first_bag_record_time_ns = (
                receipt.bag_record_time_ns
            )

        self.last_bag_record_time_ns = (
            receipt.bag_record_time_ns
        )

        if receipt.header_stamp_ns is not None:
            self.header_stamp_present_count += 1

            if self.first_header_stamp_ns is None:
                self.first_header_stamp_ns = (
                    receipt.header_stamp_ns
                )

            self.last_header_stamp_ns = (
                receipt.header_stamp_ns
            )

    def payload(self) -> dict[str, Any]:
        present = self.message_count > 0

        return {
            "trajectory_id":
                self.trajectory_id,

            "split_role":
                "train",

            "source_stream_id":
                self.source_stream_id,

            "modality":
                self.modality.value,

            "stream_present":
                present,

            "message_type":
                self.message_type,

            "message_count":
                self.message_count,

            "total_serialized_payload_bytes":
                self.total_serialized_payload_bytes,

            "header_stamp_present_count":
                self.header_stamp_present_count,

            "first_bag_record_time_ns":
                self.first_bag_record_time_ns,

            "last_bag_record_time_ns":
                self.last_bag_record_time_ns,

            "first_header_stamp_ns":
                self.first_header_stamp_ns,

            "last_header_stamp_ns":
                self.last_header_stamp_ns,

            "aggregate_receipt_sha256":
                self._rolling_digest.hexdigest(),

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
                "feature_contract_selected":
                    False,

                "feature_extraction_performed":
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
            },
        }


def modality_for_supported_stream(
    source_stream_id: str,
) -> Modality:
    if source_stream_id == CAMERA_STREAM_ID:
        return Modality.CAMERA

    if source_stream_id in IMU_STREAM_IDS:
        return Modality.IMU

    raise CameraImuTrainIngestionError(
        f"unsupported camera/IMU stream {source_stream_id!r}"
    )


def empty_stream_builders(
    trajectory_id: str,
) -> dict[str, StreamAggregateBuilder]:
    if trajectory_id not in TRAIN_TRAJECTORIES:
        raise CameraImuTrainIngestionError(
            "trajectory is not in the frozen TRAIN set"
        )

    return {
        stream: StreamAggregateBuilder(
            trajectory_id=trajectory_id,
            source_stream_id=stream,
            modality=modality_for_supported_stream(
                stream
            ),
        )
        for stream in SUPPORTED_STREAMS
    }


def build_candidate_manifest() -> dict[str, Any]:
    return {
        "schema":
            SCHEMA,

        "run_id":
            RUN_ID,

        "frozen_split_sha256":
            FROZEN_SPLIT_SHA256,

        "split_role":
            "train",

        "train_trajectory_count":
            len(TRAIN_TRAJECTORIES),

        "train_trajectories":
            list(TRAIN_TRAJECTORIES),

        "supported_streams": {
            "camera": [
                CAMERA_STREAM_ID,
            ],

            "imu":
                list(IMU_STREAM_IDS),
        },

        "reader": {
            "package":
                "rosbags",

            "interface":
                "rosbags.highlevel.AnyReader",
        },

        "output_contract": {
            "per_message_raw_payload_written":
                False,

            "per_message_receipt_written":
                False,

            "stream_level_aggregate_receipt_digest":
                True,

            "stream_message_count":
                True,

            "stream_total_serialized_bytes":
                True,

            "first_last_record_time":
                True,

            "first_last_header_stamp_when_present":
                True,

            "missing_stream_preserved_as_absent":
                True,
        },

        "scientific_boundary": {
            "camera_feature_contract_selected":
                False,

            "imu_feature_contract_selected":
                False,

            "feature_extraction_performed":
                False,

            "health_label_assigned":
                False,

            "health_probability_emitted":
                False,

            "health_threshold_selected":
                False,

            "classifier_training_authorized":
                False,

            "physical_measurement_time_selected":
                False,

            "shared_clock_domain_verified":
                False,

            "fixed_offset_selected":
                False,

            "interpolation_rule_selected":
                False,

            "reference_data_read":
                False,

            "confirmation_bag_open_authorized":
                False,

            "ate_rpe_computation_authorized":
                False,

            "final_scoring_authorized":
                False,
        },
    }


def validate_candidate_manifest(
    payload: Mapping[str, Any],
) -> None:
    expected = build_candidate_manifest()

    if canonical_json_bytes(payload) != canonical_json_bytes(expected):
        raise CameraImuTrainIngestionError(
            "TRAIN-ingestion candidate manifest differs from frozen contract"
        )
