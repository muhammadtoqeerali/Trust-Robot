from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from trust_robot.data_contracts import (
    MeasurementTimeBasis,
    ReferenceCoverage,
    SplitRole,
    SynchronizationSpec,
    TrajectoryRecord,
    VerificationStatus,
)
from trust_robot.m2dgr_manifest_builder import (
    build_phase3_timing_successor_payload,
    build_reference,
    build_streams,
    build_streams_for_trajectory,
    build_synchronization_for_trajectory,
)
from trust_robot.m2dgr_reference_quality import (
    build_m2dgr_reference_quality_payload,
)
from trust_robot.reference_quality import (
    write_immutable_reference_quality_artifact,
)
from trust_robot.trajectory_manifest import (
    build_trajectory_manifest,
)


TOPICS = (
    "/camera/color/image_raw/compressed",
    "/camera/imu",
    "/handsfree/imu",
    "/velodyne_points",
)


def _stream_block(available: bool):
    if not available:
        return {
            "message_count": 0,
            "header_count": 0,
            "decode_error_count": 0,
            "message_types": [],
            "frame_ids": {},
            "header_time": None,
            "record_time": None,
            "record_minus_header_ms": None,
            "largest_header_intervals": [],
            "largest_absolute_record_header_offsets": [],
            "decode_error_examples": [],
            "common_header_range_diagnostic": {
                "samples_before": None,
                "samples_after": None,
                "samples_outside": None,
                "sample_exclusion_rule": False,
            },
        }

    return {
        "message_count": 2,
        "header_count": 2,
        "decode_error_count": 0,
        "message_types": ["sensor_msgs/msg/Imu"],
        "frame_ids": {"synthetic": 2},
        "header_time": {
            "first_ns": 1,
            "last_ns": 2,
            "min_ns": 1,
            "max_ns": 2,
            "duplicate_count": 0,
            "reverse_count": 0,
            "positive_interval_ms": {
                "count": 1,
                "min": 1.0,
                "median": 1.0,
                "p05": 1.0,
                "p95": 1.0,
                "p99": 1.0,
                "max": 1.0,
            },
        },
        "record_time": {
            "first_ns": 1,
            "last_ns": 2,
            "duplicate_count": 0,
            "reverse_count": 0,
            "positive_interval_ms": {
                "count": 1,
                "min": 1.0,
                "median": 1.0,
                "p05": 1.0,
                "p95": 1.0,
                "p99": 1.0,
                "max": 1.0,
            },
        },
        "record_minus_header_ms": {
            "count": 2,
            "min": 0.0,
            "median": 0.0,
            "p05": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "max": 0.0,
        },
        "record_minus_header_sign_counts": {
            "negative": 0,
            "zero": 2,
            "positive": 0,
        },
        "largest_header_intervals": [],
        "largest_absolute_record_header_offsets": [],
        "decode_error_examples": [],
        "common_header_range_diagnostic": {
            "samples_before": 0,
            "samples_after": 0,
            "samples_outside": 0,
            "sample_exclusion_rule": False,
        },
    }


