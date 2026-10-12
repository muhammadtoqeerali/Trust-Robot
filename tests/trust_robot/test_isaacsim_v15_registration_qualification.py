import tempfile
import unittest
from pathlib import Path

import numpy as np

from trust_robot.isaacsim_v15_registration_qualification import (
    bounded_registration,
    json_bytes,
    pair_records,
    spatial_rank,
    timing_readiness,
)


class QualificationTests(unittest.TestCase):
    def setUp(self):
        self.cloud = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
            [2, 2, 2],
            [1, 2, 3],
            [3, 1, 2],
            [2, 3, 1],
        ], dtype=np.float32)

    def test_frozen_registration_identical_cloud(self):
        result = bounded_registration(self.cloud, self.cloud)
        self.assertEqual(
            result["status"],
            "FROZEN_REGISTRATION_DIAGNOSTICS_AVAILABLE",
        )
        self.assertEqual(
            result["features"]["source_point_count"], 8
        )
        self.assertEqual(
            result["features"]["final_correspondence_count"], 8
        )

    def test_sparse_cloud_registration(self):
        result = bounded_registration(
            self.cloud, self.cloud[::2].copy()
        )
        if result["features"] is not None:
            self.assertEqual(
                result["features"]["source_point_count"], 4
            )
            self.assertEqual(
                result["features"]["target_point_count"], 8
            )
        else:
            self.assertIsNotNone(result["error_code"])

    def test_invalid_cloud_fails_without_fabricated_features(self):
        invalid = self.cloud.copy()
        invalid[0, 0] = np.nan
        result = bounded_registration(self.cloud, invalid)
        self.assertIsNone(result["features"])
        self.assertEqual(
            result["status"], "REGISTRATION_UNAVAILABLE"
        )

    def test_spatial_rank_not_reliability_probability(self):
        self.assertEqual(spatial_rank(self.cloud), 3)
        self.assertEqual(
            spatial_rank(np.array([
                [0, 0, 0],
                [1, 0, 0],
                [2, 0, 0],
            ], dtype=np.float32)),
            1,
        )

    def test_pair_topology(self):
        scans = {
            "clean": [self.cloud.copy() for _ in range(6)],
            "intervention": [
                self.cloud[::2].copy() if i == 2
                else self.cloud.copy()
                for i in range(6)
            ],
        }
        frames = [{"step": 31 + i * 10} for i in range(6)]
        output = pair_records(scans, frames)

        self.assertEqual(len(output), 10)
        self.assertEqual(
            [r["condition"] for r in output],
            ["clean"] * 5 + ["intervention"] * 5,
        )
        self.assertFalse(
            any(r["physical_synchronization_verified"] for r in output)
        )

    def test_nonfinite_serialization_rejected(self):
        with self.assertRaises(ValueError):
            json_bytes({"value": float("nan")})

    def test_timing_readiness_does_not_claim_sync(self):
        frames = [{
            "step": 31 + i * 10,
            "camera_read_step_time_s": float(i+1),
            "lidar_read_step_time_s": float(i+1),
            "acquisition_timing_verified": False,
            "cross_sensor_synchronization_verified": False,
        } for i in range(6)]
        poses = [{
            "step": i+1,
            "simulation_step_time_s": float(i+1),
            "pose_source": "USD_COMPOSED_WORLD_TRANSFORM",
            "physics_pose_independently_verified": False,
        } for i in range(90)]
        imu = [{
            "step": i+1,
            "timestamp_semantics_verified": False,
        } for i in range(90)]

        output = timing_readiness(frames, poses, imu)
        self.assertTrue(
            output["same_step_camera_lidar_read_time_values_equal"]
        )
        self.assertFalse(
            output["same_step_read_time_values_prove_synchronization"]
        )

        frames[3]["lidar_read_step_time_s"] = -1.0
        with self.assertRaises(ValueError):
            timing_readiness(frames, poses, imu)


if __name__ == "__main__":
    unittest.main()
