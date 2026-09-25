from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence
import json
import struct


FEATURE_RECORD_SCHEMA = (
    "TRUST_ROBOT_SE3_MULTIMODAL_FEATURE_RECORD_V1"
)

TRAJECTORY_SCHEMA = (
    "TRUST_ROBOT_SE3_MULTIMODAL_FEATURE_TRAJECTORY_V1"
)

RUN_SCHEMA = (
    "TRUST_ROBOT_SE3_MULTIMODAL_FEATURE_RUN_V1"
)

SUCCESS_SCHEMA = (
    "TRUST_ROBOT_SE3_MULTIMODAL_FEATURE_SUCCESS_V1"
)

CANDIDATE_SCHEMA = (
    "TRUST_ROBOT_SE3_MULTIMODAL_FEATURE_EXTRACTION_CANDIDATE_V1"
)

RUN_ID = (
    "trust_robot_se3_m2dgr_multimodal_feature_extraction_v1"
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

CAMERA_STREAM = (
    "/camera/color/image_raw/compressed"
)

IMU_STREAMS = (
    "/camera/imu",
    "/handsfree/imu",
)

SUPPORTED_STREAMS = (
    CAMERA_STREAM,
    *IMU_STREAMS,
)

STREAM_FILE_NAMES = {
    CAMERA_STREAM:
        "camera_color_image_raw_compressed.jsonl",

    "/camera/imu":
        "camera_imu.jsonl",

    "/handsfree/imu":
        "handsfree_imu.jsonl",
}

STREAM_MODALITY = {
    CAMERA_STREAM:
        "camera",

    "/camera/imu":
        "imu",

    "/handsfree/imu":
        "imu",
}

CAMERA_FEATURE_NAMES = (
    "gray_mean_intensity_8bit",
    "gray_std_intensity_8bit",
    "gray_mean_abs_neighbor_difference_8bit",
)

IMU_FEATURE_NAMES = (
    "angular_speed_norm_rad_s",
    "linear_acceleration_norm_m_s2",
)

FEATURE_CONTRACT_CONFIG_SHA256 = (
    "a71c85965b16c642adc81a190447d8935fed55c7c02a84505d0b298efeb3ef5b"
)

FEATURE_CONTRACT_CONTENT_SHA256 = (
    "323ce690d0cd563d8af798f5ca8291bfc6eb9f0556e21a90d20d6310e4e27528"
)

FROZEN_SPLIT_SHA256 = (
    "017a388ef1ce4ad30812669632a022ca37c084871bc949693fd9c0541014238f"
)


class SE3FeatureExtractionError(ValueError):
    """Raised when SE3 TRAIN feature extraction violates its contract."""


def canonical_json_bytes(
    payload: Mapping[str, Any],
) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode(
        "utf-8"
    )


def content_sha256(
    payload: Mapping[str, Any],
) -> str:
    value = dict(payload)
    value.pop(
        "content_sha256",
        None,
    )

    return sha256(
        canonical_json_bytes(
            value
        )
    ).hexdigest()


def file_sha256(
    path: Path,
) -> str:
    digest = sha256()

    with path.open(
        "rb"
    ) as handle:
        while True:
            block = handle.read(
                1024 * 1024
            )

            if not block:
                break

            digest.update(
                block
            )

    return digest.hexdigest()


def feature_names_for_stream(
    stream_id: str,
) -> tuple[str, ...]:
    if stream_id == CAMERA_STREAM:
        return CAMERA_FEATURE_NAMES

    if stream_id in IMU_STREAMS:
        return IMU_FEATURE_NAMES

    raise SE3FeatureExtractionError(
        f"unsupported stream {stream_id!r}"
    )


def stream_file_name(
    stream_id: str,
) -> str:
    try:
        return STREAM_FILE_NAMES[
            stream_id
        ]
    except KeyError as exc:
        raise SE3FeatureExtractionError(
            f"unsupported stream {stream_id!r}"
        ) from exc


@dataclass(frozen=True)
class FeatureRecord:
    trajectory_id: str
    source_stream_id: str
    selected_reader_index: int
    stream_index: int
    bag_record_time_ns: int
    header_stamp_ns: Optional[int]
    feature_values: tuple[float, ...]

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.trajectory_id,
                str,
            )
            or not self.trajectory_id
        ):
            raise SE3FeatureExtractionError(
                "trajectory_id must be non-empty"
            )

        if self.source_stream_id not in SUPPORTED_STREAMS:
            raise SE3FeatureExtractionError(
                "unsupported feature stream"
            )

        for field, value in (
            (
                "selected_reader_index",
                self.selected_reader_index,
            ),
            (
                "stream_index",
                self.stream_index,
            ),
            (
                "bag_record_time_ns",
                self.bag_record_time_ns,
            ),
        ):
            if (
                type(value) is not int
                or value < 0
            ):
                raise SE3FeatureExtractionError(
                    f"{field} must be a non-negative exact integer"
                )

        if self.header_stamp_ns is not None:
            if (
                type(
                    self.header_stamp_ns
                ) is not int
                or self.header_stamp_ns < 0
            ):
                raise SE3FeatureExtractionError(
                    "header_stamp_ns must be null or a non-negative integer"
                )

        expected_names = feature_names_for_stream(
            self.source_stream_id
        )

        if len(
            self.feature_values
        ) != len(
            expected_names
        ):
            raise SE3FeatureExtractionError(
                "feature value count differs from frozen feature contract"
            )

        if not all(
            isinstance(
                value,
                float,
            )
            and isfinite(
                value
            )
            for value in self.feature_values
        ):
            raise SE3FeatureExtractionError(
                "feature values must be finite floats"
            )


