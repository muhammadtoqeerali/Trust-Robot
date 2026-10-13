import inspect
import math
import unittest

import numpy as np

from trust_robot.analytic_inertial_15d import (
    CONDITIONS,
    N,
    DT,
    analytic_truth,
    initial_state,
    make_fixture,
    predict_imu,
    imu_residual,
    lidar_residual,
    build_lidar_factors,
    estimate,
    score,
    canonical,
)
from trust_robot.clean_backbone import PoseSE3


class Inertial15DTests(unittest.TestCase):
    def test_full_state_has_fifteen_components(self):
        x = initial_state()
        self.assertEqual(x.shape, (15,))
        self.assertEqual(
            np.linalg.norm(x[9:15]), 0.0
        )

    def test_synthetic_trajectory_nontrivial(self):
        a = analytic_truth(0)
        b = analytic_truth(N - 1)
        self.assertGreater(
            np.linalg.norm(b[:3] - a[:3]), 0.1
        )
        self.assertGreater(
            np.linalg.norm(b[3:6] - a[3:6]), 0.01
        )

    def test_discrete_inertial_propagation(self):
        fixture, truth = make_fixture("clean")

        for k in range(N - 1):
            predicted = predict_imu(
                truth[k], fixture["imu"][k]
            )
            self.assertLess(
                np.linalg.norm(
                    predicted - truth[k+1]
                ),
                1e-10,
            )

    def test_imu_factor_zero_for_truth(self):
        fixture, truth = make_fixture("clean")
        error = imu_residual(
            truth[2], truth[3], fixture["imu"][2]
        )
        self.assertEqual(error.shape, (15,))
        self.assertLess(
            np.linalg.norm(error), 1e-9
        )

    def test_corrupted_accel_measurement_is_distinct(self):
        clean, _ = make_fixture("clean")
        altered, _ = make_fixture("accel_bias")
        self.assertNotEqual(
            clean["imu"][4]["specific_force_m_s2"],
            altered["imu"][4]["specific_force_m_s2"],
        )
        self.assertEqual(
            clean["imu"][0]["specific_force_m_s2"],
            altered["imu"][0]["specific_force_m_s2"],
        )

    def test_lidar_dropout_provenance(self):
        fixture, _ = make_fixture("lidar_dropout")
        self.assertFalse(fixture["available"][4])
        self.assertEqual(
            sum(fixture["available"]), N - 1
        )

    def test_lidar_factor_zero_at_consistent_poses(self):
        pose = PoseSE3.identity()
        error = lidar_residual(
            initial_state(),
            initial_state(),
            pose,
        )
        self.assertEqual(error.shape, (6,))
        self.assertLess(np.linalg.norm(error), 1e-12)

    def test_estimator_does_not_receive_truth(self):
        self.assertEqual(
            list(inspect.signature(estimate).parameters),
            ["fixture"],
        )
        fixture, _ = make_fixture("clean")
        self.assertNotIn("truth", fixture)

    def test_nominal_short_window_integration(self):
        fixture, truth = make_fixture("clean")
        estimates, solver = estimate(fixture)

        self.assertEqual(len(estimates), N)
        self.assertEqual(
            solver["accepted_window_count"], N - 1
        )
        self.assertTrue(all(
            r["state_dimension"] == 15
            for r in estimates
        ))
        self.assertTrue(all(
            r["reference_pose"] is None
            for r in estimates
        ))

        metrics = score(estimates, truth)
        self.assertLess(
            metrics["fixture_position_rmse_m"],
            1e-4,
        )

    def test_nonfinite_json_rejected(self):
        with self.assertRaises(ValueError):
            canonical({"value": float("nan")})


if __name__ == "__main__":
    unittest.main()
