import unittest

import numpy as np

from trust_robot.analytic_inertial_15d import make_fixture
from trust_robot.analytic_marginalized_fusion import (
    estimate_marginalized,
)
from trust_robot.analytic_marginalized_horizon import (
    CONDITIONS,
    NODE_FRAMES,
    linear_fullbatch_equivalence,
    long_fixture,
    long_factors,
    execute,
)


class LongHorizonTests(unittest.TestCase):

    def test_fullbatch_schur_information_preserved(self):
        result = linear_fullbatch_equivalence()

        self.assertTrue(
            result["exact_linear_fullbatch_equivalence"]
        )
        self.assertLess(
            result["information_max_abs_error"],
            1e-5,
        )
        self.assertLess(
            result["gradient_max_abs_error"],
            1e-5,
        )

    def test_twelve_node_chronology(self):
        self.assertEqual(len(NODE_FRAMES), 12)
        self.assertEqual(
            NODE_FRAMES,
            tuple(range(0, 24, 2)),
        )

    def test_clean_fixture_has_complete_imu_stream(self):
        fixture, truth = long_fixture("clean")

        self.assertEqual(
            len(fixture["imu"]),
            NODE_FRAMES[-1],
        )
        self.assertEqual(len(truth), 12)

        self.assertTrue(all(
            row["physical_clock_verified"] is False
            for row in fixture["imu"]
        ))

    def test_bias_interventions_are_separate(self):
        clean, _ = long_fixture("clean")
        accel, _ = long_fixture("accel_bias")
        gyro, _ = long_fixture("gyro_bias")

        self.assertNotEqual(
            clean["imu"][8]["specific_force_m_s2"],
            accel["imu"][8]["specific_force_m_s2"],
        )
        self.assertNotEqual(
            clean["imu"][10]["gyro_rad_s"],
            gyro["imu"][10]["gyro_rad_s"],
        )

    def test_multi_frame_lidar_outage(self):
        clean, _ = long_fixture("clean")
        outage, _ = long_fixture("lidar_outage")

        self.assertEqual(
            sum(clean["available"]),
            len(clean["available"]),
        )
        self.assertEqual(
            sum(outage["available"]),
            len(outage["available"])-4,
        )

    def test_no_imu_double_counting(self):
        fixture, _ = long_fixture("clean")
        inertial, _, counts = long_factors(fixture)

        self.assertEqual(len(inertial), 11)
        self.assertEqual(
            counts["unique_imu_sample_count"],
            22,
        )
        self.assertFalse(
            counts["imu_samples_reused"]
        )

    def test_missing_imu_sample_fails_closed(self):
        fixture, _ = long_fixture("clean")
        fixture["imu"][4]["interval_index"] = 3

        with self.assertRaises(ValueError):
            long_factors(fixture)

    def test_original_five_node_estimator_remains_valid(self):
        fixture, _ = make_fixture("clean")
        records, audit = estimate_marginalized(fixture)

        self.assertEqual(len(records), 5)
        self.assertEqual(
            audit["schur_elimination_count"], 3
        )

    def test_longer_horizon_factor_conservation(self):
        fixture, _ = long_fixture("clean")

        records, audit = estimate_marginalized(
            fixture,
            node_frames=NODE_FRAMES,
            factor_factory=long_factors,
        )

        self.assertEqual(len(records), 12)
        self.assertEqual(
            audit["accepted_window_count"], 11
        )
        self.assertEqual(
            audit["schur_elimination_count"], 10
        )
        self.assertEqual(
            audit["unaccounted_factor_count"], 0
        )

    def test_full_conditions_and_scientific_limits(self):
        _, manifest = execute()

        self.assertEqual(
            manifest["condition_names"],
            list(CONDITIONS),
        )
        self.assertFalse(
            manifest["reference_passed_to_estimator"]
        )
        self.assertFalse(
            manifest["physical_observability_proven"]
        )
        self.assertFalse(
            manifest["health_model_trained"]
        )


if __name__ == "__main__":
    unittest.main()
