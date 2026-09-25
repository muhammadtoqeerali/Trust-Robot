from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from math import isfinite, sqrt
from typing import Mapping, Sequence
import json

import numpy as np
from PIL import Image


SCHEMA = (
    "TRUST_ROBOT_SE3_MULTIMODAL_FEATURE_CONTRACT_V1"
)

CONTRACT_ID = (
    "trust_robot_se3_multimodal_feature_contract_v1"
)

CAMERA_CONTRACT_ID = (
    "trust_robot_se3_camera_low_level_feature_contract_v1"
)

IMU_CONTRACT_ID = (
    "trust_robot_se3_imu_low_level_feature_contract_v1"
)

LIDAR_CONTRACT_ID = (
    "trust_robot_phase4_validated_lidar_diagnostic_feature_contract_v1"
)

CAMERA_STREAM = (
    "/camera/color/image_raw/compressed"
)

IMU_STREAMS = (
    "/camera/imu",
    "/handsfree/imu",
)

LIDAR_STREAM = (
    "/velodyne_points"
)

PHASE4_LIDAR_FREEZE_SHA256 = (
    "09a05d8491c7af7cd8122ee58d9f485d21f03d2cd50f44764d57d48726d08e88"
)

SE2_FREEZE_SHA256 = (
    "63da52c788208ae715abc7e0b8eb0ba6777cc16d33d90466332779c630618230"
)

TRAIN_SOURCE_EVIDENCE_SHA256 = (
    "d4d2a73ddbcf73102cec0d0d4556fa65786a408217fefe1dece0f4d402cce675"
)

PHASE5_CHANNEL_CONTRACT_SHA256 = (
    "de6656d35e24162dcd3ff489f21b735396c2457dae526a13be9790bb88bdf485"
)


class SE3FeatureContractError(ValueError):
    """Raised when the SE3 feature contract is violated."""


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    unit: str
    definition: str

    def __post_init__(self) -> None:
        for field_name, value in (
            ("name", self.name),
            ("unit", self.unit),
            ("definition", self.definition),
        ):
            if (
                not isinstance(value, str)
                or not value.strip()
            ):
                raise SE3FeatureContractError(
                    f"{field_name} must be non-empty"
                )


CAMERA_FEATURE_SPECS = (
    FeatureSpec(
        name="gray_mean_intensity_8bit",
        unit="gray_level",
        definition=(
            "Arithmetic mean of all pixels after deterministic Pillow "
            "conversion of the compressed image to 8-bit grayscale."
        ),
    ),
    FeatureSpec(
        name="gray_std_intensity_8bit",
        unit="gray_level",
        definition=(
            "Population standard deviation of all pixels after deterministic "
            "conversion to 8-bit grayscale; ddof=0."
        ),
    ),
    FeatureSpec(
        name="gray_mean_abs_neighbor_difference_8bit",
        unit="gray_level",
        definition=(
            "Mean absolute intensity difference over all horizontally and "
            "vertically adjacent grayscale pixel pairs, pooling both "
            "directions by pair count."
        ),
    ),
)

IMU_FEATURE_SPECS = (
    FeatureSpec(
        name="angular_speed_norm_rad_s",
        unit="rad/s",
        definition=(
            "Euclidean norm sqrt(wx^2 + wy^2 + wz^2) of the directly "
            "recorded angular_velocity vector."
        ),
    ),
    FeatureSpec(
        name="linear_acceleration_norm_m_s2",
        unit="m/s^2",
        definition=(
            "Euclidean norm sqrt(ax^2 + ay^2 + az^2) of the directly "
            "recorded linear_acceleration vector."
        ),
    ),
)

LIDAR_FEATURE_NAMES = (
    "source_point_count",
    "target_point_count",
    "fixed_point_iterations",
    "final_correspondence_count",
    "final_nearest_neighbor_rmse_m",
)

LIDAR_FEATURE_UNITS = (
    "count",
    "count",
    "count",
    "count",
    "m",
)


def _canonical_json(
    value: object,
) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode(
        "utf-8"
    )


def content_sha256(
    payload: Mapping[str, object],
) -> str:
    value = dict(payload)
    value.pop(
        "content_sha256",
        None,
    )

    return sha256(
        _canonical_json(
            value
        )
    ).hexdigest()


def _finite_float(
    value: object,
    field: str,
) -> float:
    if isinstance(value, bool):
        raise SE3FeatureContractError(
            f"{field} must be a finite real number"
        )

    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise SE3FeatureContractError(
            f"{field} must be a finite real number"
        ) from exc

    if not isfinite(normalized):
        raise SE3FeatureContractError(
            f"{field} must be finite"
        )

    return normalized


