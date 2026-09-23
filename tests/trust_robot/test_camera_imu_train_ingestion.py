import copy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from trust_robot.camera_imu_observation_adapter import (
    build_raw_observation_receipt,
)
from trust_robot.camera_imu_train_ingestion import (
    FROZEN_SPLIT_SHA256,
    RUN_ID,
    SCHEMA,
    SUPPORTED_STREAMS,
    TRAIN_TRAJECTORIES,
    CameraImuTrainIngestionError,
    StreamAggregateBuilder,
    build_candidate_manifest,
    content_sha256,
    empty_stream_builders,
    header_stamp_ns_from_message,
    modality_for_supported_stream,
    validate_candidate_manifest,
)
from trust_robot.multimodal_diagnostic_foundation import (
    Modality,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs"
    / "trust_robot"
    / "phase5_camera_imu_train_ingestion_candidate_v1.json"
)


class TestCameraImuTrainIngestion(unittest.TestCase):

    def receipt(
        self,
        *,
        stream="/handsfree/imu",
        trajectory="Circle_01",
        index=0,
        payload=b"abc",
        record_ns=100,
        header_ns=90,
        split="train",
    ):
        msgtype = (
            "sensor_msgs/msg/CompressedImage"
            if stream == "/camera/color/image_raw/compressed"
            else "sensor_msgs/msg/Imu"
        )

        return build_raw_observation_receipt(
            source_stream_id=stream,
            trajectory_or_session_id=trajectory,
            split_role=split,
            message_index=index,
            serialized_payload=payload,
            bag_record_time_ns=record_ns,
            header_stamp_ns=header_ns,
            message_type=msgtype,
        )

    def test_01_schema(self):
        self.assertEqual(
            SCHEMA,
            "TRUST_ROBOT_PHASE5_CAMERA_IMU_TRAIN_INGESTION_V1",
        )

    def test_02_run_id(self):
        self.assertEqual(
            RUN_ID,
            "trust_robot_phase5_m2dgr_camera_imu_train_ingestion_v1",
        )

    def test_03_split_sha(self):
        self.assertEqual(
            FROZEN_SPLIT_SHA256,
            "017a388ef1ce4ad30812669632a022ca37c084871bc949693fd9c0541014238f",
        )

    def test_04_exact_train_count(self):
        self.assertEqual(
            len(TRAIN_TRAJECTORIES),
            22,
        )

    def test_05_train_unique(self):
        self.assertEqual(
            len(set(TRAIN_TRAJECTORIES)),
            22,
        )

    def test_06_circle_02_not_train(self):
        self.assertNotIn(
            "Circle_02",
            TRAIN_TRAJECTORIES,
        )

    def test_07_gate_02_not_train(self):
        self.assertNotIn(
            "gate_02",
            TRAIN_TRAJECTORIES,
        )

    def test_08_hall_02_not_train(self):
        self.assertNotIn(
            "hall_02",
            TRAIN_TRAJECTORIES,
        )

    def test_09_lift_01_not_train(self):
        self.assertNotIn(
            "lift_01",
            TRAIN_TRAJECTORIES,
        )

    def test_10_room_01_not_train(self):
        self.assertNotIn(
            "room_01",
            TRAIN_TRAJECTORIES,
        )

    def test_11_room_dark_05_not_train(self):
        self.assertNotIn(
            "room_dark_05",
            TRAIN_TRAJECTORIES,
        )

    def test_12_street_06_not_train(self):
        self.assertNotIn(
            "street_06",
            TRAIN_TRAJECTORIES,
        )

    def test_13_supported_stream_count(self):
        self.assertEqual(
            len(SUPPORTED_STREAMS),
            3,
        )

    def test_14_camera_mapping(self):
        self.assertIs(
            modality_for_supported_stream(
                "/camera/color/image_raw/compressed"
            ),
            Modality.CAMERA,
        )

    def test_15_camera_imu_mapping(self):
        self.assertIs(
            modality_for_supported_stream(
                "/camera/imu"
            ),
            Modality.IMU,
        )

    def test_16_handsfree_mapping(self):
        self.assertIs(
            modality_for_supported_stream(
                "/handsfree/imu"
            ),
            Modality.IMU,
        )

    def test_17_unknown_stream_rejected(self):
        with self.assertRaises(
            CameraImuTrainIngestionError
        ):
            modality_for_supported_stream(
                "/velodyne_points"
            )

    def test_18_empty_builders_have_three_streams(self):
        builders = empty_stream_builders(
            "Circle_01"
        )

        self.assertEqual(
            set(builders),
            set(SUPPORTED_STREAMS),
        )

    def test_19_non_train_builder_rejected(self):
        with self.assertRaises(
            CameraImuTrainIngestionError
        ):
            empty_stream_builders(
                "Circle_02"
            )

    def test_20_empty_stream_preserved_absent(self):
        builder = empty_stream_builders(
            "Circle_01"
        )[
            "/camera/color/image_raw/compressed"
        ]

        payload = builder.payload()

        self.assertFalse(
            payload["stream_present"]
        )

        self.assertEqual(
            payload["message_count"],
            0,
        )

    def test_21_add_one_receipt(self):
        builder = empty_stream_builders(
            "Circle_01"
        )[
            "/handsfree/imu"
        ]

        builder.add(
            self.receipt()
        )

        payload = builder.payload()

        self.assertTrue(
            payload["stream_present"]
        )

        self.assertEqual(
            payload["message_count"],
            1,
        )

    def test_22_total_bytes(self):
        builder = empty_stream_builders(
            "Circle_01"
        )[
            "/handsfree/imu"
        ]

        builder.add(
            self.receipt(
                payload=b"12345"
            )
        )

        self.assertEqual(
            builder.payload()[
                "total_serialized_payload_bytes"
            ],
            5,
        )

    def test_23_indices_must_be_contiguous(self):
        builder = empty_stream_builders(
            "Circle_01"
        )[
            "/handsfree/imu"
        ]

        with self.assertRaises(
            CameraImuTrainIngestionError
        ):
            builder.add(
                self.receipt(
                    index=1
                )
            )

    def test_24_validation_receipt_rejected(self):
        builder = empty_stream_builders(
            "Circle_01"
        )[
            "/handsfree/imu"
        ]

        with self.assertRaises(
            CameraImuTrainIngestionError
        ):
            builder.add(
                self.receipt(
                    split="validation"
                )
            )

    def test_25_confirmation_receipt_rejected(self):
        builder = empty_stream_builders(
            "Circle_01"
        )[
            "/handsfree/imu"
        ]

        with self.assertRaises(
            CameraImuTrainIngestionError
        ):
            builder.add(
                self.receipt(
                    split="confirmation_test"
                )
            )

    def test_26_wrong_trajectory_rejected(self):
        builder = empty_stream_builders(
            "Circle_01"
        )[
            "/handsfree/imu"
        ]

        with self.assertRaises(
            CameraImuTrainIngestionError
        ):
            builder.add(
                self.receipt(
                    trajectory="door_01"
                )
            )

    def test_27_wrong_stream_rejected(self):
        builder = empty_stream_builders(
            "Circle_01"
        )[
            "/handsfree/imu"
        ]

        with self.assertRaises(
            CameraImuTrainIngestionError
        ):
            builder.add(
                self.receipt(
                    stream="/camera/imu"
                )
            )

    def test_28_first_last_record_time(self):
        builder = empty_stream_builders(
            "Circle_01"
        )[
            "/handsfree/imu"
        ]

        builder.add(
            self.receipt(
                index=0,
                record_ns=100,
            )
        )

        builder.add(
            self.receipt(
                index=1,
                record_ns=200,
            )
        )

        payload = builder.payload()

        self.assertEqual(
            payload["first_bag_record_time_ns"],
            100,
        )

        self.assertEqual(
            payload["last_bag_record_time_ns"],
            200,
        )

    def test_29_header_present_count(self):
        builder = empty_stream_builders(
            "Circle_01"
        )[
            "/handsfree/imu"
        ]

        builder.add(
            self.receipt(
                index=0,
                header_ns=90,
            )
        )

        builder.add(
            self.receipt(
                index=1,
                header_ns=None,
            )
        )

        self.assertEqual(
            builder.payload()[
                "header_stamp_present_count"
            ],
            1,
        )

    def test_30_aggregate_digest_deterministic(self):
        first = empty_stream_builders(
            "Circle_01"
        )[
            "/handsfree/imu"
        ]

        second = empty_stream_builders(
            "Circle_01"
        )[
            "/handsfree/imu"
        ]

        for builder in (
            first,
            second,
        ):
            builder.add(
                self.receipt(
                    index=0
                )
            )

            builder.add(
                self.receipt(
                    index=1,
                    payload=b"xyz",
                    record_ns=200,
                    header_ns=190,
                )
            )

        self.assertEqual(
            first.payload()[
                "aggregate_receipt_sha256"
            ],
            second.payload()[
                "aggregate_receipt_sha256"
            ],
        )

    def test_31_header_stamp_ros2_names(self):
        msg = SimpleNamespace(
            header=SimpleNamespace(
                stamp=SimpleNamespace(
                    sec=3,
                    nanosec=4,
                )
            )
        )

        self.assertEqual(
            header_stamp_ns_from_message(
                msg
            ),
            3_000_000_004,
        )

    def test_32_header_stamp_ros1_names(self):
        msg = SimpleNamespace(
            header=SimpleNamespace(
                stamp=SimpleNamespace(
                    secs=5,
                    nsecs=6,
                )
            )
        )

        self.assertEqual(
            header_stamp_ns_from_message(
                msg
            ),
            5_000_000_006,
        )

    def test_33_missing_header_returns_none(self):
        self.assertIsNone(
            header_stamp_ns_from_message(
                SimpleNamespace()
            )
        )

    def test_34_manifest_matches_config(self):
        payload = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

        validate_candidate_manifest(
            payload
        )

        self.assertEqual(
            payload,
            build_candidate_manifest(),
        )

    def test_35_manifest_train_only(self):
        payload = build_candidate_manifest()

        self.assertEqual(
            payload["split_role"],
            "train",
        )

        self.assertFalse(
            payload[
                "scientific_boundary"
            ][
                "confirmation_bag_open_authorized"
            ]
        )

    def test_36_manifest_scientific_boundary(self):
        payload = build_candidate_manifest()

        boundary = payload[
            "scientific_boundary"
        ]

        self.assertFalse(
            boundary[
                "camera_feature_contract_selected"
            ]
        )
        self.assertFalse(
            boundary[
                "imu_feature_contract_selected"
            ]
        )
        self.assertFalse(
            boundary[
                "classifier_training_authorized"
            ]
        )
        self.assertFalse(
            boundary[
                "ate_rpe_computation_authorized"
            ]
        )
        self.assertFalse(
            boundary[
                "final_scoring_authorized"
            ]
        )

    def test_37_manifest_mutation_rejected(self):
        payload = build_candidate_manifest()

        modified = copy.deepcopy(
            payload
        )

        modified[
            "scientific_boundary"
        ][
            "classifier_training_authorized"
        ] = True

        with self.assertRaises(
            CameraImuTrainIngestionError
        ):
            validate_candidate_manifest(
                modified
            )

    def test_38_content_digest_deterministic(self):
        payload = build_candidate_manifest()

        self.assertEqual(
            content_sha256(
                payload
            ),
            content_sha256(
                payload
            ),
        )

        self.assertEqual(
            len(
                content_sha256(
                    payload
                )
            ),
            64,
        )


if __name__ == "__main__":
    unittest.main()
