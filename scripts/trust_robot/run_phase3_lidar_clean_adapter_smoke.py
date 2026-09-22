#!/usr/bin/env python3

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import argparse
import json

import numpy as np
from rosbags.highlevel import AnyReader

from trust_robot.lidar_corruption_adapter import (
    adapt_m2dgr_velodyne_messages,
    validate_m2dgr_velodyne_clean_adapter_receipt,
)
from trust_robot.lidar_frontend import (
    EXPECTED_MSGTYPE,
    EXPECTED_TOPIC,
    decode_m2dgr_velodyne_xyz,
    pointcloud_header_stamp_ns,
)


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--bag",
        required=True,
    )

    return parser.parse_args()


def raw_data_sha(
    message,
):
    raw = memoryview(
        message.data
    ).cast(
        "B"
    )

    return sha256(
        raw.tobytes()
    ).hexdigest()


def main() -> int:
    args = parse_args()

    bag = Path(
        args.bag
    )

    if bag.name != "Circle_01.bag":
        raise RuntimeError(
            "smoke is prospectively restricted to TRAIN Circle_01"
        )

    messages = []

    with AnyReader(
        [
            bag
        ]
    ) as reader:
        connections = [
            connection
            for connection
            in reader.connections
            if (
                connection.topic
                == EXPECTED_TOPIC
                and connection.msgtype
                == EXPECTED_MSGTYPE
            )
        ]

        if len(
            connections
        ) != 1:
            raise RuntimeError(
                "expected exactly one frozen Velodyne PointCloud2 connection"
            )

        for connection, _bag_time, rawdata in reader.messages(
            connections=connections
        ):
            messages.append(
                reader.deserialize(
                    rawdata,
                    connection.msgtype,
                )
            )

            if len(
                messages
            ) == 3:
                break

    if len(
        messages
    ) != 3:
        raise RuntimeError(
            "could not read exactly three clean TRAIN Velodyne messages"
        )

    raw_before = [
        raw_data_sha(
            message
        )
        for message
        in messages
    ]

    first = adapt_m2dgr_velodyne_messages(
        messages
    )

    second = adapt_m2dgr_velodyne_messages(
        messages
    )

    raw_after = [
        raw_data_sha(
            message
        )
        for message
        in messages
    ]

    if raw_before != raw_after:
        raise RuntimeError(
            "clean source PointCloud2 bytes changed during adaptation"
        )

    if (
        first.stream.fingerprint()
        != second.stream.fingerprint()
    ):
        raise RuntimeError(
            "clean EventStream fingerprint was not reproducible"
        )

    if first.receipt_json != second.receipt_json:
        raise RuntimeError(
            "clean adapter receipt was not byte-reproducible"
        )

    receipt = first.receipt_dict()

    validate_m2dgr_velodyne_clean_adapter_receipt(
        receipt
    )

    if first.stream.n_events != 3:
        raise RuntimeError(
            "unexpected clean EventStream event count"
        )

    direct_timestamps = np.asarray(
        [
            pointcloud_header_stamp_ns(
                message
            )
            for message
            in messages
        ],
        dtype=np.int64,
    )

    np.testing.assert_array_equal(
        first.stream.timestamps_ns,
        direct_timestamps,
    )

    for index, (
        message,
        payload,
    ) in enumerate(
        zip(
            messages,
            first.stream.payloads,
            strict=True,
        )
    ):
        direct = decode_m2dgr_velodyne_xyz(
            message
        )

        np.testing.assert_array_equal(
            payload,
            direct,
        )

        print(
            f"event_index={index}"
        )

        print(
            "  header_stamp_ns=",
            int(
                first.stream.timestamps_ns[
                    index
                ]
            ),
        )

        print(
            "  xyz_shape=",
            payload.shape,
        )

        print(
            "  xyz_dtype=",
            payload.dtype.str,
        )

        print(
            "  raw_pointcloud_data_sha256=",
            raw_before[
                index
            ],
        )

        print(
            "  decoded_xyz_data_sha256=",
            receipt[
                "event_records"
            ][
                index
            ][
                "decoded_xyz_data_sha256"
            ],
        )

    print(
        "clean_event_count=",
        first.stream.n_events,
    )

    print(
        "clean_eventstream_fingerprint_sha256=",
        first.stream.fingerprint(),
    )

    print(
        "adapter_receipt_content_sha256=",
        receipt[
            "content_sha256"
        ],
    )

    print(
        "source_raw_bytes_unchanged=true"
    )

    print(
        "repeated_adaptation_fingerprint_exact_match=true"
    )

    print(
        "repeated_adapter_receipt_byte_exact_match=true"
    )

    print(
        "phase2_decoder_payload_exact_match=true"
    )

    print(
        "corruption_applied=false"
    )

    print(
        "reference_data_used=false"
    )

    print(
        "confirmation_test_data_used=false"
    )

    print(
        "estimator_executed=false"
    )

    print(
        "physical_scan_timestamp_reference_verified=false"
    )

    print(
        "per_point_time_used=false"
    )

    print(
        "deskew_performed=false"
    )

    print(
        "ate_computed=false"
    )

    print(
        "rpe_computed=false"
    )

    print(
        "TRUST_ROBOT_PHASE3_LIDAR_CLEAN_ADAPTER_SMOKE_V1=PASS"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