def _xyz(
    values: Sequence[object],
    field: str,
) -> tuple[float, float, float]:
    if isinstance(
        values,
        (
            str,
            bytes,
            bytearray,
        ),
    ):
        raise SE3FeatureContractError(
            f"{field} must contain exactly three values"
        )

    if len(values) != 3:
        raise SE3FeatureContractError(
            f"{field} must contain exactly three values"
        )

    return (
        _finite_float(
            values[0],
            f"{field}[0]",
        ),
        _finite_float(
            values[1],
            f"{field}[1]",
        ),
        _finite_float(
            values[2],
            f"{field}[2]",
        ),
    )


def extract_camera_features_from_gray(
    gray: np.ndarray,
) -> tuple[float, float, float]:
    """Extract the frozen SE3 camera low-level feature vector.

    No thresholding, normalization, health mapping, temporal aggregation,
    reference data, or cross-modal synchronization is used.
    """

    array = np.asarray(
        gray
    )

    if array.ndim != 2:
        raise SE3FeatureContractError(
            "camera grayscale array must be exactly 2D"
        )

    if (
        array.shape[0] < 2
        or array.shape[1] < 2
    ):
        raise SE3FeatureContractError(
            "camera grayscale array must be at least 2x2"
        )

    if array.dtype != np.uint8:
        raise SE3FeatureContractError(
            "camera grayscale array must use uint8 pixels"
        )

    values = array.astype(
        np.float64,
        copy=False,
    )

    mean = float(
        np.mean(
            values,
            dtype=np.float64,
        )
    )

    std = float(
        np.std(
            values,
            dtype=np.float64,
            ddof=0,
        )
    )

    horizontal = np.abs(
        np.diff(
            values,
            axis=1,
        )
    )

    vertical = np.abs(
        np.diff(
            values,
            axis=0,
        )
    )

    neighbor_difference = float(
        (
            float(
                horizontal.sum(
                    dtype=np.float64
                )
            )
            + float(
                vertical.sum(
                    dtype=np.float64
                )
            )
        )
        / (
            horizontal.size
            + vertical.size
        )
    )

    result = (
        mean,
        std,
        neighbor_difference,
    )

    if not all(
        isfinite(value)
        for value in result
    ):
        raise SE3FeatureContractError(
            "camera feature extraction produced non-finite output"
        )

    return result


def decode_camera_grayscale(
    compressed_payload: bytes,
) -> np.ndarray:
    """Decode a compressed camera payload deterministically via Pillow."""

    if not isinstance(
        compressed_payload,
        bytes,
    ):
        raise SE3FeatureContractError(
            "compressed camera payload must be bytes"
        )

    if not compressed_payload:
        raise SE3FeatureContractError(
            "compressed camera payload must not be empty"
        )

    try:
        with Image.open(
            BytesIO(
                compressed_payload
            )
        ) as image:
            gray = np.asarray(
                image.convert(
                    "L"
                ),
                dtype=np.uint8,
            )
    except Exception as exc:
        raise SE3FeatureContractError(
            "compressed camera payload cannot be decoded"
        ) from exc

    if gray.ndim != 2:
        raise SE3FeatureContractError(
            "decoded camera image is not 2D grayscale"
        )

    return gray


def extract_camera_features(
    compressed_payload: bytes,
) -> tuple[float, float, float]:
    return extract_camera_features_from_gray(
        decode_camera_grayscale(
            compressed_payload
        )
    )


def extract_imu_features(
    angular_velocity_xyz: Sequence[object],
    linear_acceleration_xyz: Sequence[object],
) -> tuple[float, float]:
    """Extract frame-invariant low-level IMU magnitudes.

    Orientation and covariance fields are intentionally excluded because the
    verified TRAIN streams expose materially different orientation/covariance
    semantics and no common physical interpretation is established here.
    """

    wx, wy, wz = _xyz(
        angular_velocity_xyz,
        "angular_velocity_xyz",
    )

    ax, ay, az = _xyz(
        linear_acceleration_xyz,
        "linear_acceleration_xyz",
    )

    angular_speed = sqrt(
        wx * wx
        + wy * wy
        + wz * wz
    )

    linear_acceleration = sqrt(
        ax * ax
        + ay * ay
        + az * az
    )

    result = (
        angular_speed,
        linear_acceleration,
    )

    if not all(
        isfinite(value)
        for value in result
    ):
        raise SE3FeatureContractError(
            "IMU feature extraction produced non-finite output"
        )

    return result


def _feature_payload(
    spec: FeatureSpec,
) -> dict[str, str]:
    return {
        "name":
            spec.name,

        "unit":
            spec.unit,

        "definition":
            spec.definition,
    }


