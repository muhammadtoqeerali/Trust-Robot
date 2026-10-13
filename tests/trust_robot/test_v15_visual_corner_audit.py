import unittest

import numpy as np

from trust_robot.v15_visual_corner_audit import (
    audit_image_corners,
)
from trust_robot.visual_pixel_motion import VisualMotionError


class V15CornerAuditTests(unittest.TestCase):

    def test_dark_image_has_no_features(self):
        image = np.zeros((120, 160, 4), dtype=np.uint8)
        image[:, :, 3] = 255

        result = audit_image_corners(image)

        self.assertEqual(result["original_corner_count"], 0)
        self.assertEqual(result["global_intensity_std"], 0)

    def test_textured_image_has_features(self):
        image = np.random.default_rng(
            13
        ).integers(
            0, 256, size=(120, 160),
            dtype=np.uint8,
        )

        result = audit_image_corners(image)

        self.assertGreater(
            result["original_corner_count"], 10
        )
        self.assertFalse(
            result["original_detector_thresholds_changed"]
        )

    def test_wrong_dtype_rejected(self):
        with self.assertRaises(VisualMotionError):
            audit_image_corners(
                np.zeros(
                    (120, 160), dtype=np.float32
                )
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
