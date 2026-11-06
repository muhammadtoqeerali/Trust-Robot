import copy
import unittest

from trust_robot.synthetic_toy_sensitivity_v1 import (
    ToySensitivityError,
    evaluate_toy_sensitivity,
    infer_real_robot_sensitivity,
)


def experiment():
    return evaluate_toy_sensitivity(
        [11, 23],
        [0.0, 6.0],
        [9],
        [0.0],
    )


class ToySensitivityTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.result = experiment()

    def test_01_cell_count(self):
        self.assertEqual(
            self.result["grid_cell_count"], 6
        )

    def test_02_run_count(self):
        self.assertEqual(
            self.result["toy_trajectory_run_count"], 12
        )

    def test_03_three_distinct_profiles(self):
        self.assertEqual(
            self.result["toy_profile_count"], 3
        )

    def test_04_four_policies(self):
        self.assertTrue(all(
            len(cell["summary"]) == 4
            for cell in self.result["cells"]
        ))

    def test_05_continuous_updates(self):
        cells = [
            c for c in self.result["cells"]
            if c["synthetic_profile"]
            == "continuous_toy_delivery"
        ]
        self.assertTrue(all(
            c["summary"]["scheduled_delivery_only"][
                "mean_accepted_toy_updates"
            ] == 6
            for c in cells
        ))

    def test_06_dropout_updates(self):
        cells = [
            c for c in self.result["cells"]
            if c["synthetic_profile"]
            == "injected_toy_dropout_recovery"
        ]
        self.assertTrue(all(
            c["summary"]["scheduled_delivery_only"][
                "mean_accepted_toy_updates"
            ] == 4
            for c in cells
        ))

    def test_07_fully_withheld_updates(self):
        cells = [
            c for c in self.result["cells"]
            if c["synthetic_profile"]
            == "fully_withheld_toy_delivery"
        ]
        self.assertTrue(all(
            c["summary"]["combined_toy_screening"][
                "mean_accepted_toy_updates"
            ] == 0
            for c in cells
        ))

    def test_08_reproducibility(self):
        self.assertEqual(
            self.result,
            experiment(),
        )

    def test_09_reject_duplicate_seed(self):
        with self.assertRaises(ToySensitivityError):
            evaluate_toy_sensitivity(
                [11, 11], [6.0], [9], [0.0]
            )

    def test_10_reject_boolean_seed(self):
        with self.assertRaises(ToySensitivityError):
            evaluate_toy_sensitivity(
                [True, 23], [6.0], [9], [0.0]
            )

    def test_11_reject_negative_outlier(self):
        with self.assertRaises(ToySensitivityError):
            evaluate_toy_sensitivity(
                [11, 23], [-1.0], [9], [0.0]
            )

    def test_12_reject_negative_process_noise(self):
        with self.assertRaises(ToySensitivityError):
            evaluate_toy_sensitivity(
                [11, 23], [6.0], [9], [-0.01]
            )

    def test_13_reject_boolean_limit(self):
        with self.assertRaises(ToySensitivityError):
            evaluate_toy_sensitivity(
                [11, 23], [6.0], [True], [0.0]
            )

    def test_14_reject_nonfinite_noise(self):
        with self.assertRaises(ToySensitivityError):
            evaluate_toy_sensitivity(
                [11, 23], [6.0], [9], [float("nan")]
            )

    def test_15_no_physical_claim(self):
        self.assertFalse(
            self.result[
                "physical_localization_accuracy_verified"
            ]
        )
        self.assertFalse(
            self.result["statistical_calibration_established"]
        )
        self.assertEqual(
            self.result["real_factor_count"], 0
        )

    def test_16_real_sensitivity_denied(self):
        with self.assertRaises(ToySensitivityError):
            infer_real_robot_sensitivity()


if __name__ == "__main__":
    unittest.main()