def feature_record_payload(
    record: FeatureRecord,
) -> dict[str, Any]:
    return {
        "schema":
            FEATURE_RECORD_SCHEMA,

        "trajectory_id":
            record.trajectory_id,

        "split_role":
            "train",

        "source_stream_id":
            record.source_stream_id,

        "modality":
            STREAM_MODALITY[
                record.source_stream_id
            ],

        "selected_reader_index":
            record.selected_reader_index,

        "stream_index":
            record.stream_index,

        "bag_record_time_ns":
            record.bag_record_time_ns,

        "header_stamp_ns":
            record.header_stamp_ns,

        "feature_values":
            list(
                record.feature_values
            ),
    }


def feature_record_line(
    record: FeatureRecord,
) -> bytes:
    return (
        canonical_json_bytes(
            feature_record_payload(
                record
            )
        )
        + b"\n"
    )


class FeatureStreamAccumulator:
    def __init__(
        self,
        *,
        trajectory_id: str,
        source_stream_id: str,
    ) -> None:
        if source_stream_id not in SUPPORTED_STREAMS:
            raise SE3FeatureExtractionError(
                "unsupported feature stream"
            )

        self.trajectory_id = trajectory_id
        self.source_stream_id = source_stream_id
        self.feature_names = feature_names_for_stream(
            source_stream_id
        )

        self.record_count = 0
        self.source_serialized_payload_bytes = 0

        self.first_bag_record_time_ns: Optional[int] = None
        self.last_bag_record_time_ns: Optional[int] = None

        self.first_header_stamp_ns: Optional[int] = None
        self.last_header_stamp_ns: Optional[int] = None
        self.header_stamp_present_count = 0

        self._raw_sequence_digest = sha256()
        self._feature_file_digest = sha256()

        count = len(
            self.feature_names
        )

        self._feature_min = [
            None
        ] * count

        self._feature_max = [
            None
        ] * count

        self._feature_sum = [
            0.0
        ] * count

    def add(
        self,
        *,
        raw_serialized_payload: bytes,
        record: FeatureRecord,
        serialized_line: bytes,
    ) -> None:
        if (
            record.trajectory_id
            != self.trajectory_id
        ):
            raise SE3FeatureExtractionError(
                "record trajectory differs from stream accumulator"
            )

        if (
            record.source_stream_id
            != self.source_stream_id
        ):
            raise SE3FeatureExtractionError(
                "record stream differs from stream accumulator"
            )

        if (
            record.stream_index
            != self.record_count
        ):
            raise SE3FeatureExtractionError(
                "stream index is not contiguous"
            )

        if not isinstance(
            raw_serialized_payload,
            bytes,
        ):
            raise SE3FeatureExtractionError(
                "serialized source payload must be bytes"
            )

        if not isinstance(
            serialized_line,
            bytes,
        ):
            raise SE3FeatureExtractionError(
                "serialized feature line must be bytes"
            )

        self._raw_sequence_digest.update(
            struct.pack(
                ">Q",
                len(
                    raw_serialized_payload
                ),
            )
        )

        self._raw_sequence_digest.update(
            raw_serialized_payload
        )

        self._feature_file_digest.update(
            serialized_line
        )

        self.source_serialized_payload_bytes += len(
            raw_serialized_payload
        )

        if self.first_bag_record_time_ns is None:
            self.first_bag_record_time_ns = (
                record.bag_record_time_ns
            )

        self.last_bag_record_time_ns = (
            record.bag_record_time_ns
        )

        if record.header_stamp_ns is not None:
            self.header_stamp_present_count += 1

            if self.first_header_stamp_ns is None:
                self.first_header_stamp_ns = (
                    record.header_stamp_ns
                )

            self.last_header_stamp_ns = (
                record.header_stamp_ns
            )

        for index, value in enumerate(
            record.feature_values
        ):
            current_min = self._feature_min[
                index
            ]

            current_max = self._feature_max[
                index
            ]

            if (
                current_min is None
                or value < current_min
            ):
                self._feature_min[
                    index
                ] = value

            if (
                current_max is None
                or value > current_max
            ):
                self._feature_max[
                    index
                ] = value

            self._feature_sum[
                index
            ] += value

        self.record_count += 1

    def summary(
        self,
        *,
        feature_file_relative_path: Optional[str],
    ) -> dict[str, Any]:
        if self.record_count == 0:
            if feature_file_relative_path is not None:
                raise SE3FeatureExtractionError(
                    "absent stream cannot have feature file"
                )

            feature_statistics = None
            feature_file_sha256 = None
            raw_sequence_sha256 = None

        else:
            if feature_file_relative_path is None:
                raise SE3FeatureExtractionError(
                    "present stream requires feature file"
                )

            feature_statistics = {
                name: {
                    "min":
                        self._feature_min[
                            index
                        ],

                    "max":
                        self._feature_max[
                            index
                        ],

                    "mean":
                        (
                            self._feature_sum[
                                index
                            ]
                            / self.record_count
                        ),
                }
                for index, name
                in enumerate(
                    self.feature_names
                )
            }

            feature_file_sha256 = (
                self._feature_file_digest.hexdigest()
            )

            raw_sequence_sha256 = (
                self._raw_sequence_digest.hexdigest()
            )

        return {
            "source_stream_id":
                self.source_stream_id,

            "modality":
                STREAM_MODALITY[
                    self.source_stream_id
                ],

            "availability":
                (
                    "observed_present"
                    if self.record_count
                    else "observed_absent"
                ),

            "feature_names":
                list(
                    self.feature_names
                ),

            "feature_record_count":
                self.record_count,

            "source_serialized_payload_bytes":
                self.source_serialized_payload_bytes,

            "source_raw_sequence_sha256":
                raw_sequence_sha256,

            "feature_file_relative_path":
                feature_file_relative_path,

            "feature_file_sha256":
                feature_file_sha256,

            "first_bag_record_time_ns":
                self.first_bag_record_time_ns,

            "last_bag_record_time_ns":
                self.last_bag_record_time_ns,

            "header_stamp_present_count":
                self.header_stamp_present_count,

            "first_header_stamp_ns":
                self.first_header_stamp_ns,

            "last_header_stamp_ns":
                self.last_header_stamp_ns,

            "feature_statistics":
                feature_statistics,

            "scientific_boundary": {
                "health_label":
                    None,

                "health_probability":
                    None,

                "threshold":
                    None,

                "normalization":
                    None,

                "temporal_aggregation":
                    None,

                "physical_measurement_time_inferred":
                    False,

                "cross_modal_alignment_performed":
                    False,
            },
        }


