from pathlib import Path
from types import SimpleNamespace
import ast
import json
import struct
import unittest

import numpy as np

from trust_robot.lidar_corruption_adapter import (
    ADAPTER_ID,
    ADAPTER_SCHEMA,
    LidarCorruptionAdapterError,
    adapt_m2dgr_velodyne_messages,
    validate_m2dgr_velodyne_clean_adapter_receipt,
)
from trust_robot.lidar_frontend import (
    EXPECTED_FIELDS,
    decode_m2dgr_velodyne_xyz,
    pointcloud_header_stamp_ns,
)


ROOT = Path(__file__).resolve().parents[2]

MODULE = (
    ROOT
    / "src/trust_robot/lidar_corruption_adapter.py"
)


def make_message(
    xyz,
    *,
    timestamp_ns,
    frame_id="velodyne",
):
    xyz = np.asarray(
        xyz,
        dtype=np.float32,
    )

    width = int(
        xyz.shape[0]
    )

    point_step = 22

    buffer = bytearray(
        width
        * point_step
    )

    for index, point in enumerate(
        xyz
    ):
        base = (
            index
            * point_step
        )

        struct.pack_into(
            "<fff",
            buffer,
            base,
            float(
                point[
                    0
                ]
            ),
            float(
                point[
                    1
                ]
            ),
            float(
                point[
                    2
                ]
            ),
        )

        struct.pack_into(
            "<fHf",
            buffer,
            base + 12,
            float(
                index
            ),
            index % 16,
            float(
                index
            )
            * 0.001,
        )

    sec = (
        timestamp_ns
        // 1_000_000_000
    )

    nanosec = (
        timestamp_ns
        % 1_000_000_000
    )

    fields = (
        ("x", 0, 7, 1),
        ("y", 4, 7, 1),
        ("z", 8, 7, 1),
        ("intensity", 12, 7, 1),
        ("ring", 16, 4, 1),
        ("time", 18, 7, 1),
    )

    return SimpleNamespace(
        header=
            SimpleNamespace(
                frame_id=
                    frame_id,

                stamp=
                    SimpleNamespace(
                        sec=
                            sec,

                        nanosec=
                            nanosec,
                    ),
            ),

        height=
            1,

        width=
            width,

        fields=[
            SimpleNamespace(
                name=
                    name,

                offset=
                    offset,

                datatype=
                    datatype,

                count=
                    count,
            )
            for (
                name,
                offset,
                datatype,
                count,
            )
            in fields
        ],

        is_bigendian=
            False,

        point_step=
            point_step,

        row_step=
            width
            * point_step,

        data=
            bytes(
                buffer
            ),

        is_dense=
            True,
    )


def fixture_messages():
    return (
        make_message(
            [
                [0.0, 1.0, 2.0],
                [3.0, 4.0, 5.0],
                [6.0, 7.0, 8.0],
            ],
            timestamp_ns=
                1_000_000_000,
        ),
        make_message(
            [
                [0.1, 1.1, 2.1],
                [3.1, 4.1, 5.1],
                [6.1, 7.1, 8.1],
                [9.1, 10.1, 11.1],
            ],
            timestamp_ns=
                1_100_000_000,
        ),
        make_message(
            [
                [0.2, 1.2, 2.2],
                [3.2, 4.2, 5.2],
                [6.2, 7.2, 8.2],
                [9.2, 10.2, 11.2],
                [12.2, 13.2, 14.2],
            ],
            timestamp_ns=
                1_200_000_000,
        ),
    )


