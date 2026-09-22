from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Iterable, Mapping
import json

import numpy as np

from .corruption import (
    EventStream,
    SensorModality,
)
from .lidar_frontend import (
    EXPECTED_FIELDS,
    EXPECTED_FRAME_ID,
    EXPECTED_MSGTYPE,
    EXPECTED_POINT_STEP,
    EXPECTED_TOPIC,
    decode_m2dgr_velodyne_xyz,
    pointcloud_field_descriptors,
    pointcloud_header_stamp_ns,
)


ADAPTER_SCHEMA = "TRUST_ROBOT_PHASE3_M2DGR_VELODYNE_CLEAN_ADAPTER_V1"
ADAPTER_ID = "m2dgr_velodyne_phase2_xyz_clean_adapter_v1"


class LidarCorruptionAdapterError(ValueError):
    """Raised when the clean Phase-3 LiDAR adapter contract is violated."""


def _canonical_json(
    value: object,
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _content_sha256(
    payload: Mapping[str, Any],
) -> str:
    value = dict(
        payload
    )

    value.pop(
        "content_sha256",
        None,
    )

    return sha256(
        _canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def _raw_pointcloud_data_bytes(
    message,
) -> bytes:
    data = getattr(
        message,
        "data",
        None,
    )

    if data is None:
        raise LidarCorruptionAdapterError(
            "PointCloud2 message has no data buffer"
        )

    try:
        raw = memoryview(
            data
        ).cast(
            "B"
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise LidarCorruptionAdapterError(
            "PointCloud2 data does not expose a contiguous byte buffer"
        ) from exc

    return raw.tobytes()


def _array_data_sha256(
    array: np.ndarray,
) -> str:
    return sha256(
        np.ascontiguousarray(
            array
        ).tobytes(
            order="C"
        )
    ).hexdigest()


def _frame_id(
    message,
) -> str:
    header = getattr(
        message,
        "header",
        None,
    )

    if header is None:
        raise LidarCorruptionAdapterError(
            "PointCloud2 message has no header"
        )

    return str(
        getattr(
            header,
            "frame_id",
            "",
        )
    )


@dataclass(
    frozen=True,
)
class M2DGRVelodyneCleanAdapterResult:
    stream: EventStream
    receipt_json: str

    def receipt_dict(
        self,
    ) -> dict[str, Any]:
        return json.loads(
            self.receipt_json
        )


def adapt_m2dgr_velodyne_messages(
    messages: Iterable[object],
) -> M2DGRVelodyneCleanAdapterResult:
    """Adapt clean M2DGR Velodyne messages through the frozen Phase-2 decoder.

    This function performs no corruption and no deskew.

    The PointCloud2 header stamp is carried only as the same event/state label
    used by the frozen Phase-2 estimator. No physical scan start/center/end
    interpretation is introduced here.
    """

    message_tuple = tuple(
        messages
    )

    if not message_tuple:
        raise LidarCorruptionAdapterError(
            "at least one Velodyne PointCloud2 message is required"
        )

    timestamps = []
    payloads = []
    event_records = []

    previous_timestamp = None

    for index, message in enumerate(
        message_tuple
    ):
        timestamp_ns = pointcloud_header_stamp_ns(
            message
        )

        if (
            previous_timestamp is not None
            and timestamp_ns <= previous_timestamp
        ):
            raise LidarCorruptionAdapterError(
                "clean adapter requires strictly increasing PointCloud2 header stamps"
            )

        xyz = decode_m2dgr_velodyne_xyz(
            message
        )

        descriptors = pointcloud_field_descriptors(
            message
        )

        frame_id = _frame_id(
            message
        )

        if frame_id != EXPECTED_FRAME_ID:
            raise LidarCorruptionAdapterError(
                "decoded PointCloud2 frame differs from frozen Phase-2 frame"
            )

        raw_bytes = _raw_pointcloud_data_bytes(
            message
        )

        timestamps.append(
            timestamp_ns
        )

        payloads.append(
            xyz
        )

        event_records.append(
            {
                "event_index":
                    index,

                "header_stamp_ns":
                    timestamp_ns,

                "frame_id":
                    frame_id,

                "height":
                    int(
                        getattr(
                            message,
                            "height",
                        )
                    ),

                "width":
                    int(
                        getattr(
                            message,
                            "width",
                        )
                    ),

                "point_step":
                    int(
                        getattr(
                            message,
                            "point_step",
                        )
                    ),

                "row_step":
                    int(
                        getattr(
                            message,
                            "row_step",
                        )
                    ),

                "is_bigendian":
                    bool(
                        getattr(
                            message,
                            "is_bigendian",
                        )
                    ),

                "is_dense":
                    bool(
                        getattr(
                            message,
                            "is_dense",
                        )
                    ),

                "field_descriptors":
                    [
                        list(
                            descriptor
                        )
                        for descriptor
                        in descriptors
                    ],

                "raw_pointcloud_data_sha256":
                    sha256(
                        raw_bytes
                    ).hexdigest(),

                "raw_pointcloud_data_nbytes":
                    len(
                        raw_bytes
                    ),

                "decoded_xyz_shape":
                    list(
                        xyz.shape
                    ),

                "decoded_xyz_dtype":
                    xyz.dtype.str,

                "decoded_xyz_data_sha256":
                    _array_data_sha256(
                        xyz
                    ),
            }
        )

        previous_timestamp = timestamp_ns

    metadata = {
        "adapter_schema":
            ADAPTER_SCHEMA,

        "adapter_id":
            ADAPTER_ID,

        "source_topic":
            EXPECTED_TOPIC,

        "source_msgtype":
            EXPECTED_MSGTYPE,

        "frame_id":
            EXPECTED_FRAME_ID,

        "phase2_expected_field_names":
            list(
                EXPECTED_FIELDS
            ),

        "phase2_expected_point_step":
            EXPECTED_POINT_STEP,

        "payload_semantics":
            "decoded_xyz_float64",

        "decoder_module":
            "trust_robot.lidar_frontend",

        "decoder_function":
            "decode_m2dgr_velodyne_xyz",

        "timestamp_function":
            "pointcloud_header_stamp_ns",

        "field_descriptor_function":
            "pointcloud_field_descriptors",

        "event_count":
            len(
                message_tuple
            ),

        "pointcloud_header_used_as_event_label":
            True,

        "physical_scan_timestamp_reference_verified":
            False,

        "per_point_time_used":
            False,

        "deskew_performed":
            False,

        "intensity_retained_in_event_payload":
            False,

        "ring_retained_in_event_payload":
            False,

        "per_point_time_retained_in_event_payload":
            False,
    }

    stream = EventStream(
        modality=
            SensorModality.LIDAR,

        source_id=
            EXPECTED_TOPIC,

        timestamps_ns=
            np.asarray(
                timestamps,
                dtype=np.int64,
            ),

        payloads=
            tuple(
                payloads
            ),

        metadata=
            metadata,
    )

    receipt: dict[str, Any] = {
        "schema":
            ADAPTER_SCHEMA,

        "schema_version":
            1,

        "adapter_id":
            ADAPTER_ID,

        "source": {
            "topic":
                EXPECTED_TOPIC,

            "msgtype":
                EXPECTED_MSGTYPE,

            "frame_id":
                EXPECTED_FRAME_ID,
        },

        "phase2_decoder_binding": {
            "module":
                "trust_robot.lidar_frontend",

            "decode_function":
                "decode_m2dgr_velodyne_xyz",

            "timestamp_function":
                "pointcloud_header_stamp_ns",

            "field_descriptor_function":
                "pointcloud_field_descriptors",

            "expected_field_names":
                list(
                    EXPECTED_FIELDS
                ),

            "expected_point_step":
                EXPECTED_POINT_STEP,
        },

        "event_count":
            stream.n_events,

        "event_records":
            event_records,

        "eventstream": {
            "modality":
                stream.modality.value,

            "source_id":
                stream.source_id,

            "fingerprint_sha256":
                stream.fingerprint(),
        },

        "scientific_scope": {
            "corruption_applied":
                False,

            "reference_data_used":
                False,

            "confirmation_test_data_used":
                False,

            "estimator_executed":
                False,

            "estimator_scoring_performed":
                False,

            "ate_computed":
                False,

            "rpe_computed":
                False,

            "physical_scan_timestamp_reference_verified":
                False,

            "per_point_time_used":
                False,

            "deskew_performed":
                False,
        },
    }

    receipt[
        "content_sha256"
    ] = _content_sha256(
        receipt
    )

    receipt_json = (
        json.dumps(
            receipt,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    )

    return M2DGRVelodyneCleanAdapterResult(
        stream=
            stream,

        receipt_json=
            receipt_json,
    )


def validate_m2dgr_velodyne_clean_adapter_receipt(
    payload: Mapping[str, Any],
) -> None:
    if payload.get(
        "schema"
    ) != ADAPTER_SCHEMA:
        raise LidarCorruptionAdapterError(
            "unexpected LiDAR clean-adapter receipt schema"
        )

    if payload.get(
        "adapter_id"
    ) != ADAPTER_ID:
        raise LidarCorruptionAdapterError(
            "unexpected LiDAR clean-adapter identity"
        )

    stored = payload.get(
        "content_sha256"
    )

    if (
        not isinstance(
            stored,
            str,
        )
        or stored
        != _content_sha256(
            payload
        )
    ):
        raise LidarCorruptionAdapterError(
            "LiDAR clean-adapter receipt content digest mismatch"
        )

    scope = payload[
        "scientific_scope"
    ]

    for key in (
        "corruption_applied",
        "reference_data_used",
        "confirmation_test_data_used",
        "estimator_executed",
        "estimator_scoring_performed",
        "ate_computed",
        "rpe_computed",
        "physical_scan_timestamp_reference_verified",
        "per_point_time_used",
        "deskew_performed",
    ):
        if scope[
            key
        ] is not False:
            raise LidarCorruptionAdapterError(
                f"clean-adapter scientific scope must remain false: {key}"
            )
