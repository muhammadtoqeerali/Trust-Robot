"""Regression tests for Isaac Sim V16 capture evidence."""

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(
    0, str(ROOT / "scripts/trust_robot")
)

from verify_isaacsim_v16_capture_v1 import (
    qualify,
    valid_camera,
)


def fixtures():
    a = {
        "schema": "TRUST_ROBOT_V16_REPLICATOR_CAPTURE_V1",
        "intervention": (
            "MANUAL_REPLICATOR_CAPTURE_RT_SUBFRAMES_4"
        ),
        "manual_capture_events": ["PASS"] * 6,
        "direct_rgb_samples": (
            [{"shape": [0]}]
            + [{
                "shape": [120, 160, 4],
                "valid_shape": True,
                "rgb_nonzero_fraction": 0.92,
            }] * 5
        ),
        "valid_direct_rgb_frames": 5,
        "accepted_camera_frames": 5,
        "accepted_lidar_scans": 0,
        "accepted_imu_records": 90,
        "runtime_success_marker": False,
    }

    b = {
        "schema": "TRUST_ROBOT_V16_LIDAR_WORKAROUND_V1",
        "intervention": (
            "RTX_LIDAR_SKIP_DROPPING_INVALID_POINTS_TRUE"
        ),
        "result": "LIDAR_WORKAROUND_NOT_EFFECTIVE",
        "camera_frames_accepted": 5,
        "lidar_scans_accepted": 0,
        "lidar_geometry_valid_samples": 0,
        "imu_records_accepted": 90,
        "full_runtime_pass": False,
        "lidar_geometry_samples": [
            {"shape": [0]} for _ in range(6)
        ],
    }

    c = {
        "schema": "TRUST_ROBOT_V16_SDG_WRITER_TEST_V1",
        "intervention": (
            "EVENT_WRITER_ON_EXISTING_LIDAR_ANNOTATOR"
        ),
        "classification": (
            "EVENT_WRITER_EXECUTED_WITHOUT_VALID_LIDAR"
        ),
        "sdg_writer_callback_count": 5,
        "valid_geometry_callback_count": 0,
        "accepted_camera_frames": 5,
        "accepted_cached_lidar_scans": 0,
        "accepted_imu_records": 90,
        "full_runtime_qualified": False,
        "saved_event_clouds": [],
        "event_samples": [{
            "shape": [0],
            "valid_geometry": False,
            "data_keys": [
                "reference_time",
                "swhFrameNumber",
            ],
        } for _ in range(5)],
    }

    return a, b, c


class CaptureEvidenceTests(unittest.TestCase):

    def test_expected_regression_evidence(self):
        result = qualify(*fixtures())
        self.assertEqual(
            result["camera_recovery"], "PARTIAL"
        )
        self.assertEqual(
            result["lidar_recovery"], "NOT_ACHIEVED"
        )
        self.assertFalse(
            result["complete_runtime_qualified"]
        )

    def test_camera_empty_is_not_valid(self):
        self.assertFalse(
            valid_camera({"shape": [0]})
        )

    def test_wrong_camera_count_rejected(self):
        a, b, c = fixtures()
        a["accepted_camera_frames"] = 6
        with self.assertRaises(ValueError):
            qualify(a, b, c)

    def test_false_lidar_success_rejected(self):
        a, b, c = fixtures()
        b["lidar_scans_accepted"] = 1
        with self.assertRaises(ValueError):
            qualify(a, b, c)

    def test_missing_writer_events_rejected(self):
        a, b, c = fixtures()
        c["event_samples"] = []
        with self.assertRaises(ValueError):
            qualify(a, b, c)

    def test_missing_reference_time_key_rejected(self):
        a, b, c = fixtures()
        c["event_samples"][0]["data_keys"] = []
        with self.assertRaises(ValueError):
            qualify(a, b, c)

    def test_writer_does_not_prove_valid_geometry(self):
        a, b, c = fixtures()
        c = copy.deepcopy(c)
        c["valid_geometry_callback_count"] = 1
        with self.assertRaises(ValueError):
            qualify(a, b, c)


if __name__ == "__main__":
    unittest.main(verbosity=2)
