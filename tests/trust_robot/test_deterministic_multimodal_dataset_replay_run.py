from hashlib import sha256
import unittest

from trust_robot.deterministic_multimodal_dataset_replay import (
    CAMERA_STREAM_ID,
    D435I_IMU_STREAM_ID,
    HANDSFREE_IMU_STREAM_ID,
    LIDAR_STREAM_ID,
    ReplayEnvelope,
    build_train_replay_source,
)
from trust_robot.deterministic_multimodal_dataset_replay_run import (
    RUN_ID,
    DeterministicReplayRunError,
    TrajectoryReplayAggregateBuilder,
    build_candidate_contract,
    build_run_manifest,
    build_success_payload,
    build_trajectory_record,
    content_sha256,
)
from trust_robot.software_evidence_completion import (
    TRAIN_TRAJECTORIES,
)


BAG_SHA = "a" * 64


def stream(
    stream_id,
    modality,
):
    return {
        "stream_id":
            stream_id,
        "modality":
            modality,
        "frame_id":
            {
                CAMERA_STREAM_ID:
                    "camera_color_optical_frame",
                D435I_IMU_STREAM_ID:
                    "camera_imu_optical_frame",
                HANDSFREE_IMU_STREAM_ID:
                    "base_link",
                LIDAR_STREAM_ID:
                    "velodyne",
            }[
                stream_id
            ],
        "clock_domain":
            {
                CAMERA_STREAM_ID:
                    "camera_clock",
                D435I_IMU_STREAM_ID:
                    "camera_imu_clock",
                HANDSFREE_IMU_STREAM_ID:
                    "handsfree_clock",
                LIDAR_STREAM_ID:
                    "lidar_clock",
            }[
                stream_id
            ],
        "timestamp_unit":
            "nanoseconds",
        "estimator_input":
            True,
        "reference_only":
            False,
    }


def record(
    trajectory_id="Circle_01",
):
    streams = [
        stream(
            CAMERA_STREAM_ID,
            "camera",
        ),
        stream(
            D435I_IMU_STREAM_ID,
            "imu",
        ),
        stream(
            HANDSFREE_IMU_STREAM_ID,
            "imu",
        ),
        stream(
            LIDAR_STREAM_ID,
            "lidar",
        ),
    ]

    if trajectory_id in {
        "street_010",
        "street_09",
    }:
        streams = streams[
            2:
        ]

    return {
        "trajectory_id":
            trajectory_id,
        "base_trajectory_id":
            trajectory_id,
        "split":
            "train",
        "derivative_kind":
            "clean",
        "streams":
            streams,
        "calibration_artifacts": [
            {
                "source_path":
                    f"raw/rosbags/{trajectory_id}.bag",
                "verification_status":
                    "verified",
                "sha256":
                    BAG_SHA,
            }
        ],
    }


def envelope(
    source,
    *,
    record_index,
    stream_id,
    stream_message_index,
    payload,
    bag_time,
    header_time,
    message_type="msg",
):
    modality = {
        CAMERA_STREAM_ID:
            "camera",
        D435I_IMU_STREAM_ID:
            "imu",
        HANDSFREE_IMU_STREAM_ID:
            "imu",
        LIDAR_STREAM_ID:
            "lidar",
    }[
        stream_id
    ]

    return ReplayEnvelope(
        schema=(
            "TRUST_ROBOT_SE1_DETERMINISTIC_MULTIMODAL_DATASET_REPLAY_V1"
        ),
        trajectory_id=source.trajectory_id,
        split_role="train",
        source_bag_relative_path=source.bag_relative_path,
        source_bag_sha256=source.bag_sha256,
        record_index=record_index,
        stream_message_index=stream_message_index,
        source_stream_id=stream_id,
        modality=modality,
        message_type=message_type,
        serialized_payload=payload,
        serialized_payload_bytes=len(
            payload
        ),
        serialized_payload_sha256=sha256(
            payload
        ).hexdigest(),
        bag_record_time_ns=bag_time,
        header_stamp_ns=header_time,
    )


