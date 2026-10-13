import inspect
import math
import unittest

import numpy as np

from trust_robot.analytic_inertial_15d import (
    make_fixture,
)
from trust_robot.analytic_preintegrated_fusion import (
    CONDITIONS,
    NODE_FRAMES,
    canonical,
    estimate_preintegrated,
    execute,
    factor_whitener,
    make_factors,
    whitened_inertial_residual,
)
from trust_robot.analytic_imu_preintegration import (
    preintegrate,
)


class PreintegratedFusionTests(unittest.TestCase):

    def setUp(self):
        self.fixture, self.truth = make_fixture("clean")

    def test_nonoverlapping_imu_intervals(self):
        inertial, _, provenance = make_factors(
            self.fixture
        )

        self.assertEqual(len(inertial), 4)
        self.assertEqual(
            provenance["unique_imu_sample_count"], 8
        )
        self.assertFalse(
            provenance["imu_samples_reused"]
        )

        self.assertEqual(
            sorted(inertial),
            [(0, 1), (1, 2), (2, 3), (3, 4)],
        )

    def test_full_covariance_whitener(self):
        pre = preintegrate(
            self.fixture["imu"][:2]
        )
        lower = factor_whitener(pre)

        self.assertEqual(lower.shape, (15, 15))

        reconstructed = lower @ lower.T
        expected = (
            pre["covariance"]
            + 1e-8 * np.eye(15)
        )

        np.testing.assert_allclose(
            reconstructed,
            expected,
            atol=1e-12,
        )

        cross_block = pre["covariance"][:9, 9:15]

        self.assertGreater(
            np.linalg.norm(cross_block), 0
        )

    def test_indefinite_covariance_rejected(self):
        pre = preintegrate(
            self.fixture["imu"][:2]
        )
        corrupt = dict(pre)
        corrupt["covariance"] = -np.eye(15)

        with self.assertRaises(ValueError):
            factor_whitener(corrupt)

    def test_clean_truth_factor_closure(self):
        inertial, _, _ = make_factors(
            self.fixture
        )

        error = whitened_inertial_residual(
            self.truth[0],
            self.truth[2],
            inertial[0, 1],
        )

        self.assertEqual(error.shape, (15,))
        self.assertLess(np.linalg.norm(error), 1e-7)

    def test_bias_intervention_changes_residual(self):
        changed, truth = make_fixture("accel_bias")

        clean_factors, _, _ = make_factors(
            self.fixture
        )
        changed_factors, _, _ = make_factors(
            changed
        )

        clean_residual = whitened_inertial_residual(
            truth[2],
            truth[4],
            clean_factors[1, 2],
        )

        biased_residual = whitened_inertial_residual(
            truth[2],
            truth[4],
            changed_factors[1, 2],
        )

        self.assertGreater(
            np.linalg.norm(biased_residual),
            np.linalg.norm(clean_residual) + 0.1,
        )

    def test_lidar_dropout_removes_factors(self):
        dropout, _ = make_fixture("lidar_dropout")

        _, clean_lidar, _ = make_factors(
            self.fixture
        )

        _, altered_lidar, _ = make_factors(
            dropout
        )

        self.assertEqual(len(clean_lidar), 7)
        self.assertEqual(len(altered_lidar), 3)

    def test_reference_not_estimator_argument(self):
        self.assertEqual(
            list(
                inspect.signature(
                    estimate_preintegrated
                ).parameters
            ),
            ["fixture"],
        )

        self.assertNotIn("truth", self.fixture)

    def test_invalid_state_shape(self):
        factors, _, _ = make_factors(
            self.fixture
        )

        with self.assertRaises(ValueError):
            whitened_inertial_residual(
                np.zeros(14),
                np.zeros(15),
                factors[0, 1],
            )

    def test_clean_rolling_integration(self):
        states, solver = estimate_preintegrated(
            self.fixture
        )

        self.assertEqual(len(states), 5)
        self.assertEqual(
            solver["accepted_window_count"], 4
        )

        self.assertTrue(all(
            row["state_dimension"] == 15
            and row["reference_pose"] is None
            for row in states
        ))

    def test_full_three_condition_experiment(self):
        _, manifest = execute()

        self.assertEqual(
            manifest["conditions"],
            list(CONDITIONS),
        )

        self.assertEqual(
            manifest["node_frames"],
            list(NODE_FRAMES),
        )

        self.assertTrue(
            manifest["covariance_aware_preintegration_integrated"]
        )

        self.assertFalse(
            manifest["full_trust_robot_estimator_complete"]
        )

    def test_nonfinite_json_rejected(self):
        with self.assertRaises(ValueError):
            canonical({"value": float("nan")})


if __name__ == "__main__":
    unittest.main()
