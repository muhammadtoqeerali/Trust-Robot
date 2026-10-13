import unittest

import numpy as np
from scipy.spatial.transform import Rotation

from trust_robot.visual_two_view_geometry import (
    TwoViewGeometryError,
    estimate_two_view,
    manufacture_case,
    controlled_study,
    require_real_camera_pose_factor,
)


def fit(**kwargs):
    row = manufacture_case(**kwargs)
    return estimate_two_view(
        row["source"], row["target"], row["K"]
    )


class TwoViewGeometryTests(unittest.TestCase):

    def test_known_geometry_recovers_direction(self):
        fixture = manufacture_case()
        output = fit()
        self.assertEqual(
            output["status"],
            "MANUFACTURED_TWO_VIEW_DIRECTION_RECOVERED",
        )
        self.assertGreaterEqual(
            output["inlier_count"], 80
        )

        R = np.array(
            output["geometry"]["rotation_matrix"]
        )
        t = np.array(
            output["geometry"]["translation_direction_unit"]
        )

        error = Rotation.from_matrix(
            R@fixture["R_truth"].T
        ).magnitude()

        self.assertLess(error, np.deg2rad(1))
        self.assertGreater(
            t@(
                fixture["t_truth"]
                / np.linalg.norm(fixture["t_truth"])
            ),
            0.98,
        )

    def test_25pct_outliers(self):
        result = fit(outlier_fraction=0.25)
        self.assertEqual(
            result["status"],
            "MANUFACTURED_TWO_VIEW_DIRECTION_RECOVERED",
        )
        self.assertGreaterEqual(result["inlier_count"], 60)

    def test_35pct_outliers(self):
        result = fit(outlier_fraction=0.35)
        self.assertEqual(
            result["status"],
            "MANUFACTURED_TWO_VIEW_DIRECTION_RECOVERED",
        )
        self.assertGreaterEqual(result["inlier_count"], 55)

    def test_pure_rotation_unavailable(self):
        result = fit(pure_rotation=True)
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertFalse(
            result["metric_translation_estimated"]
        )

    def test_unrelated_correspondence_unavailable(self):
        row = manufacture_case()
        unrelated = np.random.default_rng(
            993
        ).uniform(
            [10, 10], [150, 110],
            row["target"].shape,
        )
        result = estimate_two_view(
            row["source"], unrelated, row["K"]
        )
        self.assertEqual(result["status"], "UNAVAILABLE")

    def test_repeat_deterministic(self):
        self.assertEqual(
            fit(outlier_fraction=0.25),
            fit(outlier_fraction=0.25),
        )

    def test_metric_scene_scale_ambiguous(self):
        a = manufacture_case(scene_scale=1)
        b = manufacture_case(scene_scale=2)

        np.testing.assert_allclose(
            a["source"], b["source"], atol=1e-10
        )
        np.testing.assert_allclose(
            a["target"], b["target"], atol=1e-10
        )

    def test_real_provenance_rejected(self):
        row = manufacture_case()
        with self.assertRaises(TwoViewGeometryError):
            estimate_two_view(
                row["source"], row["target"], row["K"],
                intrinsics_provenance="M2DGR",
            )

    def test_singular_intrinsics_rejected(self):
        row = manufacture_case()
        K = row["K"].copy()
        K[0, 0] = 0
        with self.assertRaises(TwoViewGeometryError):
            estimate_two_view(
                row["source"], row["target"], K
            )

    def test_nonfinite_coordinates_rejected(self):
        row = manufacture_case()
        x = row["source"].copy()
        x[0, 0] = np.nan
        with self.assertRaises(TwoViewGeometryError):
            estimate_two_view(
                x, row["target"], row["K"]
            )

    def test_insufficient_correspondences_unavailable(self):
        row = manufacture_case()
        result = estimate_two_view(
            row["source"][:10],
            row["target"][:10],
            row["K"],
        )
        self.assertEqual(
            result["reason"], "TOO_FEW_CORRESPONDENCES"
        )

    def test_essential_matrix_has_correct_singular_values(self):
        output = fit()
        E = np.asarray(output["essential_matrix"])
        s = np.linalg.svd(E, compute_uv=False)
        self.assertLess(s[2], 1e-10)
        self.assertAlmostEqual(s[0], s[1], places=9)

    def test_no_physical_factor_permission(self):
        with self.assertRaises(TwoViewGeometryError):
            require_real_camera_pose_factor()
        self.assertFalse(fit()[
            "physical_pose_factor_created"
        ])

    def test_complete_manufactured_study(self):
        study = controlled_study()
        self.assertEqual(study["case_count"], 4)
        self.assertTrue(
            study["projective_scene_scale_ambiguity_demonstrated"]
        )
        self.assertFalse(
            study["real_camera_intrinsics_verified"]
        )
        self.assertFalse(
            study["physical_camera_pose_factors_authorized"]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
