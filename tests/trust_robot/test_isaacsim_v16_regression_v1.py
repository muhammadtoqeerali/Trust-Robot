"""Tests for V16 regression evidence semantics."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(
    0, str(ROOT / "scripts/trust_robot")
)

from audit_isaacsim_v16_regression_v1 import (
    summarize,
    compare,
)


class RegressionAuditTests(unittest.TestCase):

    def test_historical_success_markers(self):
        text = (
            "MULTIMODAL_RUNTIME=PASS\n"
            "TIMESERIES_CAMERA_FRAMES=6\n"
            "TIMESERIES_LIDAR_FRAMES=6\n"
        )
        result = summarize(text)
        self.assertTrue(result["runtime_pass"])
        self.assertTrue(
            result["historical_camera_success_marker"]
        )

    def test_empty_arrays_are_not_black_images(self):
        text = (
            'V16_CAMERA_SAMPLE '
            '{"step":31,"shape":[0],"state":"ARRAY"}\n'
            "V16_CAMERA_ACCEPTED_FRAME_COUNT= 0\n"
        )
        result = summarize(text)
        self.assertEqual(
            result["empty_camera_samples"], 1
        )
        self.assertEqual(
            result["accepted_cameras"], 0
        )

    def test_timeline_clock_distinction(self):
        text = (
            'TIMELINE_SAMPLE '
            '{"step":1,"world_time_s":0.05,'
            '"timeline_time_s":-0.01666,'
            '"timeline_playing":true}\n'
            'TIMELINE_SAMPLE '
            '{"step":90,"world_time_s":1.5333,'
            '"timeline_time_s":-0.01665,'
            '"timeline_playing":true}\n'
        )
        result = summarize(text)
        self.assertGreater(
            result["world_clock_span_s"], 1.0
        )
        self.assertLess(
            result["timeline_clock_span_s"], 0.001
        )

    def test_bad_synthetic_log_not_promoted(self):
        historical = (
            "MULTIMODAL_RUNTIME=PASS\n"
            "TIMESERIES_CAMERA_FRAMES=6\n"
            "TIMESERIES_LIDAR_FRAMES=6\n"
        )
        with self.assertRaises(AssertionError):
            compare(
                historical,
                "MULTIMODAL_RUNTIME=PASS\n",
                "",
                "",
            )


if __name__ == "__main__":
    unittest.main()