def build_feature_contract_manifest(
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema":
            SCHEMA,

        "schema_version":
            1,

        "contract_id":
            CONTRACT_ID,

        "stage": {
            "stage_id":
                "SE3",

            "stage_name":
                "multimodal_feature_pipeline",

            "status":
                "exact_camera_imu_contracts_resolved_train_extraction_pending",
        },

        "resolution_basis": {
            "mode":
                "prospective_measurement_semantics",

            "supervised_feature_ranking_used":
                False,

            "health_labels_used":
                False,

            "validation_used":
                False,

            "confirmation_used":
                False,

            "reference_trajectory_used":
                False,

            "final_localization_error_used":
                False,

            "historical_missing_feature_basis_artifacts_reconstructed":
                False,

            "historical_phase5_unselected_contract_overwritten":
                False,
        },

        "camera": {
            "contract_id":
                CAMERA_CONTRACT_ID,

            "source_stream":
                CAMERA_STREAM,

            "message_type":
                "sensor_msgs/msg/CompressedImage",

            "decoded_representation":
                "Pillow_L_uint8_grayscale",

            "feature_specs": [
                _feature_payload(
                    spec
                )
                for spec in CAMERA_FEATURE_SPECS
            ],

            "feature_count":
                len(
                    CAMERA_FEATURE_SPECS
                ),

            "temporal_aggregation":
                "none_per_message",

            "normalization":
                "none",

            "thresholding":
                "none",

            "health_semantics":
                "none",
        },

        "imu": {
            "contract_id":
                IMU_CONTRACT_ID,

            "source_streams":
                list(
                    IMU_STREAMS
                ),

            "message_type":
                "sensor_msgs/msg/Imu",

            "feature_specs": [
                _feature_payload(
                    spec
                )
                for spec in IMU_FEATURE_SPECS
            ],

            "feature_count":
                len(
                    IMU_FEATURE_SPECS
                ),

            "orientation_used":
                False,

            "covariance_used":
                False,

            "raw_axes_emitted_as_features":
                False,

            "temporal_aggregation":
                "none_per_message",

            "normalization":
                "none",

            "thresholding":
                "none",

            "health_semantics":
                "none",
        },

        "lidar": {
            "contract_id":
                LIDAR_CONTRACT_ID,

            "source_stream":
                LIDAR_STREAM,

            "phase4_freeze_sha256":
                PHASE4_LIDAR_FREEZE_SHA256,

            "feature_names":
                list(
                    LIDAR_FEATURE_NAMES
                ),

            "feature_units":
                list(
                    LIDAR_FEATURE_UNITS
                ),

            "feature_count":
                len(
                    LIDAR_FEATURE_NAMES
                ),

            "contract_changed":
                False,

            "feature_reselection_performed":
                False,
        },

        "missing_measurement_policy": {
            "missing_stream_is_zero_vector":
                False,

            "missing_record_is_zero_vector":
                False,

            "missing_measurement_preserved_as_absent":
                True,

            "cross_modal_imputation_authorized":
                False,
        },

        "timing_boundary": {
            "bag_record_time_is_physical_measurement_time":
                False,

            "header_stamp_proves_shared_clock":
                False,

            "cross_modal_synchronization_selected":
                False,

            "fixed_offset_selected":
                False,

            "interpolation_selected":
                False,

            "feature_extraction_requires_cross_modal_alignment":
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

            "supervised_feature_selection_performed":
                False,

            "parameter_tuning_performed":
                False,

            "validation_access":
                False,

            "confirmation_access":
                False,

            "reference_data_access":
                False,

            "ate_rpe_computed":
                False,

            "final_scoring_performed":
                False,
        },

        "empirical_status": {
            "camera_train_source_evidence_available":
                True,

            "imu_train_source_evidence_available":
                True,

            "camera_exact_contract_resolved":
                True,

            "imu_exact_contract_resolved":
                True,

            "lidar_frozen_contract_preserved":
                True,

            "full_train_camera_feature_extraction_completed":
                False,

            "full_train_imu_feature_extraction_completed":
                False,

            "SE3_complete":
                False,
        },

        "source_bindings": {
            "SE2_freeze_sha256":
                SE2_FREEZE_SHA256,

            "phase4_lidar_freeze_sha256":
                PHASE4_LIDAR_FREEZE_SHA256,

            "phase5_camera_imu_train_source_evidence_sha256":
                TRAIN_SOURCE_EVIDENCE_SHA256,

            "phase5_camera_imu_diagnostic_channel_contract_sha256":
                PHASE5_CHANNEL_CONTRACT_SHA256,
        },

        "next_action": {
            "stage":
                "SE3",

            "action":
                "execute_and_validate_exact_features_on_frozen_TRAIN_only",

            "SE4_model_training_authorized":
                False,
        },
    }

    payload[
        "content_sha256"
    ] = content_sha256(
        payload
    )

    return payload


def validate_feature_contract_manifest(
    payload: Mapping[str, object],
) -> None:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise SE3FeatureContractError(
            "feature-contract manifest must be a mapping"
        )

    expected = build_feature_contract_manifest()

    if dict(payload) != expected:
        raise SE3FeatureContractError(
            "SE3 feature-contract manifest differs from frozen definition"
        )

    if payload.get(
        "content_sha256"
    ) != content_sha256(
        payload
    ):
        raise SE3FeatureContractError(
            "SE3 feature-contract content digest mismatch"
        )
