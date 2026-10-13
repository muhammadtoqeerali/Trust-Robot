import unittest

import numpy as np

from trust_robot.analytic_estimator_seeded_stress import (
    baseline_drift,
    condition_study,
    execute,
    get_problem,
    perturb_imu,
)


class SeededEstimatorStressTests(unittest.TestCase):

    def test_seeded_perturbations_repeat(self):
        fixture, _, _ = get_problem("five", "clean")
        a = perturb_imu(fixture, 17, 1.0)
        b = perturb_imu(fixture, 17, 1.0)

        self.assertEqual(a["imu"], b["imu"])
        self.assertEqual(
            fixture["imu"][0]["measurement_origin"],
            "ANALYTIC_FIXTURE",
        )
        self.assertNotEqual(
            fixture["imu"][0]["gyro_rad_s"],
            a["imu"][0]["gyro_rad_s"],
        )

    def test_invalid_input_rejected(self):
        fixture, _, _ = get_problem("five", "clean")
        for scale in (-1, float("nan"), float("inf"), 101):
            with self.subTest(scale=scale):
                with self.assertRaises(ValueError):
                    perturb_imu(fixture, 17, scale)

        with self.assertRaises(ValueError):
            get_problem("twelve", "unsupported")

    def test_actual_five_node_estimator_runs(self):
        row = condition_study(
            "five", "clean", seeds=(3, 17)
        )
        self.assertEqual(row["node_count"], 5)
        self.assertEqual(row["trial_count"], 4)
        self.assertFalse(
            row["baseline_is_independent_ground_truth"]
        )
        self.assertEqual(
            row["solved_count"] + row["unavailable_count"],
            4,
        )

    def test_actual_twelve_node_outage_runs(self):
        row = condition_study(
            "twelve", "lidar_outage", seeds=(3,)
        )
        self.assertEqual(row["node_count"], 12)
        self.assertEqual(row["trial_count"], 2)
        self.assertEqual(row["baseline_windows"], 11)

    def test_complete_scientific_boundaries(self):
        row = execute()
        self.assertEqual(len(row["scenarios"]), 4)
        self.assertEqual(
            sum(s["trial_count"] for s in row["scenarios"]),
            48,
        )
        self.assertFalse(row["real_sensor_data_used"])
        self.assertFalse(row["posterior_coverage_assessed"])
        self.assertFalse(row["physical_observability_verified"])
        self.assertFalse(row["trust_conditioning_executed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
