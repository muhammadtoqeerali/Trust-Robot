import unittest

import numpy as np

from trust_robot.visual_pixel_motion import (
    VisualMotionError,
    controlled_pixel_study,
    estimate_pixel_motion,
    grayscale,
    require_metric_camera_factor,
)


class PixelMotionTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(123)
        cls.image = rng.integers(
            0, 256, (120, 160), dtype=np.uint8
        )

    def test_horizontal_vertical_displacement(self):
        shifted = np.roll(
            self.image, (-3, 5), axis=(0, 1)
        )
        row = estimate_pixel_motion(self.image, shifted)
        self.assertEqual(
            row["status"], "PIXEL_TRANSLATION_OBSERVED"
        )
        self.assertEqual(
            (row["pixel_displacement_dy"],
             row["pixel_displacement_dx"]),
            (-3, 5),
        )
        self.assertGreaterEqual(
            row["patch_evidence"][
                "correlated_patch_count"], 8
        )

    def test_stationary_image(self):
        row = estimate_pixel_motion(
            self.image, self.image
        )
        self.assertEqual(row["pixel_displacement_dx"], 0)
        self.assertEqual(row["pixel_displacement_dy"], 0)

    def test_brightness_change(self):
        altered = np.clip(
            self.image.astype(float)*0.8+15,
            0, 255,
        ).astype(np.uint8)
        altered = np.roll(
            altered, (2, -4), axis=(0, 1)
        )
        row = estimate_pixel_motion(
            self.image, altered
        )
        self.assertEqual(
            (row["pixel_displacement_dy"],
             row["pixel_displacement_dx"]),
            (2, -4),
        )

    def test_blackout_fails_closed(self):
        row = estimate_pixel_motion(
            self.image,
            np.zeros_like(self.image),
        )
        self.assertEqual(row["status"], "UNAVAILABLE")
        self.assertIsNone(row["pixel_displacement_dx"])
        self.assertFalse(row["health_label_created"])

    def test_unrelated_images_unavailable(self):
        other = np.random.default_rng(
            999
        ).integers(
            0, 256, self.image.shape,
            dtype=np.uint8,
        )
        row = estimate_pixel_motion(
            self.image, other
        )
        self.assertEqual(row["status"], "UNAVAILABLE")

    def test_shape_mismatch_rejected(self):
        with self.assertRaises(VisualMotionError):
            estimate_pixel_motion(
                self.image,
                self.image[:100],
            )

    def test_non_uint8_rejected(self):
        with self.assertRaises(VisualMotionError):
            grayscale(self.image.astype(float))

    def test_invalid_channels_rejected(self):
        with self.assertRaises(VisualMotionError):
            grayscale(
                np.zeros((120, 160, 2), dtype=np.uint8)
            )

    def test_rgb_and_rgba_supported(self):
        rgb = np.repeat(
            self.image[:, :, None], 3, axis=2
        )
        rgba = np.concatenate(
            (
                rgb,
                np.full(
                    (120, 160, 1),
                    255,
                    dtype=np.uint8,
                ),
            ),
            axis=2,
        )
        row = estimate_pixel_motion(rgb, rgba)
        self.assertEqual(
            row["status"], "PIXEL_TRANSLATION_OBSERVED"
        )

    def test_metric_pose_conversion_blocked(self):
        row = estimate_pixel_motion(
            self.image, self.image
        )
        with self.assertRaises(VisualMotionError):
            require_metric_camera_factor(row)

    def test_deterministic_result(self):
        altered = np.roll(
            self.image, (1, 2), axis=(0, 1)
        )
        a = estimate_pixel_motion(
            self.image, altered
        )
        b = estimate_pixel_motion(
            self.image.copy(), altered.copy()
        )
        self.assertEqual(a, b)

    def test_complete_controlled_study(self):
        report = controlled_pixel_study()
        self.assertEqual(report["case_count"], 7)
        self.assertFalse(
            report["metric_camera_pose_factors_created"]
        )
        self.assertFalse(
            report["physical_sensor_evaluation_performed"]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