class TestDeterministicReplayRunArtifacts(
    unittest.TestCase
):

    def test_01_candidate_contract_is_train_only(self):
        payload = (
            build_candidate_contract()
        )

        self.assertEqual(
            payload[
                "trajectory_order"
            ],
            list(
                TRAIN_TRAJECTORIES
            ),
        )

        self.assertEqual(
            payload[
                "trajectory_count"
            ],
            22,
        )

        boundary = payload[
            "scientific_boundary"
        ]

        self.assertFalse(
            boundary[
                "validation_access"
            ]
        )

        self.assertFalse(
            boundary[
                "confirmation_access"
            ]
        )

        self.assertFalse(
            boundary[
                "model_training"
            ]
        )

    def test_02_content_digest_ignores_own_digest_field(self):
        payload = {
            "a":
                1,
        }

        digest = content_sha256(
            payload
        )

        payload[
            "content_sha256"
        ] = digest

        self.assertEqual(
            content_sha256(
                payload
            ),
            digest,
        )

    def test_03_trajectory_aggregate_preserves_reader_order(self):
        source = (
            build_train_replay_source(
                record()
            )
        )

        builder = (
            TrajectoryReplayAggregateBuilder(
                source
            )
        )

        builder.add(
            envelope(
                source,
                record_index=0,
                stream_id=LIDAR_STREAM_ID,
                stream_message_index=0,
                payload=b"lidar",
                bag_time=300,
                header_time=250,
            )
        )

        builder.add(
            envelope(
                source,
                record_index=1,
                stream_id=CAMERA_STREAM_ID,
                stream_message_index=0,
                payload=b"camera",
                bag_time=100,
                header_time=90,
            )
        )

        payload = builder.payload(
            bag_file_size_bytes=1000
        )

        self.assertEqual(
            payload[
                "message_count"
            ],
            2,
        )

        self.assertEqual(
            payload[
                "first_observed_bag_record_time_ns"
            ],
            300,
        )

        self.assertEqual(
            payload[
                "last_observed_bag_record_time_ns"
            ],
            100,
        )

        self.assertFalse(
            payload[
                "ordering_contract"
            ][
                "timestamp_sort_performed"
            ]
        )

    def test_04_reduced_availability_remains_explicit(self):
        source = (
            build_train_replay_source(
                record(
                    "street_09"
                )
            )
        )

        builder = (
            TrajectoryReplayAggregateBuilder(
                source
            )
        )

        payload = builder.payload(
            bag_file_size_bytes=100
        )

        availability = {
            item[
                "stream_id"
            ]:
                item[
                    "present_in_frozen_manifest"
                ]
            for item in payload[
                "availability"
            ]
        }

        self.assertFalse(
            availability[
                CAMERA_STREAM_ID
            ]
        )

        self.assertFalse(
            availability[
                D435I_IMU_STREAM_ID
            ]
        )

        self.assertTrue(
            availability[
                HANDSFREE_IMU_STREAM_ID
            ]
        )

        self.assertTrue(
            availability[
                LIDAR_STREAM_ID
            ]
        )

    def test_05_reject_out_of_order_record_index(self):
        source = (
            build_train_replay_source(
                record()
            )
        )

        builder = (
            TrajectoryReplayAggregateBuilder(
                source
            )
        )

        with self.assertRaises(
            DeterministicReplayRunError
        ):
            builder.add(
                envelope(
                    source,
                    record_index=1,
                    stream_id=CAMERA_STREAM_ID,
                    stream_message_index=0,
                    payload=b"x",
                    bag_time=1,
                    header_time=None,
                )
            )

    def test_06_stream_indices_must_be_contiguous(self):
        source = (
            build_train_replay_source(
                record()
            )
        )

        builder = (
            TrajectoryReplayAggregateBuilder(
                source
            )
        )

        with self.assertRaises(
            DeterministicReplayRunError
        ):
            builder.add(
                envelope(
                    source,
                    record_index=0,
                    stream_id=CAMERA_STREAM_ID,
                    stream_message_index=1,
                    payload=b"x",
                    bag_time=1,
                    header_time=None,
                )
            )

    def test_07_trajectory_payload_has_deterministic_digest(self):
        source = (
            build_train_replay_source(
                record()
            )
        )

        first = (
            TrajectoryReplayAggregateBuilder(
                source
            )
        )

        second = (
            TrajectoryReplayAggregateBuilder(
                source
            )
        )

        for builder in (
            first,
            second,
        ):
            builder.add(
                envelope(
                    source,
                    record_index=0,
                    stream_id=CAMERA_STREAM_ID,
                    stream_message_index=0,
                    payload=b"x",
                    bag_time=1,
                    header_time=2,
                )
            )

        first_payload = first.payload(
            bag_file_size_bytes=99
        )

        second_payload = second.payload(
            bag_file_size_bytes=99
        )

        self.assertEqual(
            first_payload,
            second_payload,
        )

        self.assertEqual(
            first_payload[
                "content_sha256"
            ],
            content_sha256(
                first_payload
            ),
        )

    def test_08_raw_per_message_payload_not_in_trajectory_artifact(self):
        source = (
            build_train_replay_source(
                record()
            )
        )

        builder = (
            TrajectoryReplayAggregateBuilder(
                source
            )
        )

        builder.add(
            envelope(
                source,
                record_index=0,
                stream_id=CAMERA_STREAM_ID,
                stream_message_index=0,
                payload=b"secret-payload",
                bag_time=1,
                header_time=None,
            )
        )

        payload = builder.payload(
            bag_file_size_bytes=99
        )

        self.assertNotIn(
            b"secret-payload".hex(),
            repr(
                payload
            ),
        )

        self.assertFalse(
            payload[
                "artifact_contract"
            ][
                "raw_per_message_payload_written"
            ]
        )

    def test_09_build_trajectory_record_validates_content_digest(self):
        source = (
            build_train_replay_source(
                record()
            )
        )

        builder = (
            TrajectoryReplayAggregateBuilder(
                source
            )
        )

        payload = builder.payload(
            bag_file_size_bytes=99
        )

        record_payload = (
            build_trajectory_record(
                trajectory_payload=payload,
                trajectory_file_sha256="b" * 64,
            )
        )

        self.assertEqual(
            record_payload[
                "trajectory_id"
            ],
            "Circle_01",
        )

        self.assertEqual(
            record_payload[
                "trajectory_content_sha256"
            ],
            payload[
                "content_sha256"
            ],
        )

    def test_10_run_manifest_requires_exact_frozen_order(self):
        fake = [
            {
                "trajectory_id":
                    trajectory,
                "message_count":
                    1,
                "total_serialized_payload_bytes":
                    2,
            }
            for trajectory in TRAIN_TRAJECTORIES
        ]

        bad = list(
            reversed(
                fake
            )
        )

        with self.assertRaises(
            DeterministicReplayRunError
        ):
            build_run_manifest(
                dataset_root="/dataset",
                candidate_contract_content_sha256="c" * 64,
                trajectory_records=bad,
            )

    def test_11_run_manifest_aggregates_counts(self):
        fake = [
            {
                "trajectory_id":
                    trajectory,
                "message_count":
                    index + 1,
                "total_serialized_payload_bytes":
                    (index + 1) * 10,
            }
            for index, trajectory in enumerate(
                TRAIN_TRAJECTORIES
            )
        ]

        payload = (
            build_run_manifest(
                dataset_root="/dataset",
                candidate_contract_content_sha256="c" * 64,
                trajectory_records=fake,
            )
        )

        expected_messages = sum(
            range(
                1,
                23,
            )
        )

        self.assertEqual(
            payload[
                "total_selected_replay_messages"
            ],
            expected_messages,
        )

        self.assertEqual(
            payload[
                "total_selected_serialized_payload_bytes"
            ],
            expected_messages * 10,
        )

        self.assertEqual(
            payload[
                "content_sha256"
            ],
            content_sha256(
                payload
            ),
        )

    def test_12_success_payload_preserves_nonselection_boundary(self):
        payload = (
            build_success_payload(
                run_manifest_file_sha256="d" * 64,
                run_manifest_content_sha256="e" * 64,
                total_selected_replay_messages=100,
                total_selected_serialized_payload_bytes=200,
            )
        )

        self.assertEqual(
            payload[
                "run_id"
            ],
            RUN_ID,
        )

        self.assertEqual(
            payload[
                "status"
            ],
            "success",
        )

        for key in (
            "validation_bags_opened",
            "confirmation_bags_opened",
            "reference_data_read",
            "health_labels_assigned",
            "model_training_performed",
            "ate_rpe_computed",
            "final_score_computed",
        ):
            self.assertFalse(
                payload[
                    key
                ]
            )


if __name__ == "__main__":
    unittest.main()
