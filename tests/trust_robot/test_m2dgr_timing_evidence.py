from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from trust_robot.m2dgr_timing_evidence import (
    M2DGRTimingEvidenceError,
    available_stream_ids,
    build_m2dgr_timing_evidence_index,
    validate_exact_header_anomaly_payload,
    validate_m2dgr_stream_timing_payload,
    validate_m2dgr_timing_evidence_index,
)


TOPICS = (
    "/camera/color/image_raw/compressed",
    "/camera/imu",
    "/handsfree/imu",
    "/velodyne_points",
)


def stream_block(available: bool, reverse_count: int = 0):
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
        "message_count": 3,
        "header_count": 3,
        "decode_error_count": 0,
        "message_types": ["sensor_msgs/msg/Imu"],
        "frame_ids": {"synthetic": 3},
        "header_time": {
            "first_ns": 1,
            "last_ns": 3,
            "min_ns": 1,
            "max_ns": 3,
            "duplicate_count": 0,
            "reverse_count": reverse_count,
            "positive_interval_ms": {
                "count": 2,
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
            "last_ns": 3,
            "duplicate_count": 0,
            "reverse_count": 0,
            "positive_interval_ms": {
                "count": 2,
                "min": 1.0,
                "median": 1.0,
                "p05": 1.0,
                "p95": 1.0,
                "p99": 1.0,
                "max": 1.0,
            },
        },
        "record_minus_header_ms": {
            "count": 3,
            "min": 0.0,
            "median": 0.0,
            "p05": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "max": 0.0,
        },
        "record_minus_header_sign_counts": {
            "negative": 0,
            "zero": 3,
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


def make_payload(
    trajectory_id="synthetic_01",
    available=TOPICS,
    reverse_topic=None,
):
    available = tuple(available)
    missing = [topic for topic in TOPICS if topic not in available]
    streams = {
        topic: stream_block(
            topic in available,
            reverse_count=(
                1 if topic == reverse_topic else 0
            ),
        )
        for topic in TOPICS
    }

    return {
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
            stream["message_count"]
            for stream in streams.values()
        ),
        "total_decode_errors": 0,
        "common_header_range": {
            "start_ns": 1 if len(available) == len(TOPICS) else None,
            "end_ns": 3 if len(available) == len(TOPICS) else None,
            "interpretation": "numeric_header_range_intersection_only",
            "synchronization_claim": False,
        },
        "streams": streams,
        "pairs": {},
    }


def make_exact_anomaly_payload():
    return {
        "schema": "trust_robot.m2dgr_exact_header_anomaly",
        "version": 1,
        "trajectory_id": "hall_05",
        "topic": "/camera/imu",
        "source": {
            "relative_path": "raw/rosbags/hall_05.bag",
            "recorded_sha256": "2" * 64,
            "checksum_sidecar": "checksums/hall_05.bag.sha256",
            "raw_modified": False,
        },
        "reader": {
            "message_deserialization": True,
            "package": "rosbags",
            "scan_completed": True,
            "targeted_topic_scan": True,
            "version": "0.11.5",
        },
        "stream": {
            "duplicate_count": 0,
            "first_header_ns": 1,
            "frame_ids": ["camera_imu_optical_frame"],
            "last_header_ns": 200,
            "message_count": 10,
            "message_types": ["sensor_msgs/msg/Imu"],
            "reverse_count": 1,
        },
        "reversals": [
            {
                "context": [],
                "current_header_ns": 50,
                "current_index": 6,
                "current_record_minus_header_ns": 0,
                "current_record_ns": 50,
                "delta_ms": -0.00005,
                "delta_ns": -50,
                "previous_header_ns": 100,
                "previous_index": 5,
                "previous_record_minus_header_ns": 0,
                "previous_record_ns": 100,
            }
        ],
        "duplicates": [],
        "comparison": {
            "aggregate_artifact": (
                "audit/phase3_staging/stream_timing_v1/"
                "hall_05_phase3_stream_timing_v1.json"
            ),
            "aggregate_reverse_count": 1,
            "counts_match": True,
            "targeted_reverse_count": 1,
        },
        "policy": {
            "automatic_sample_exclusion_rule_created": False,
            "automatic_sample_repair": False,
            "fixed_time_offset_estimated": False,
            "structural_reverse_timestamp": True,
            "synchronization_tolerance_frozen": False,
            "synchronization_verified": False,
            "threshold_required_to_detect": False,
        },
    }


class M2DGRTimingEvidenceTests(unittest.TestCase):
    def test_valid_payload_preserves_stream_inventory(self):
        payload = make_payload(
            trajectory_id="street_09",
            available=(
                "/handsfree/imu",
                "/velodyne_points",
            ),
        )
        validate_m2dgr_stream_timing_payload(payload)
        self.assertEqual(
            available_stream_ids(payload),
            (
                "/handsfree/imu",
                "/velodyne_points",
            ),
        )

    def test_unsafe_sync_claim_is_rejected(self):
        payload = make_payload()
        payload["policy"]["synchronization_verified"] = True
        with self.assertRaises(M2DGRTimingEvidenceError):
            validate_m2dgr_stream_timing_payload(payload)

    def test_missing_topic_cannot_contain_samples(self):
        payload = make_payload(
            available=(
                "/handsfree/imu",
                "/velodyne_points",
            )
        )
        payload["streams"]["/camera/imu"]["message_count"] = 1
        with self.assertRaises(M2DGRTimingEvidenceError):
            validate_m2dgr_stream_timing_payload(payload)

    def test_exact_reversal_is_threshold_free_structural_evidence(self):
        payload = make_exact_anomaly_payload()
        validate_exact_header_anomaly_payload(payload)
        self.assertEqual(
            payload["reversals"][0]["delta_ns"],
            -50,
        )

    def test_fake_non_reversal_is_rejected(self):
        payload = make_exact_anomaly_payload()
        payload["reversals"][0]["current_header_ns"] = 150
        with self.assertRaises(M2DGRTimingEvidenceError):
            validate_exact_header_anomaly_payload(payload)

    def test_index_hash_binds_timing_and_exact_anomaly_artifacts(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            timing_root = (
                root
                / "audit"
                / "phase3_staging"
                / "stream_timing_v1"
            )
            timing_root.mkdir(parents=True)

            for trajectory in ("hall_05", "street_09"):
                payload = make_payload(
                    trajectory_id=trajectory,
                    available=(
                        (
                            "/handsfree/imu",
                            "/velodyne_points",
                        )
                        if trajectory == "street_09"
                        else TOPICS
                    ),
                    reverse_topic=(
                        "/camera/imu"
                        if trajectory == "hall_05"
                        else None
                    ),
                )
                (
                    timing_root
                    / f"{trajectory}_phase3_stream_timing_v1.json"
                ).write_text(
                    json.dumps(payload),
                    encoding="utf-8",
                )

            exact_root = (
                root
                / "audit"
                / "phase3_staging"
                / "exact_anomalies"
            )
            exact_root.mkdir(parents=True)
            (
                exact_root
                / "hall_05_camera_imu_reverse_v1.json"
            ).write_text(
                json.dumps(make_exact_anomaly_payload()),
                encoding="utf-8",
            )

            index = build_m2dgr_timing_evidence_index(
                root,
                ("hall_05", "street_09"),
            )
            validate_m2dgr_timing_evidence_index(index)
            self.assertEqual(index["trajectory_count"], 2)
            self.assertEqual(
                index["exact_anomaly_artifact_count"],
                1,
            )
            self.assertFalse(
                index["policy"]["synchronization_verified"]
            )


if __name__ == "__main__":
    unittest.main()
