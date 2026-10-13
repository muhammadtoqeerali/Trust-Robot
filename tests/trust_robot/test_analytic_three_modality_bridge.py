import unittest

from trust_robot.analytic_three_modality_bridge import (
    execute,
    execute_case,
)


class AnalyticThreeModalityBridgeTests(unittest.TestCase):

    def test_clean_three_modality_execution(self):
        row = execute_case("clean", 13)
        factors = row["relative_pose_factors"]

        self.assertEqual(row["estimated_node_count"], 5)
        self.assertEqual(row["inertial_factor_count"], 4)
        self.assertEqual(
            factors["synthetic_camera_factor_count"], 2
        )
        self.assertGreater(
            factors["synthetic_lidar_factor_count"], 0
        )
        self.assertTrue(row["factor_accounting_valid"])
        self.assertFalse(row["camera_pixels_processed"])

    def test_dropout_three_modality_execution(self):
        row = execute_case("lidar_dropout", 13)
        self.assertEqual(row["accepted_window_count"], 4)
        self.assertEqual(row["schur_elimination_count"], 3)
        self.assertFalse(
            row["independent_ground_truth_scored"]
        )

    def test_camera_disabled_control(self):
        row = execute_case(
            "clean", 13, camera_enabled=False
        )
        self.assertEqual(
            row["relative_pose_factors"][
                "synthetic_camera_factor_count"
            ], 0,
        )

    def test_seeded_repeat(self):
        first = execute_case("clean", 31)
        second = execute_case("clean", 31)
        self.assertEqual(first, second)

    def test_invalid_experiment_condition_rejected(self):
        with self.assertRaises(ValueError):
            execute_case("real_m2dgr", 13)

    def test_complete_synthetic_scope(self):
        report = execute()
        self.assertEqual(report["case_count"], 12)
        self.assertFalse(
            report["real_three_modality_localization_verified"]
        )
        self.assertFalse(
            report["physical_sensor_factor_execution_authorized"]
        )
        self.assertFalse(report["legacy_estimator_modified"])
        self.assertFalse(
            report["frozen_scientific_gates_changed"]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
