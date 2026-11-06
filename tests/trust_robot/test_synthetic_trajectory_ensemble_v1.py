import copy
import unittest

from trust_robot.synthetic_trajectory_ensemble_v1 import (
    SyntheticEnsembleError,
    build_seeded_trial,
    evaluate_seeded_ensemble,
    evaluate_real_robot_ensemble,
)


SEEDS = [11, 23]

NORMAL = [True, True, False, False, True, True]
MISSING = [False] * 6


def masks():
    return {
        "lossless_reference": list(NORMAL),
        "synthetic_lidar_suppression": list(NORMAL),
        "synthetic_stereo_image_suppression": list(NORMAL),
        "synthetic_imu_suppression": list(MISSING),
        "synthetic_queue_pressure": list(MISSING),
    }


class EnsembleTests(unittest.TestCase):

    def test_01_seeded_trial_length(self):
        self.assertEqual(
            len(build_seeded_trial(11, NORMAL)), 6
        )

    def test_02_seed_determinism(self):
        self.assertEqual(
            build_seeded_trial(11, NORMAL),
            build_seeded_trial(11, list(NORMAL)),
        )

    def test_03_seed_variation(self):
        self.assertNotEqual(
            build_seeded_trial(11, NORMAL),
            build_seeded_trial(23, NORMAL),
        )

    def test_04_all_five_scenarios(self):
        result = evaluate_seeded_ensemble(
            SEEDS, masks()
        )
        self.assertEqual(result["scenario_count"], 5)

    def test_05_four_policies(self):
        result = evaluate_seeded_ensemble(
            SEEDS, masks()
        )
        self.assertEqual(
            len(result["scenarios"]["lossless_reference"][
                "summary"
            ]),
            4,
        )

    def test_06_delivery_accounting(self):
        result = evaluate_seeded_ensemble(
            SEEDS, masks()
        )

        summary = result["scenarios"][
            "lossless_reference"
        ]["summary"]

        self.assertEqual(
            summary["scheduled_delivery_only"][
                "mean_synthetic_updates"
            ],
            4,
        )

    def test_07_suppressed_delivery_zero(self):
        result = evaluate_seeded_ensemble(
            SEEDS, masks()
        )

        summary = result["scenarios"][
            "synthetic_imu_suppression"
        ]["summary"]

        self.assertEqual(
            summary["combined_toy_screening"][
                "mean_synthetic_updates"
            ],
            0,
        )

    def test_08_counterfactual_six(self):
        result = evaluate_seeded_ensemble(
            SEEDS, masks()
        )

        summary = result["scenarios"][
            "synthetic_queue_pressure"
        ]["summary"]

        self.assertEqual(
            summary["counterfactual_all_candidates"][
                "mean_synthetic_updates"
            ],
            6,
        )

    def test_09_reproducibility(self):
        self.assertEqual(
            evaluate_seeded_ensemble(SEEDS, masks()),
            evaluate_seeded_ensemble(
                copy.deepcopy(SEEDS),
                copy.deepcopy(masks()),
            ),
        )

    def test_10_reject_duplicate_seeds(self):
        with self.assertRaises(SyntheticEnsembleError):
            evaluate_seeded_ensemble(
                [11, 11], masks()
            )

    def test_11_reject_boolean_seed(self):
        with self.assertRaises(SyntheticEnsembleError):
            evaluate_seeded_ensemble(
                [True, 23], masks()
            )

    def test_12_reject_missing_scenario(self):
        value = masks()
        del value["lossless_reference"]

        with self.assertRaises(SyntheticEnsembleError):
            evaluate_seeded_ensemble(SEEDS, value)

    def test_13_reject_bad_mask(self):
        value = masks()
        value["lossless_reference"][0] = 1

        with self.assertRaises(SyntheticEnsembleError):
            evaluate_seeded_ensemble(SEEDS, value)

    def test_14_reject_invalid_nis(self):
        with self.assertRaises(SyntheticEnsembleError):
            evaluate_seeded_ensemble(
                SEEDS,
                masks(),
                nis_limit_den=0,
            )

    def test_15_no_statistical_calibration(self):
        result = evaluate_seeded_ensemble(
            SEEDS, masks()
        )
        self.assertFalse(
            result["statistical_calibration_established"]
        )
        self.assertFalse(
            result["physical_reference_verified"]
        )

    def test_16_no_physical_factors(self):
        result = evaluate_seeded_ensemble(
            SEEDS, masks()
        )
        self.assertEqual(result["real_factor_count"], 0)
        self.assertEqual(
            result["real_factor_admission"],
            "DENIED",
        )

    def test_17_real_evaluation_denied(self):
        with self.assertRaises(SyntheticEnsembleError):
            evaluate_real_robot_ensemble()


if __name__ == "__main__":
    unittest.main()