def build_candidate_manifest(
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema":
            CANDIDATE_SCHEMA,

        "run_id":
            RUN_ID,

        "split_role":
            "train",

        "frozen_split_sha256":
            FROZEN_SPLIT_SHA256,

        "train_trajectory_count":
            len(
                TRAIN_TRAJECTORIES
            ),

        "train_trajectories":
            list(
                TRAIN_TRAJECTORIES
            ),

        "supported_streams":
            {
                "camera": [
                    CAMERA_STREAM
                ],

                "imu":
                    list(
                        IMU_STREAMS
                    ),
            },

        "feature_contract": {
            "config_sha256":
                FEATURE_CONTRACT_CONFIG_SHA256,

            "content_sha256":
                FEATURE_CONTRACT_CONTENT_SHA256,

            "camera_feature_names":
                list(
                    CAMERA_FEATURE_NAMES
                ),

            "imu_feature_names":
                list(
                    IMU_FEATURE_NAMES
                ),

            "lidar_contract_reopened":
                False,
        },

        "output_contract": {
            "per_stream_feature_jsonl":
                True,

            "per_trajectory_summary_json":
                True,

            "run_manifest_json":
                True,

            "success_receipt_json":
                True,

            "raw_source_payload_persisted":
                False,

            "source_raw_sequence_sha256":
                True,

            "missing_stream_file_fabricated":
                False,

            "missing_stream_zero_vector_fabricated":
                False,
        },

        "timing_boundary": {
            "bag_record_time_role":
                "transport_or_container_time_only",

            "header_stamp_role":
                "preserved_when_recorded_no_physical_semantics_inferred",

            "shared_clock_domain_verified":
                False,

            "fixed_offset_selected":
                False,

            "interpolation_rule_selected":
                False,

            "cross_modal_alignment_performed":
                False,
        },

        "scientific_boundary": {
            "train_only":
                True,

            "validation_bags_open_authorized":
                False,

            "confirmation_bags_open_authorized":
                False,

            "reference_data_read_authorized":
                False,

            "health_labels_assigned":
                False,

            "health_probabilities_emitted":
                False,

            "health_threshold_selected":
                False,

            "supervised_feature_selection_performed":
                False,

            "model_training_authorized":
                False,

            "calibration_authorized":
                False,

            "ate_rpe_authorized":
                False,

            "final_scoring_authorized":
                False,
        },
    }

    payload[
        "content_sha256"
    ] = content_sha256(
        payload
    )

    return payload


def validate_candidate_manifest(
    payload: Mapping[str, Any],
) -> None:
    if dict(
        payload
    ) != build_candidate_manifest():
        raise SE3FeatureExtractionError(
            "SE3 extraction candidate differs from frozen contract"
        )
