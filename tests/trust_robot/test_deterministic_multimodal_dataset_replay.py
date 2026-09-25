import copy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from trust_robot.deterministic_multimodal_dataset_replay import (
    CAMERA_STREAM_ID,
    D435I_IMU_STREAM_ID,
    HANDSFREE_IMU_STREAM_ID,
    LIDAR_STREAM_ID,
    SCHEMA,
    DeterministicReplayError,
    ReplayEnvelopeBuilder,
    build_train_replay_source,
    expected_stream_ids,
    iter_anyreader_replay,
    load_train_replay_source_from_manifest_file,
)
from trust_robot.software_evidence_completion import (
    TRAIN_TRAJECTORIES,
)


BAG_SHA = "a" * 64


def stream(
    stream_id,
    modality,
):
    frame = {
        CAMERA_STREAM_ID:
            "camera_color_optical_frame",
        D435I_IMU_STREAM_ID:
            "camera_imu_optical_frame",
        HANDSFREE_IMU_STREAM_ID:
            "base_link",
        LIDAR_STREAM_ID:
            "velodyne",
    }[stream_id]

    clock = {
        CAMERA_STREAM_ID:
            "m2dgr_camera_image_header_clock_unverified",
        D435I_IMU_STREAM_ID:
            "m2dgr_camera_imu_header_clock_unverified",
        HANDSFREE_IMU_STREAM_ID:
            "m2dgr_handsfree_header_clock_unverified",
        LIDAR_STREAM_ID:
            "m2dgr_velodyne_header_clock_unverified",
    }[stream_id]

    return {
        "stream_id":
            stream_id,
        "modality":
            modality,
        "frame_id":
            frame,
        "clock_domain":
            clock,
        "timestamp_unit":
            "nanoseconds",
        "estimator_input":
            True,
        "reference_only":
            False,
    }


def full_record(
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
                    (
                        "raw/rosbags/"
                        f"{trajectory_id}.bag"
                    ),
                "verification_status":
                    "verified",
                "sha256":
                    BAG_SHA,
            }
        ],
        "references": [
            {
                "source_id":
                    f"{trajectory_id}_reference",
            }
        ],
    }


