import unittest

import numpy as np

from trust_robot.visual_homography_robustness import (
    HomographyAuditError,
    characterize_homography,
    manufacture_pairs,
    summarize_v15_corner_failure,
    controlled_study,
)
from trust_robot.visual_sparse_correspondence import (
    match_patches,
)


def study(kind, fraction=0.0):
    a, b = manufacture_pairs(
        kind, outlier_fraction=float(fraction)
    )
    return characterize_homography(
        a, b,
        provenance="MANUFACTURED_3D_PROJECTIONS",
    )


class VisualHomographyRobustnessTests(unittest.TestCase):

    def test_general_three_d_not_dominated_by_homography(self):
        row = study("general_3d")
        self.assertEqual(row["status"], "UNAVAILABLE")
        self.assertFalse(row["scene_planarity_proven"])

    def test_planar_scene_has_homography_support(self):
        row = study("planar")
        self.assertEqual(
            row["status"],
            "TWO_D_HOMOGRAPHY_SUPPORT_OBSERVED",
        )
        self.assertGreaterEqual(row["inlier_count"], 85)

    def test_planar_scene_with_30_percent_outliers(self):
        row = study("planar", 0.3)
        self.assertEqual(
            row["status"],
            "TWO_D_HOMOGRAPHY_SUPPORT_OBSERVED",
        )
        self.assertGreaterEqual(row["inlier_count"], 60)

    def test_pure_rotation_has_two_d_support_only(self):
        row = study("pure_rotation")
        self.assertEqual(
            row["status"],
            "TWO_D_HOMOGRAPHY_SUPPORT_OBSERVED",
        )
        self.assertFalse(row["supports_3d_pose_inference"])
        self.assertFalse(row["metric_pose_factor_created"])

    def test_unrelated_points_are_not_admitted(self):
        row = study("unrelated")
        self.assertEqual(row["status"], "UNAVAILABLE")

    def test_actual_image_pixel_correspondences(self):
        image = np.random.default_rng(
            20261013
        ).integers(
            0, 256, (120, 160), dtype=np.uint8
        )

        moved = np.roll(
            image, (2, -3), axis=(0, 1)
        )

        features, matches = match_patches(
            image, moved
        )

        self.assertGreaterEqual(len(matches), 36)

        source = [
            item["source_xy_px"] for item in matches
        ]
        target = [
            item["target_xy_px"] for item in matches
        ]

        row = characterize_homography(
            source, target,
            provenance="CONTROLLED_IMAGE_PIXELS",
        )

        self.assertEqual(
            row["status"],
            "TWO_D_HOMOGRAPHY_SUPPORT_OBSERVED",
        )
        self.assertFalse(row["metric_pose_factor_created"])

    def test_repeat_is_deterministic(self):
        self.assertEqual(
            study("planar", 0.3),
            study("planar", 0.3),
        )

    def test_unqualified_provenance_rejected(self):
        a, b = manufacture_pairs("planar")
        with self.assertRaises(HomographyAuditError):
            characterize_homography(
                a, b, provenance="M2DGR"
            )

    def test_nonfinite_coordinates_rejected(self):
        a, b = manufacture_pairs("planar")
        a[0, 0] = float("nan")

        with self.assertRaises(HomographyAuditError):
            characterize_homography(
                a, b,
                provenance="MANUFACTURED_3D_PROJECTIONS",
            )

    def test_insufficient_correspondences_closed(self):
        a, b = manufacture_pairs("planar")

        row = characterize_homography(
            a[:10], b[:10],
            provenance="MANUFACTURED_3D_PROJECTIONS",
        )

        self.assertEqual(
            row["reason"], "TOO_FEW_CORRESPONDENCES"
        )

    def test_v15_summary_rejects_inconsistent_evidence(self):
        rows = [
            {
                "original_harris_cutoff": 2000.0,
                "eligible_region_max_harris_response": 0.05,
                "original_corner_count": 0,
                "original_detector_thresholds_changed": False,
            }
            for _ in range(6)
        ]

        evidence = {
            "status": "EXISTING_V15_CORNER_FAILURE_CHARACTERIZED",
            "camera_frames_hash_verified": 6,
            "adjacent_pairs": 5,
            "accepted_sparse_pairs": 0,
            "original_detection_thresholds_changed": False,
            "per_frame_corner_diagnostics": rows,
        }

        summary = summarize_v15_corner_failure(evidence)

        self.assertEqual(
            summary["frames_with_no_eligible_corners"], 6
        )
        self.assertFalse(
            summary["detector_thresholds_changed"]
        )

        evidence["accepted_sparse_pairs"] = 1

        with self.assertRaises(HomographyAuditError):
            summarize_v15_corner_failure(evidence)

    def test_complete_manufactured_study(self):
        report = controlled_study()

        self.assertEqual(len(report["cases"]), 5)
        self.assertFalse(report["scene_planarity_proven"])
        self.assertFalse(
            report["metric_pose_factors_created"]
        )
        self.assertFalse(
            report["real_sensor_streams_processed"]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
