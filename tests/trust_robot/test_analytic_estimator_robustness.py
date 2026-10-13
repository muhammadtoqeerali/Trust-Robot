import unittest

import numpy as np

from trust_robot.analytic_inertial_15d import make_fixture
from trust_robot.analytic_marginalized_horizon import (
    NODE_FRAMES as LONG_FRAMES,
    long_fixture,
    long_factors,
)
from trust_robot.analytic_estimator_robustness import (
    corruption_trials,
    dropout_information_diagnostic,
    execute,
    full_batch_comparison,
    guarded_estimate,
    validate_fixture,
)


class EstimatorRobustnessTests(unittest.TestCase):

    def setUp(self):
        self.fixture, _ = make_fixture("clean")

    def test_valid_synthetic_fixture(self):
        result = validate_fixture(self.fixture)

        self.assertEqual(result["node_count"], 5)
        self.assertEqual(result["imu_sample_count"], 8)
        self.assertFalse(
            result["real_sensor_admission_authorized"]
        )

    def test_long_outage_is_explicit(self):
        fixture, _ = long_fixture("lidar_outage")

        result = validate_fixture(
            fixture,
            node_frames=LONG_FRAMES,
        )

        self.assertEqual(result["node_count"], 12)
        self.assertLess(
            result["available_lidar_nodes"], 12
        )

    def test_missing_lidar_without_any_pair_rejected(self):
        modified, _ = make_fixture("clean")

        modified["available"] = [
            False for _ in modified["available"]
        ]

        with self.assertRaises(ValueError):
            validate_fixture(modified)

    def test_invalid_imu_record_rejected(self):
        modified, _ = make_fixture("clean")

        modified["imu"][2]["interval_index"] = 1

        with self.assertRaises(ValueError):
            validate_fixture(modified)

    def test_nan_cloud_rejected(self):
        modified, _ = make_fixture("clean")
        modified["scans"][4][0, 0] = np.nan

        with self.assertRaises(ValueError):
            validate_fixture(modified)

    def test_guarded_five_node_solver(self):
        states, audit, admission = guarded_estimate(
            self.fixture
        )

        self.assertEqual(len(states), 5)
        self.assertEqual(
            audit["schur_elimination_count"], 3
        )
        self.assertEqual(
            admission["node_count"], 5
        )

    def test_corruption_rejection_matrix(self):
        result = corruption_trials()

        self.assertEqual(len(result), 9)
        self.assertTrue(all(
            value == "REJECTED_BEFORE_ESTIMATION"
            for value in result.values()
        ))

    def test_clean_nonlinear_fullbatch_comparison(self):
        comparison = full_batch_comparison("clean")

        self.assertTrue(
            comparison["full_batch_solver_converged"]
        )
        self.assertLess(
            comparison[
                "rolling_vs_fullbatch_final_translation_gap_m"
            ],
            1e-3,
        )
        self.assertFalse(
            comparison[
                "nonlinear_posterior_consistency_proven"
            ]
        )

    def test_lidar_information_removal_identity(self):
        result = dropout_information_diagnostic()

        self.assertTrue(
            result["linearized_information_conservation"]
        )
        self.assertGreater(
            len(result["missing_lidar_factor_keys"]), 0
        )
        self.assertFalse(
            result["covariance_is_empirically_calibrated"]
        )

    def test_full_robustness_report(self):
        report = execute()

        self.assertEqual(
            report["status"],
            "LOCAL_DEVELOPMENT_ROBUSTNESS_VALIDATED"
        )
        self.assertFalse(
            report["independent_ground_truth_used"]
        )
        self.assertFalse(
            report["nonlinear_posterior_consistency_proven"]
        )
        self.assertFalse(
            report["factor_conditioning_executed"]
        )


if __name__ == "__main__":
    unittest.main()
