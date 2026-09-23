"""Permanent compact Phase-5 camera/IMU TRAIN source-evidence contract."""

from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping
import json


SCHEMA = "TRUST_ROBOT_PHASE5_CAMERA_IMU_TRAIN_SOURCE_EVIDENCE_V1"

FINDING = (
    "REAL_M2DGR_TRAIN_CAMERA_IMU_SOURCE_EVIDENCE_FROZEN"
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

CAMERA_STREAM = "/camera/color/image_raw/compressed"
D435I_IMU_STREAM = "/camera/imu"
HANDSFREE_IMU_STREAM = "/handsfree/imu"


class CameraImuTrainSourceEvidenceError(ValueError):
    """Raised for invalid frozen camera/IMU source evidence."""


def _canonical_bytes(
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
        _canonical_bytes(payload)
    ).hexdigest()


def validate_source_evidence(
    payload: Mapping[str, Any],
) -> None:
    if not isinstance(payload, Mapping):
        raise CameraImuTrainSourceEvidenceError(
            "source evidence must be a mapping"
        )

    required = {
        "schema",
        "finding",
        "train_population",
        "ingestion_totals",
        "stream_evidence",
        "representative_feasibility",
        "source_hashes",
        "scientific_boundary",
        "content_sha256",
    }

    if set(payload) != required:
        raise CameraImuTrainSourceEvidenceError(
            "unexpected top-level evidence keys"
        )

    if payload["schema"] != SCHEMA:
        raise CameraImuTrainSourceEvidenceError(
            "unexpected schema"
        )

    if payload["finding"] != FINDING:
        raise CameraImuTrainSourceEvidenceError(
            "unexpected finding"
        )

    train = payload["train_population"]

    if train != {
        "split_role": "train",
        "trajectory_count": 22,
        "trajectory_ids": list(TRAIN_TRAJECTORIES),
        "validation_data_used": False,
        "confirmation_data_used": False,
    }:
        raise CameraImuTrainSourceEvidenceError(
            "TRAIN population differs from frozen split"
        )

    totals = payload["ingestion_totals"]

    if totals != {
        "selected_stream_messages": 2816957,
        "selected_serialized_payload_bytes": 4320203720,
    }:
        raise CameraImuTrainSourceEvidenceError(
            "unexpected verified ingestion totals"
        )

    streams = payload["stream_evidence"]

    if set(streams) != {
        CAMERA_STREAM,
        D435I_IMU_STREAM,
        HANDSFREE_IMU_STREAM,
    }:
        raise CameraImuTrainSourceEvidenceError(
            "unexpected stream set"
        )

    expected_camera = {
        "modality": "camera",
        "message_type": "sensor_msgs/msg/CompressedImage",
        "present_trajectory_count": 20,
        "absent_trajectory_count": 2,
        "absent_trajectories": [
            "street_010",
            "street_09",
        ],
        "message_count": 107675,
        "serialized_payload_bytes": 3429452123,
        "header_stamp_present_count": 107675,
    }

    if streams[CAMERA_STREAM] != expected_camera:
        raise CameraImuTrainSourceEvidenceError(
            "camera stream evidence changed"
        )

    expected_d435i = {
        "modality": "imu",
        "message_type": "sensor_msgs/msg/Imu",
        "present_trajectory_count": 20,
        "absent_trajectory_count": 2,
        "absent_trajectories": [
            "street_010",
            "street_09",
        ],
        "message_count": 1404805,
        "serialized_payload_bytes": 472014480,
        "header_stamp_present_count": 1404805,
    }

    if streams[D435I_IMU_STREAM] != expected_d435i:
        raise CameraImuTrainSourceEvidenceError(
            "D435i IMU stream evidence changed"
        )

    expected_handsfree = {
        "modality": "imu",
        "message_type": "sensor_msgs/msg/Imu",
        "present_trajectory_count": 22,
        "absent_trajectory_count": 0,
        "absent_trajectories": [],
        "message_count": 1304477,
        "serialized_payload_bytes": 418737117,
        "header_stamp_present_count": 1304477,
    }

    if streams[HANDSFREE_IMU_STREAM] != expected_handsfree:
        raise CameraImuTrainSourceEvidenceError(
            "HandsFree IMU stream evidence changed"
        )

    feasibility = payload["representative_feasibility"]

    if feasibility["representative_sample_count"] != 62:
        raise CameraImuTrainSourceEvidenceError(
            "unexpected representative sample count"
        )

    camera = feasibility["camera"]

    if camera != {
        "representative_sample_count": 20,
        "format_values": [
            "rgb8; jpeg compressed bgr8",
        ],
        "numpy_available": True,
        "opencv_available": False,
        "pillow_available": True,
        "decode_attempt_count": 20,
        "decode_success_count": 20,
    }:
        raise CameraImuTrainSourceEvidenceError(
            "camera feasibility evidence changed"
        )

    imu = feasibility["imu"]

    if imu[D435I_IMU_STREAM] != {
        "representative_sample_count": 20,
        "orientation_covariance_lengths": [9],
        "orientation_covariance_first_values": [-1.0],
        "angular_velocity_covariance_lengths": [9],
        "angular_velocity_covariance_first_values": [0.01],
        "linear_acceleration_covariance_lengths": [9],
        "linear_acceleration_covariance_first_values": [0.01],
        "finite_orientation_sample_count": 20,
        "finite_angular_velocity_sample_count": 20,
        "finite_linear_acceleration_sample_count": 20,
    }:
        raise CameraImuTrainSourceEvidenceError(
            "D435i representative IMU evidence changed"
        )

    if imu[HANDSFREE_IMU_STREAM] != {
        "representative_sample_count": 22,
        "orientation_covariance_lengths": [9],
        "orientation_covariance_first_values": [0.0],
        "angular_velocity_covariance_lengths": [9],
        "angular_velocity_covariance_first_values": [0.0],
        "linear_acceleration_covariance_lengths": [9],
        "linear_acceleration_covariance_first_values": [0.0],
        "finite_orientation_sample_count": 22,
        "finite_angular_velocity_sample_count": 22,
        "finite_linear_acceleration_sample_count": 22,
    }:
        raise CameraImuTrainSourceEvidenceError(
            "HandsFree representative IMU evidence changed"
        )

    boundary = payload["scientific_boundary"]

    expected_boundary = {
        "train_only": True,
        "representative_feasibility_is_not_full_stream_feature_validation": True,
        "camera_feature_contract_selected": False,
        "imu_feature_contract_selected": False,
        "diagnostic_feature_extraction_performed": False,
        "health_label_assigned": False,
        "health_probability_emitted": False,
        "health_threshold_selected": False,
        "classifier_model_selected": False,
        "classifier_training_authorized": False,
        "physical_measurement_time_selected": False,
        "shared_clock_domain_verified": False,
        "fixed_offset_selected": False,
        "interpolation_rule_selected": False,
        "reference_data_used": False,
        "validation_data_used": False,
        "confirmation_data_used": False,
        "ate_rpe_computed": False,
        "final_score_computed": False,
    }

    if boundary != expected_boundary:
        raise CameraImuTrainSourceEvidenceError(
            "scientific boundary changed"
        )

    value = dict(payload)
    stored = value.pop(
        "content_sha256"
    )

    actual = content_sha256(
        value
    )

    if stored != actual:
        raise CameraImuTrainSourceEvidenceError(
            "content SHA-256 mismatch"
        )
