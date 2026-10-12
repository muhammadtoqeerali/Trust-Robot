import unittest

import numpy as np

from trust_robot.isaacsim_v15_diagnostic_bridge import (
    camera_features,
    imu_features,
    lidar_structure,
    canonical_line,
    require_hash,
)


class BridgeTests(unittest.TestCase):
    def test_camera_frozen_features_and_blackout(self):
        image = np.zeros((120, 160, 4), dtype=np.uint8)
        image[:, :, 3] = 255

        self.assertEqual(
            list(camera_features(image).values()),
            [0.0, 0.0, 0.0],
        )

        image[:, :, 0] = 255
        self.assertGreater(
            camera_features(image)[
                "gray_mean_intensity_8bit"
            ],
            0,
        )

    def test_camera_rejects_wrong_shape(self):
        with self.assertRaises(ValueError):
            camera_features(
                np.zeros((2, 2, 4), dtype=np.uint8)
            )

    def test_imu_frozen_features_and_absence(self):
        output = imu_features({
            "angular_velocity": [3.0, 4.0, 0.0],
            "linear_acceleration": [0.0, 0.0, 5.0],
        })

        self.assertEqual(
            output["features"]["angular_speed_norm_rad_s"],
            5.0,
        )
        self.assertEqual(
            output["features"]["linear_acceleration_norm_m_s2"],
            5.0,
        )
        self.assertIsNone(
            imu_features({"angular_velocity": None})[
                "features"
            ]
        )

    def test_lidar_structure_and_sparse_intervention(self):
        cloud = np.arange(
            48, dtype=np.float32
        ).reshape(16, 3)

        self.assertEqual(
            lidar_structure(cloud)["point_count"], 16
        )
        self.assertEqual(
            lidar_structure(cloud[::2])["point_count"], 8
        )
        self.assertNotIn(
            "fixed_point_iterations",
            lidar_structure(cloud),
        )

        cloud[0, 0] = np.nan

        with self.assertRaises(ValueError):
            lidar_structure(cloud)

    def test_no_nonfinite_json_output(self):
        with self.assertRaises(ValueError):
            canonical_line({"feature": float("nan")})

    def test_bad_source_hash_rejected(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data"
            path.write_bytes(b"a")

            with self.assertRaises(ValueError):
                require_hash(path, "0" * 64)


if __name__ == "__main__":
    unittest.main()
