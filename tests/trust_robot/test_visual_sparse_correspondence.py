import unittest

import numpy as np

from trust_robot.visual_sparse_correspondence import (
    analyze_sparse_motion,
    controlled_sparse_study,
    detect_corners,
    match_patches,
    require_metric_visual_motion,
)
from trust_robot.visual_pixel_motion import (
    VisualMotionError,
)


class SparseCorrespondenceTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.image = np.random.default_rng(
            20261013
        ).integers(
            0, 256, (120, 160),
            dtype=np.uint8,
        )

    def test_spatial_features_present(self):
        features = detect_corners(self.image)
        self.assertGreaterEqual(len(features), 12)
        self.assertEqual(
            len({f["feature_index"] for f in features}),
            len(features),
        )

    def test_integer_translation_recovered(self):
        target = np.roll(
            self.image, (-3, 5), axis=(0, 1)
        )
        row = analyze_sparse_motion(
            self.image, target
        )
        self.assertEqual(
            row["status"],
            "TWO_D_AFFINE_CONSISTENCY_OBSERVED",
        )
        self.assertAlmostEqual(
            row["two_d_affine_geometry"]["median_dx_px"],
            5.0,
        )
        self.assertAlmostEqual(
            row["two_d_affine_geometry"]["median_dy_px"],
            -3.0,
        )

    def test_brightness_change(self):
        altered = np.clip(
            self.image.astype(float)*0.8+15,
            0, 255,
        ).astype(np.uint8)

        altered = np.roll(
            altered, (2, -4), axis=(0, 1)
        )

        row = analyze_sparse_motion(
            self.image, altered
        )
        self.assertEqual(
            row["status"],
            "TWO_D_AFFINE_CONSISTENCY_OBSERVED",
        )

    def test_foreground_outliers_preserve_dominant_motion(self):
        altered = np.roll(
            self.image, (4, -6), axis=(0, 1)
        )
        altered[35:75, 40:90] = np.roll(
            self.image[35:75, 40:90],
            (-5, 7), axis=(0, 1)
        )

        row = analyze_sparse_motion(
            self.image, altered
        )
        geometry = row["two_d_affine_geometry"]

        self.assertIsNotNone(geometry)
        self.assertGreater(geometry["inlier_ratio"], 0.60)
        self.assertAlmostEqual(
            geometry["median_dx_px"], -6.0
        )

    def test_stationary_image(self):
        row = analyze_sparse_motion(
            self.image, self.image
        )
        self.assertEqual(
            row["status"],
            "TWO_D_AFFINE_CONSISTENCY_OBSERVED",
        )
        self.assertAlmostEqual(
            row["two_d_affine_geometry"]["median_dx_px"], 0.0
        )

    def test_blackout_unavailable(self):
        row = analyze_sparse_motion(
            self.image, np.zeros_like(self.image)
        )
        self.assertEqual(row["status"], "UNAVAILABLE")
        self.assertIsNone(row["two_d_affine_geometry"])

    def test_unrelated_image_unavailable(self):
        other = np.random.default_rng(
            999
        ).integers(
            0, 256, self.image.shape,
            dtype=np.uint8,
        )
        row = analyze_sparse_motion(
            self.image, other
        )
        self.assertEqual(row["status"], "UNAVAILABLE")

    def test_textureless_corners_absent(self):
        blank = np.zeros_like(self.image)
        self.assertEqual(detect_corners(blank), [])

    def test_wrong_dtype_rejected(self):
        with self.assertRaises(VisualMotionError):
            analyze_sparse_motion(
                self.image.astype(float), self.image
            )

    def test_dimensions_must_match(self):
        with self.assertRaises(VisualMotionError):
            analyze_sparse_motion(
                self.image, self.image[:90]
            )

    def test_rgb_rgba_image_support(self):
        rgb = np.repeat(
            self.image[:, :, None], 3, axis=2
        )
        rgba = np.concatenate(
            (
                rgb,
                np.full(
                    (120, 160, 1),
                    255, dtype=np.uint8,
                ),
            ),
            axis=2,
        )
        row = analyze_sparse_motion(rgb, rgba)
        self.assertEqual(
            row["status"],
            "TWO_D_AFFINE_CONSISTENCY_OBSERVED",
        )

    def test_deterministic_correspondence(self):
        shifted = np.roll(
            self.image, (1, 2), axis=(0, 1)
        )
        a = analyze_sparse_motion(self.image, shifted)
        b = analyze_sparse_motion(
            self.image.copy(), shifted.copy()
        )
        self.assertEqual(a, b)

    def test_no_metric_pose_authorization(self):
        row = analyze_sparse_motion(
            self.image, self.image
        )
        with self.assertRaises(VisualMotionError):
            require_metric_visual_motion(row)
        self.assertFalse(
            row["camera_se3_pose_factor_created"]
        )

    def test_complete_controlled_study(self):
        report = controlled_sparse_study()
        self.assertEqual(report["case_count"], 8)
        self.assertFalse(
            report["physical_camera_pose_estimated"]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