class Phase3LidarCleanAdapterTests(
    unittest.TestCase
):
    def test_01_adapter_identity_is_explicit(self):
        self.assertEqual(
            ADAPTER_SCHEMA,
            "TRUST_ROBOT_PHASE3_M2DGR_VELODYNE_CLEAN_ADAPTER_V1",
        )

        self.assertEqual(
            ADAPTER_ID,
            "m2dgr_velodyne_phase2_xyz_clean_adapter_v1",
        )

    def test_02_empty_message_sequence_is_rejected(self):
        with self.assertRaises(
            LidarCorruptionAdapterError
        ):
            adapt_m2dgr_velodyne_messages(
                ()
            )

    def test_03_payloads_equal_frozen_phase2_decoder_exactly(self):
        messages = fixture_messages()

        result = adapt_m2dgr_velodyne_messages(
            messages
        )

        for message, payload in zip(
            messages,
            result.stream.payloads,
            strict=True,
        ):
            expected = decode_m2dgr_velodyne_xyz(
                message
            )

            np.testing.assert_array_equal(
                payload,
                expected,
            )

    def test_04_timestamps_equal_frozen_phase2_header_function(self):
        messages = fixture_messages()

        result = adapt_m2dgr_velodyne_messages(
            messages
        )

        expected = np.asarray(
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
            result.stream.timestamps_ns,
            expected,
        )

    def test_05_variable_point_counts_are_preserved(self):
        result = adapt_m2dgr_velodyne_messages(
            fixture_messages()
        )

        self.assertEqual(
            [
                payload.shape
                for payload
                in result.stream.payloads
            ],
            [
                (3, 3),
                (4, 3),
                (5, 3),
            ],
        )

    def test_06_decoded_payload_dtype_is_float64(self):
        result = adapt_m2dgr_velodyne_messages(
            fixture_messages()
        )

        for payload in result.stream.payloads:
            self.assertEqual(
                payload.dtype,
                np.dtype(
                    np.float64
                ),
            )

    def test_07_eventstream_fingerprint_is_reproducible(self):
        first = adapt_m2dgr_velodyne_messages(
            fixture_messages()
        )

        second = adapt_m2dgr_velodyne_messages(
            fixture_messages()
        )

        self.assertEqual(
            first.stream.fingerprint(),
            second.stream.fingerprint(),
        )

    def test_08_receipt_is_byte_reproducible(self):
        first = adapt_m2dgr_velodyne_messages(
            fixture_messages()
        )

        second = adapt_m2dgr_velodyne_messages(
            fixture_messages()
        )

        self.assertEqual(
            first.receipt_json,
            second.receipt_json,
        )

    def test_09_adapter_does_not_mutate_raw_message_bytes(self):
        messages = fixture_messages()

        before = [
            bytes(
                message.data
            )
            for message
            in messages
        ]

        adapt_m2dgr_velodyne_messages(
            messages
        )

        after = [
            bytes(
                message.data
            )
            for message
            in messages
        ]

        self.assertEqual(
            before,
            after,
        )

    def test_10_eventstream_arrays_are_immutable(self):
        result = adapt_m2dgr_velodyne_messages(
            fixture_messages()
        )

        self.assertFalse(
            result.stream.timestamps_ns.flags.writeable
        )

        for payload in result.stream.payloads:
            self.assertFalse(
                payload.flags.writeable
            )

    def test_11_nonincreasing_clean_timestamps_are_rejected(self):
        messages = list(
            fixture_messages()
        )

        messages[
            2
        ] = make_message(
            [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [2.0, 0.0, 0.0],
            ],
            timestamp_ns=
                1_100_000_000,
        )

        with self.assertRaises(
            LidarCorruptionAdapterError
        ):
            adapt_m2dgr_velodyne_messages(
                messages
            )

    def test_12_wrong_frame_is_rejected_by_frozen_decoder_path(self):
        messages = list(
            fixture_messages()
        )

        messages[
            1
        ] = make_message(
            [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [2.0, 0.0, 0.0],
            ],
            timestamp_ns=
                1_100_000_000,
            frame_id=
                "base_link",
        )

        with self.assertRaises(
            ValueError
        ):
            adapt_m2dgr_velodyne_messages(
                messages
            )

    def test_13_source_identity_is_frozen_velodyne_topic(self):
        result = adapt_m2dgr_velodyne_messages(
            fixture_messages()
        )

        self.assertEqual(
            result.stream.modality.value,
            "lidar",
        )

        self.assertEqual(
            result.stream.source_id,
            "/velodyne_points",
        )

    def test_14_receipt_preserves_structural_descriptors(self):
        result = adapt_m2dgr_velodyne_messages(
            fixture_messages()
        )

        receipt = result.receipt_dict()

        first = receipt[
            "event_records"
        ][
            0
        ]

        self.assertEqual(
            [
                descriptor[
                    0
                ]
                for descriptor
                in first[
                    "field_descriptors"
                ]
            ],
            list(
                EXPECTED_FIELDS
            ),
        )

        self.assertEqual(
            first[
                "point_step"
            ],
            22,
        )

        self.assertEqual(
            first[
                "frame_id"
            ],
            "velodyne",
        )

    def test_15_receipt_scientific_scope_remains_clean_only(self):
        result = adapt_m2dgr_velodyne_messages(
            fixture_messages()
        )

        receipt = result.receipt_dict()

        validate_m2dgr_velodyne_clean_adapter_receipt(
            receipt
        )

        scope = receipt[
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
            self.assertFalse(
                scope[
                    key
                ]
            )

    def test_16_adapter_reuses_frozen_decoder_and_has_no_corruption_execution(self):
        source = MODULE.read_text(
            encoding="utf-8"
        )

        tree = ast.parse(
            source,
            filename=str(
                MODULE
            ),
        )

        imported_from_lidar_frontend = set()

        imported_from_corruption = set()

        for node in ast.walk(
            tree
        ):
            if not isinstance(
                node,
                ast.ImportFrom,
            ):
                continue

            if node.module == "lidar_frontend":
                imported_from_lidar_frontend.update(
                    alias.name
                    for alias
                    in node.names
                )

            if node.module == "corruption":
                imported_from_corruption.update(
                    alias.name
                    for alias
                    in node.names
                )

        self.assertIn(
            "decode_m2dgr_velodyne_xyz",
            imported_from_lidar_frontend,
        )

        self.assertIn(
            "pointcloud_header_stamp_ns",
            imported_from_lidar_frontend,
        )

        self.assertIn(
            "pointcloud_field_descriptors",
            imported_from_lidar_frontend,
        )

        self.assertEqual(
            imported_from_corruption,
            {
                "EventStream",
                "SensorModality",
            },
        )

        for forbidden in (
            "apply_corruption(",
            "CorruptionSpec(",
            "inject_event_gap(",
            "inject_event_repeat(",
            "inject_timestamp_step_shift(",
        ):
            self.assertNotIn(
                forbidden,
                source,
            )


if __name__ == "__main__":
    unittest.main()