def _write_timing_artifact(
    root: Path,
    trajectory_id: str,
    available=TOPICS,
):
    available = tuple(available)
    missing = [topic for topic in TOPICS if topic not in available]
    streams = {
        topic: _stream_block(topic in available)
        for topic in TOPICS
    }

    payload = {
        "schema": "trust_robot.m2dgr_phase3_stream_timing",
        "version": 1,
        "trajectory_id": trajectory_id,
        "source": {
            "relative_path": f"raw/rosbags/{trajectory_id}.bag",
            "size_bytes": 123,
            "recorded_sha256": "1" * 64,
            "checksum_sidecar": f"checksums/{trajectory_id}.bag.sha256",
            "raw_modified": False,
        },
        "reader": {
            "package": "rosbags",
            "version": "0.11.5",
            "message_deserialization": True,
            "targeted_stream_scan": True,
            "image_pixels_decoded": False,
            "pointcloud_points_interpreted": False,
            "scan_completed": True,
        },
        "policy": {
            "characterization_only": True,
            "measurement_time_basis": "sensor_header_stamp",
            "bag_record_time_role": "transport_provenance_diagnostic_only",
            "nearest_neighbor_is_sync_proof": False,
            "common_range_is_sync_proof": False,
            "automatic_sample_exclusion_rule_created": False,
            "fixed_time_offset_estimated": False,
            "fixed_time_offset_applied": False,
            "synchronization_tolerance_frozen": False,
            "synchronization_verified": False,
        },
        "available_target_topics": list(available),
        "missing_target_topics": missing,
        "total_target_messages": sum(
            item["message_count"]
            for item in streams.values()
        ),
        "total_decode_errors": 0,
        "common_header_range": {
            "start_ns": 1 if len(available) == 4 else None,
            "end_ns": 2 if len(available) == 4 else None,
            "interpretation": "numeric_header_range_intersection_only",
            "synchronization_claim": False,
        },
        "streams": streams,
        "pairs": {},
    }

    path = (
        root
        / "audit"
        / "phase3_staging"
        / "stream_timing_v1"
        / f"{trajectory_id}_phase3_stream_timing_v1.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class M2DGRManifestBuilderTests(unittest.TestCase):
    def _prepare_reference(
        self,
        root: Path,
        trajectory_id: str,
        rows: str,
    ):
        gt_root = root / "raw" / "ground_truth"
        gt_root.mkdir(parents=True, exist_ok=True)
        gt = gt_root / f"{trajectory_id}.txt"
        gt.write_text(rows, encoding="ascii")

        payload = build_m2dgr_reference_quality_payload(
            gt,
            trajectory_id=trajectory_id,
        )
        quality = (
            root
            / "audit"
            / "reference_quality"
            / f"{trajectory_id}_reference_quality.json"
        )
        write_immutable_reference_quality_artifact(
            quality,
            payload,
        )
        return gt, quality

    def test_reference_requires_quality_artifact(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            gt_root = root / "raw" / "ground_truth"
            gt_root.mkdir(parents=True)
            gt = gt_root / "room_01.txt"
            gt.write_text(
                "1.0 0 0 0 0 0 0 1\n"
                "1.02 0 0 0 0 0 0 1\n",
                encoding="ascii",
            )
            with self.assertRaises(FileNotFoundError):
                build_reference(root, gt, "room_01")

    def test_mocap_reference_uses_quality_artifact_and_unknown_coverage(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            gt, quality = self._prepare_reference(
                root,
                "room_01",
                "1.0 0 0 0 0 0 0 1\n"
                "1.02 0 0 0 0 0 0 1\n",
            )
            reference = build_reference(
                root,
                gt,
                "room_01",
            )
            expected = quality.relative_to(root).as_posix()
            self.assertEqual(
                reference.coverage,
                ReferenceCoverage.UNKNOWN,
            )
            self.assertEqual(
                reference.translation_coverage,
                ReferenceCoverage.UNKNOWN,
            )
            self.assertEqual(
                reference.rotation_coverage,
                ReferenceCoverage.UNKNOWN,
            )
            self.assertEqual(
                reference.translation_validity_artifact,
                expected,
            )
            self.assertEqual(
                reference.rotation_validity_artifact,
                expected,
            )

    def test_leica_reference_is_translation_only_without_dummy_interval(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            gt, quality = self._prepare_reference(
                root,
                "lift_01",
                "1.0 0 0 0 0 0 0 0\n"
                "1.14 1 0 0 0 0 0 0\n",
            )
            reference = build_reference(
                root,
                gt,
                "lift_01",
            )
            self.assertTrue(reference.supports_translation)
            self.assertFalse(reference.supports_rotation)
            self.assertEqual(
                reference.translation_validity_artifact,
                quality.relative_to(root).as_posix(),
            )
            self.assertIsNone(
                reference.rotation_validity_artifact
            )
            self.assertEqual(
                reference.coverage,
                ReferenceCoverage.UNKNOWN,
            )

    def test_stream_inventory_is_trajectory_specific(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_timing_artifact(
                root,
                "street_09",
                available=(
                    "/handsfree/imu",
                    "/velodyne_points",
                ),
            )
            streams = build_streams_for_trajectory(
                root,
                "street_09",
            )
            self.assertEqual(
                {stream.stream_id for stream in streams},
                {
                    "/handsfree/imu",
                    "/velodyne_points",
                },
            )

    def test_sync_records_header_basis_but_remains_unverified(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_timing_artifact(
                root,
                "gate_01",
            )
            streams = build_streams_for_trajectory(
                root,
                "gate_01",
            )
            sync = build_synchronization_for_trajectory(
                root,
                "gate_01",
                streams,
            )
            self.assertEqual(len(sync), 4)
            for item in sync:
                self.assertEqual(
                    item.verification_status,
                    VerificationStatus.UNVERIFIED,
                )
                self.assertEqual(
                    item.measurement_time_basis,
                    MeasurementTimeBasis.SENSOR_HEADER_STAMP,
                )
                self.assertIsNone(
                    item.tolerance_seconds
                )
                self.assertIsNone(
                    item.fixed_offset_seconds
                )
                self.assertIn(
                    "synchronization not yet verified",
                    item.method,
                )


    def test_phase3_successor_filters_streams_without_verifying_sync(self):
        with TemporaryDirectory() as tmp:
            root = Path(
                tmp
            )

            _write_timing_artifact(
                root,
                "street_09",
                available=(
                    "/handsfree/imu",
                    "/velodyne_points",
                ),
            )

            source_streams = build_streams()

            source_record = TrajectoryRecord(
                dataset_id="M2DGR",
                trajectory_id="street_09",
                base_trajectory_id="street_09",
                split=SplitRole.TRAIN,
                streams=source_streams,
                references=(),
            )

            source_sync = tuple(
                SynchronizationSpec(
                    stream_id=stream.stream_id,
                    clock_domain=stream.clock_domain,
                    verification_status=(
                        VerificationStatus.UNVERIFIED
                    ),
                )
                for stream in source_streams
            )

            phase2 = build_trajectory_manifest(
                (
                    source_record,
                ),
                {
                    "street_09":
                        source_sync,
                },
            )

            original_phase2 = json.loads(
                json.dumps(
                    phase2
                )
            )

            successor = (
                build_phase3_timing_successor_payload(
                    root,
                    phase2,
                )
            )

            self.assertEqual(
                phase2,
                original_phase2,
            )

            row = successor[
                "records"
            ][0]

            self.assertEqual(
                {
                    item[
                        "stream_id"
                    ]
                    for item in row[
                        "streams"
                    ]
                },
                {
                    "/handsfree/imu",
                    "/velodyne_points",
                },
            )

            self.assertEqual(
                {
                    item[
                        "stream_id"
                    ]
                    for item in row[
                        "synchronization"
                    ]
                },
                {
                    "/handsfree/imu",
                    "/velodyne_points",
                },
            )

            for item in row[
                "synchronization"
            ]:
                self.assertEqual(
                    item[
                        "verification_status"
                    ],
                    "unverified",
                )

                self.assertEqual(
                    item[
                        "measurement_time_basis"
                    ],
                    "sensor_header_stamp",
                )

                self.assertIsNone(
                    item[
                        "tolerance_seconds"
                    ]
                )

                self.assertIsNone(
                    item[
                        "fixed_offset_seconds"
                    ]
                )


if __name__ == "__main__":
    unittest.main()