class TestDeterministicMultimodalDatasetReplay(unittest.TestCase):

    def test_01_train_population_is_frozen(self):
        self.assertEqual(
            len(TRAIN_TRAJECTORIES),
            22,
        )

    def test_02_full_availability_contract(self):
        self.assertEqual(
            expected_stream_ids(
                "Circle_01"
            ),
            (
                CAMERA_STREAM_ID,
                D435I_IMU_STREAM_ID,
                HANDSFREE_IMU_STREAM_ID,
                LIDAR_STREAM_ID,
            ),
        )

    def test_03_reduced_availability_contract_street_010(self):
        self.assertEqual(
            expected_stream_ids(
                "street_010"
            ),
            (
                HANDSFREE_IMU_STREAM_ID,
                LIDAR_STREAM_ID,
            ),
        )

    def test_04_reduced_availability_contract_street_09(self):
        self.assertEqual(
            expected_stream_ids(
                "street_09"
            ),
            (
                HANDSFREE_IMU_STREAM_ID,
                LIDAR_STREAM_ID,
            ),
        )

    def test_05_build_full_train_source(self):
        source = build_train_replay_source(
            full_record()
        )

        self.assertEqual(
            source.trajectory_id,
            "Circle_01",
        )

        self.assertEqual(
            tuple(
                source.stream_by_id()
            ),
            expected_stream_ids(
                "Circle_01"
            ),
        )

    def test_06_build_reduced_train_source(self):
        source = build_train_replay_source(
            full_record(
                "street_010"
            )
        )

        self.assertEqual(
            tuple(
                source.stream_by_id()
            ),
            (
                HANDSFREE_IMU_STREAM_ID,
                LIDAR_STREAM_ID,
            ),
        )

    def test_07_availability_payload_preserves_absence(self):
        source = build_train_replay_source(
            full_record(
                "street_09"
            )
        )

        availability = {
            item["stream_id"]:
                item[
                    "present_in_frozen_manifest"
                ]
            for item in source.availability_payload()
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

    def test_08_contract_boundary_is_noninferential(self):
        source = build_train_replay_source(
            full_record()
        )

        payload = source.contract_payload()

        self.assertEqual(
            payload["schema"],
            SCHEMA,
        )

        boundary = payload[
            "scientific_boundary"
        ]

        for key in (
            "availability_is_health_label",
            "missing_stream_is_zero_feature_vector",
            "fabricated_streams_allowed",
            "physical_capture_time_inferred",
            "shared_clock_domain_inferred",
            "fixed_time_offset_selected",
            "interpolation_performed",
            "feature_extraction_performed",
            "health_label_assigned",
            "health_probability_emitted",
            "model_training_performed",
            "validation_data_read",
            "confirmation_data_read",
            "reference_data_read",
            "reference_association_performed",
            "ate_rpe_computed",
            "final_score_computed",
        ):
            self.assertFalse(
                boundary[
                    key
                ]
            )

    def test_09_reject_validation_record(self):
        record = full_record()
        record["split"] = (
            "validation_calibration"
        )
        record["trajectory_id"] = "door_02"
        record["base_trajectory_id"] = "door_02"

        with self.assertRaises(
            DeterministicReplayError
        ):
            build_train_replay_source(
                record
            )

    def test_10_reject_confirmation_record(self):
        record = full_record()
        record["split"] = (
            "confirmation_test"
        )
        record["trajectory_id"] = "Circle_02"
        record["base_trajectory_id"] = "Circle_02"

        with self.assertRaises(
            DeterministicReplayError
        ):
            build_train_replay_source(
                record
            )

    def test_11_reject_base_identity_change(self):
        record = full_record()
        record["base_trajectory_id"] = (
            "door_01"
        )

        with self.assertRaises(
            DeterministicReplayError
        ):
            build_train_replay_source(
                record
            )

    def test_12_reject_wrong_bag_path(self):
        record = full_record()
        record[
            "calibration_artifacts"
        ][0][
            "source_path"
        ] = "raw/rosbags/door_01.bag"

        with self.assertRaises(
            DeterministicReplayError
        ):
            build_train_replay_source(
                record
            )

    def test_13_reject_unverified_bag(self):
        record = full_record()
        record[
            "calibration_artifacts"
        ][0][
            "verification_status"
        ] = "unverified"

        with self.assertRaises(
            DeterministicReplayError
        ):
            build_train_replay_source(
                record
            )

    def test_14_reject_duplicate_stream(self):
        record = full_record()
        record["streams"].append(
            copy.deepcopy(
                record["streams"][0]
            )
        )

        with self.assertRaises(
            DeterministicReplayError
        ):
            build_train_replay_source(
                record
            )

    def test_15_reject_fabricated_camera_on_reduced_trajectory(self):
        record = full_record(
            "street_010"
        )
        record["streams"].insert(
            0,
            stream(
                CAMERA_STREAM_ID,
                "camera",
            ),
        )

        with self.assertRaises(
            DeterministicReplayError
        ):
            build_train_replay_source(
                record
            )

    def test_16_reject_missing_stream_on_full_trajectory(self):
        record = full_record()
        record["streams"] = (
            record["streams"][
                1:
            ]
        )

        with self.assertRaises(
            DeterministicReplayError
        ):
            build_train_replay_source(
                record
            )

    def test_17_reject_reference_only_stream(self):
        record = full_record()
        record["streams"][0][
            "reference_only"
        ] = True

        with self.assertRaises(
            DeterministicReplayError
        ):
            build_train_replay_source(
                record
            )

    def test_18_envelope_preserves_raw_payload_and_provenance(self):
        source = build_train_replay_source(
            full_record()
        )
        builder = ReplayEnvelopeBuilder(
            source
        )

        envelope = builder.add(
            source_stream_id=CAMERA_STREAM_ID,
            message_type="sensor_msgs/msg/CompressedImage",
            serialized_payload=b"\x01\x02\x03",
            bag_record_time_ns=100,
            header_stamp_ns=90,
        )

        self.assertEqual(
            envelope.record_index,
            0,
        )
        self.assertEqual(
            envelope.stream_message_index,
            0,
        )
        self.assertEqual(
            envelope.serialized_payload,
            b"\x01\x02\x03",
        )
        self.assertEqual(
            envelope.serialized_payload_bytes,
            3,
        )
        self.assertEqual(
            envelope.bag_record_time_ns,
            100,
        )
        self.assertEqual(
            envelope.header_stamp_ns,
            90,
        )

    def test_19_reader_call_order_is_replay_order_without_timestamp_sort(self):
        source = build_train_replay_source(
            full_record()
        )
        builder = ReplayEnvelopeBuilder(
            source
        )

        first = builder.add(
            source_stream_id=LIDAR_STREAM_ID,
            message_type="sensor_msgs/msg/PointCloud2",
            serialized_payload=b"a",
            bag_record_time_ns=200,
            header_stamp_ns=190,
        )

        second = builder.add(
            source_stream_id=HANDSFREE_IMU_STREAM_ID,
            message_type="sensor_msgs/msg/Imu",
            serialized_payload=b"b",
            bag_record_time_ns=100,
            header_stamp_ns=95,
        )

        self.assertEqual(
            first.record_index,
            0,
        )
        self.assertEqual(
            second.record_index,
            1,
        )

        self.assertGreater(
            first.bag_record_time_ns,
            second.bag_record_time_ns,
        )

    def test_20_per_stream_indices_are_independent(self):
        source = build_train_replay_source(
            full_record()
        )
        builder = ReplayEnvelopeBuilder(
            source
        )

        camera_0 = builder.add(
            source_stream_id=CAMERA_STREAM_ID,
            message_type="camera",
            serialized_payload=b"a",
            bag_record_time_ns=1,
            header_stamp_ns=None,
        )

        lidar_0 = builder.add(
            source_stream_id=LIDAR_STREAM_ID,
            message_type="lidar",
            serialized_payload=b"b",
            bag_record_time_ns=2,
            header_stamp_ns=None,
        )

        camera_1 = builder.add(
            source_stream_id=CAMERA_STREAM_ID,
            message_type="camera",
            serialized_payload=b"c",
            bag_record_time_ns=3,
            header_stamp_ns=None,
        )

        self.assertEqual(
            camera_0.stream_message_index,
            0,
        )
        self.assertEqual(
            lidar_0.stream_message_index,
            0,
        )
        self.assertEqual(
            camera_1.stream_message_index,
            1,
        )

    def test_21_reject_undeclared_stream(self):
        source = build_train_replay_source(
            full_record(
                "street_010"
            )
        )
        builder = ReplayEnvelopeBuilder(
            source
        )

        with self.assertRaises(
            DeterministicReplayError
        ):
            builder.add(
                source_stream_id=CAMERA_STREAM_ID,
                message_type="camera",
                serialized_payload=b"x",
                bag_record_time_ns=1,
                header_stamp_ns=None,
            )

    def test_22_reject_noninteger_bag_record_time(self):
        source = build_train_replay_source(
            full_record()
        )
        builder = ReplayEnvelopeBuilder(
            source
        )

        with self.assertRaises(
            DeterministicReplayError
        ):
            builder.add(
                source_stream_id=LIDAR_STREAM_ID,
                message_type="lidar",
                serialized_payload=b"x",
                bag_record_time_ns=1.0,
                header_stamp_ns=None,
            )

    def test_23_header_stamp_may_be_absent(self):
        source = build_train_replay_source(
            full_record()
        )
        builder = ReplayEnvelopeBuilder(
            source
        )

        envelope = builder.add(
            source_stream_id=HANDSFREE_IMU_STREAM_ID,
            message_type="imu",
            serialized_payload=b"x",
            bag_record_time_ns=1,
            header_stamp_ns=None,
        )

        self.assertIsNone(
            envelope.header_stamp_ns
        )

    def test_24_metadata_payload_does_not_duplicate_raw_payload(self):
        source = build_train_replay_source(
            full_record()
        )
        builder = ReplayEnvelopeBuilder(
            source
        )

        envelope = builder.add(
            source_stream_id=LIDAR_STREAM_ID,
            message_type="lidar",
            serialized_payload=b"payload",
            bag_record_time_ns=5,
            header_stamp_ns=4,
        )

        metadata = envelope.metadata_payload()

        self.assertNotIn(
            "serialized_payload",
            metadata,
        )

        self.assertEqual(
            metadata[
                "serialized_payload_bytes"
            ],
            len(
                b"payload"
            ),
        )

        semantics = metadata[
            "timestamp_semantics"
        ]

        self.assertTrue(
            semantics[
                "bag_record_time_is_transport_provenance"
            ]
        )

        self.assertFalse(
            semantics[
                "bag_record_time_is_proof_of_capture_time"
            ]
        )

        self.assertFalse(
            semantics[
                "header_stamp_is_proof_of_shared_physical_clock"
            ]
        )


class FakeStamp:

    def __init__(
        self,
        sec,
        nanosec,
    ):
        self.sec = sec
        self.nanosec = nanosec


class FakeHeader:

    def __init__(
        self,
        sec,
        nanosec,
    ):
        self.stamp = FakeStamp(
            sec,
            nanosec,
        )


class FakeMessage:

    def __init__(
        self,
        sec,
        nanosec,
    ):
        self.header = FakeHeader(
            sec,
            nanosec,
        )


class FakeConnection:

    def __init__(
        self,
        topic,
        msgtype,
    ):
        self.topic = topic
        self.msgtype = msgtype


def fake_reader_class(
    connections,
    rows,
    decoded,
):
    class FakeReader:

        def __init__(
            self,
            paths,
        ):
            self.paths = paths
            self.connections = list(
                connections
            )

        def __enter__(
            self,
        ):
            return self

        def __exit__(
            self,
            exc_type,
            exc,
            tb,
        ):
            return False

        def messages(
            self,
            *,
            connections,
        ):
            allowed = set(
                connections
            )

            for row in rows:
                if row[0] in allowed:
                    yield row

        def deserialize(
            self,
            rawdata,
            msgtype,
        ):
            return decoded[
                bytes(
                    rawdata
                )
            ]

    return FakeReader


class TestDeterministicMultimodalDatasetReplayReaderIntegration(
    unittest.TestCase
):

    def test_25_manifest_file_digest_and_train_lookup(self):
        payload = {
            "dataset_id":
                "M2DGR",
            "records": [
                full_record(
                    "Circle_01"
                )
            ],
        }

        raw = (
            json.dumps(
                payload,
                sort_keys=True,
            )
            + "\n"
        ).encode(
            "utf-8"
        )

        with tempfile.TemporaryDirectory() as td:
            path = (
                Path(td)
                / "manifest.json"
            )
            path.write_bytes(
                raw
            )

            source = (
                load_train_replay_source_from_manifest_file(
                    path,
                    "Circle_01",
                    expected_file_sha256=sha256(
                        raw
                    ).hexdigest(),
                )
            )

        self.assertEqual(
            source.trajectory_id,
            "Circle_01",
        )

    def test_26_manifest_file_digest_mismatch_rejected(self):
        payload = {
            "dataset_id":
                "M2DGR",
            "records": [
                full_record()
            ],
        }

        with tempfile.TemporaryDirectory() as td:
            path = (
                Path(td)
                / "manifest.json"
            )
            path.write_text(
                json.dumps(
                    payload
                ),
                encoding="utf-8",
            )

            with self.assertRaises(
                DeterministicReplayError
            ):
                load_train_replay_source_from_manifest_file(
                    path,
                    "Circle_01",
                    expected_file_sha256="0" * 64,
                )

    def test_27_anyreader_order_preserved_without_sorting(self):
        source = build_train_replay_source(
            full_record()
        )

        connections = [
            FakeConnection(
                CAMERA_STREAM_ID,
                "camera_type",
            ),
            FakeConnection(
                D435I_IMU_STREAM_ID,
                "d435i_imu_type",
            ),
            FakeConnection(
                HANDSFREE_IMU_STREAM_ID,
                "handsfree_imu_type",
            ),
            FakeConnection(
                LIDAR_STREAM_ID,
                "lidar_type",
            ),
            FakeConnection(
                "/unrelated",
                "other_type",
            ),
        ]

        rows = [
            (
                connections[3],
                300,
                b"lidar",
            ),
            (
                connections[0],
                100,
                b"camera",
            ),
            (
                connections[2],
                200,
                b"imu",
            ),
            (
                connections[4],
                50,
                b"ignored",
            ),
        ]

        decoded = {
            b"lidar":
                FakeMessage(
                    3,
                    30,
                ),
            b"camera":
                FakeMessage(
                    1,
                    10,
                ),
            b"imu":
                FakeMessage(
                    2,
                    20,
                ),
            b"ignored":
                FakeMessage(
                    0,
                    1,
                ),
        }

        Reader = fake_reader_class(
            connections,
            rows,
            decoded,
        )

        with tempfile.TemporaryDirectory() as td:
            bag = (
                Path(td)
                / "Circle_01.bag"
            )
            bag.write_bytes(
                b"fake"
            )

            envelopes = list(
                iter_anyreader_replay(
                    source,
                    bag,
                    reader_class=Reader,
                )
            )

        self.assertEqual(
            [
                e.source_stream_id
                for e in envelopes
            ],
            [
                LIDAR_STREAM_ID,
                CAMERA_STREAM_ID,
                HANDSFREE_IMU_STREAM_ID,
            ],
        )

        self.assertEqual(
            [
                e.record_index
                for e in envelopes
            ],
            [
                0,
                1,
                2,
            ],
        )

        self.assertEqual(
            [
                e.bag_record_time_ns
                for e in envelopes
            ],
            [
                300,
                100,
                200,
            ],
        )

    def test_28_anyreader_preserves_direct_header_stamp(self):
        source = build_train_replay_source(
            full_record()
        )

        connection = FakeConnection(
            HANDSFREE_IMU_STREAM_ID,
            "imu_type",
        )

        connections = [
            FakeConnection(
                CAMERA_STREAM_ID,
                "camera_type",
            ),
            FakeConnection(
                D435I_IMU_STREAM_ID,
                "d435i_type",
            ),
            connection,
            FakeConnection(
                LIDAR_STREAM_ID,
                "lidar_type",
            ),
        ]

        rows = [
            (
                connection,
                900,
                b"x",
            )
        ]

        decoded = {
            b"x":
                FakeMessage(
                    12,
                    345,
                )
        }

        Reader = fake_reader_class(
            connections,
            rows,
            decoded,
        )

        with tempfile.TemporaryDirectory() as td:
            bag = (
                Path(td)
                / "Circle_01.bag"
            )
            bag.write_bytes(
                b"fake"
            )

            envelope = next(
                iter_anyreader_replay(
                    source,
                    bag,
                    reader_class=Reader,
                )
            )

        self.assertEqual(
            envelope.header_stamp_ns,
            12_000_000_345,
        )

        self.assertEqual(
            envelope.bag_record_time_ns,
            900,
        )

    def test_29_reduced_trajectory_rejects_fabricated_supported_connection(self):
        source = build_train_replay_source(
            full_record(
                "street_010"
            )
        )

        connections = [
            FakeConnection(
                CAMERA_STREAM_ID,
                "camera_type",
            ),
            FakeConnection(
                HANDSFREE_IMU_STREAM_ID,
                "imu_type",
            ),
            FakeConnection(
                LIDAR_STREAM_ID,
                "lidar_type",
            ),
        ]

        Reader = fake_reader_class(
            connections,
            [],
            {},
        )

        with tempfile.TemporaryDirectory() as td:
            bag = (
                Path(td)
                / "street_010.bag"
            )
            bag.write_bytes(
                b"fake"
            )

            with self.assertRaises(
                DeterministicReplayError
            ):
                list(
                    iter_anyreader_replay(
                        source,
                        bag,
                        reader_class=Reader,
                    )
                )

    def test_30_unrelated_nonreplay_connection_is_ignored(self):
        source = build_train_replay_source(
            full_record(
                "street_09"
            )
        )

        hf = FakeConnection(
            HANDSFREE_IMU_STREAM_ID,
            "imu_type",
        )

        lidar = FakeConnection(
            LIDAR_STREAM_ID,
            "lidar_type",
        )

        other = FakeConnection(
            "/tf",
            "tf_type",
        )

        connections = [
            hf,
            lidar,
            other,
        ]

        rows = [
            (
                other,
                1,
                b"ignored",
            ),
            (
                hf,
                2,
                b"imu",
            ),
        ]

        decoded = {
            b"ignored":
                FakeMessage(
                    0,
                    1,
                ),
            b"imu":
                FakeMessage(
                    0,
                    2,
                ),
        }

        Reader = fake_reader_class(
            connections,
            rows,
            decoded,
        )

        with tempfile.TemporaryDirectory() as td:
            bag = (
                Path(td)
                / "street_09.bag"
            )
            bag.write_bytes(
                b"fake"
            )

            envelopes = list(
                iter_anyreader_replay(
                    source,
                    bag,
                    reader_class=Reader,
                )
            )

        self.assertEqual(
            len(
                envelopes
            ),
            1,
        )

        self.assertEqual(
            envelopes[0].source_stream_id,
            HANDSFREE_IMU_STREAM_ID,
        )


if __name__ == "__main__":
    unittest.main()
