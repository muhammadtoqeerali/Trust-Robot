import unittest
import numpy as np

from trust_robot.analytic_marginalization_consistency import (
    nonlinear_case,
    gaussian_consistency,
    relative,
    truth,
    execute,
)
from trust_robot.analytic_schur_marginalization import (
    marginalize_one,
)


class MarginalizationConsistencyTests(unittest.TestCase):

    def test_affine_schur_control_is_exact(self):
        result = nonlinear_case("affine", 11, directions=4)
        self.assertLess(
            result["far_mean_absolute_profile_cost_error"],
            1e-5,
        )
        self.assertEqual(result["local_support_rank"], 30)

    def test_nonlinear_relinearization_sensitivity(self):
        result = nonlinear_case("se3", 29, directions=6)
        self.assertGreater(
            result["far_mean_absolute_profile_cost_error"],
            4*result["near_mean_absolute_profile_cost_error"],
        )
        self.assertTrue(result["schur_elimination_completed"])

    def test_nonlinear_study_deterministic(self):
        a = nonlinear_case("se3", 47, directions=3)
        b = nonlinear_case("se3", 47, directions=3)
        self.assertEqual(a, b)

    def test_relative_motion_is_non_affine(self):
        a, b = truth(1), truth(2)
        self.assertGreater(
            np.linalg.norm(
                relative(a, b, "se3")
                - relative(a, b, "affine")
            ),
            1e-4,
        )

    def test_singular_elimination_pivot_rejected(self):
        ref = {
            0: np.zeros(15),
            1: np.zeros(15),
        }
        with self.assertRaisesRegex(ValueError, "singular"):
            marginalize_one(
                (0, 1),
                ref,
                lambda states: states[1][:3],
                0,
            )

    def test_known_noise_nees_and_coverage(self):
        row = gaussian_consistency()
        clean = row["noise_assumption_matched"]
        self.assertGreater(clean["mean_nees"], 12)
        self.assertLess(clean["mean_nees"], 18)
        self.assertGreater(clean["nees_95pct_coverage"], .90)
        self.assertFalse(
            row["empirical_sensor_covariance_calibrated"]
        )

    def test_mismatched_noise_inflates_nees(self):
        row = gaussian_consistency()
        a = row["noise_assumption_matched"]
        b = row["noise_assumption_mismatched"]
        self.assertGreater(b["mean_nees"], 3*a["mean_nees"])
        self.assertLess(
            b["nees_95pct_coverage"],
            a["nees_95pct_coverage"],
        )
        self.assertGreater(
            b["mean_residual_chi_square"],
            3*a["mean_residual_chi_square"],
        )

    def test_invalid_study_inputs_rejected(self):
        with self.assertRaises(ValueError):
            nonlinear_case("unknown", 11)
        with self.assertRaises(ValueError):
            gaussian_consistency(10)
        with self.assertRaises(ValueError):
            relative(truth(0), np.zeros(14), "se3")

    def test_complete_study_scientific_limits(self):
        result = execute()
        self.assertEqual(
            result["status"], "MANUFACTURED_MATH_STUDY_PASSED"
        )
        self.assertFalse(result["physical_observability_verified"])
        self.assertFalse(result["real_sensor_noise_calibrated"])
        self.assertFalse(
            result["estimator_posterior_coverage_validated"]
        )
        self.assertFalse(result["physical_robot_used"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
