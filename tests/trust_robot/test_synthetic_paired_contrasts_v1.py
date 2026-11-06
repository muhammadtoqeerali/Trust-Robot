import copy
import unittest

from trust_robot.synthetic_paired_contrasts_v1 import (
    PairedContrastError,
    audit_paired_ensemble,
    claim_physical_replication,
)

from trust_robot.synthetic_trajectory_ensemble_v1 import (
    evaluate_seeded_ensemble,
)


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


class PairedAuditTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.source = evaluate_seeded_ensemble(
            [11, 23],
            masks(),
        )

    def review(self):
        return audit_paired_ensemble(
            copy.deepcopy(self.source)
        )

    def test_01_five_labels(self):
        self.assertEqual(
            self.review()["scenario_label_count"], 5
        )

    def test_02_only_two_unique_conditions(self):
        self.assertEqual(
            self.review()["unique_mask_condition_count"], 2
        )

    def test_03_group_sizes(self):
        groups = self.review()[
            "synthetic_mask_condition_groups"
        ]
        self.assertEqual(
            sorted(g["scenario_label_count"] for g in groups),
            [2, 3],
        )

    def test_04_paired_seed_count(self):
        self.assertEqual(self.review()["seed_count"], 2)

    def test_05_comparison_types(self):
        contrasts = self.review()[
            "paired_scenario_contrasts"
        ]["lossless_reference"]["paired_contrasts"]
        self.assertEqual(len(contrasts), 2)

    def test_06_deterministic(self):
        self.assertEqual(self.review(), self.review())

    def test_07_reject_changed_aggregate(self):
        source = copy.deepcopy(self.source)
        source["scenarios"]["lossless_reference"][
            "summary"
        ]["combined_toy_screening"][
            "mean_toy_position_rmse"
        ] += 1.0

        with self.assertRaises(PairedContrastError):
            audit_paired_ensemble(source)

    def test_08_reject_mismatched_seed(self):
        source = copy.deepcopy(self.source)
        source["scenarios"]["lossless_reference"][
            "trials"
        ][0]["synthetic_seed"] = 999

        with self.assertRaises(PairedContrastError):
            audit_paired_ensemble(source)

    def test_09_reject_forged_factor(self):
        source = copy.deepcopy(self.source)
        source["real_factor_count"] = 1

        with self.assertRaises(PairedContrastError):
            audit_paired_ensemble(source)

    def test_10_reject_forged_clock(self):
        source = copy.deepcopy(self.source)
        source["physical_clock_verified"] = True

        with self.assertRaises(PairedContrastError):
            audit_paired_ensemble(source)

    def test_11_reject_mask_accounting(self):
        source = copy.deepcopy(self.source)
        source["scenarios"]["lossless_reference"][
            "synthetic_delivery_mask"
        ] = [False] * 6

        with self.assertRaises(PairedContrastError):
            audit_paired_ensemble(source)

    def test_12_reject_duplicate_replicate_divergence(self):
        source = copy.deepcopy(self.source)
        trial = source["scenarios"][
            "synthetic_lidar_suppression"
        ]["trials"][0]["policies"][
            "combined_toy_screening"
        ]
        trial["toy_position_rmse"] += 0.5

        source["scenarios"][
            "synthetic_lidar_suppression"
        ]["summary"]["combined_toy_screening"][
            "mean_toy_position_rmse"
        ] += 0.25

        with self.assertRaises(PairedContrastError):
            audit_paired_ensemble(source)

    def test_13_no_physical_replicates(self):
        result = self.review()
        self.assertEqual(
            result["independent_physical_trials"], 0
        )
        self.assertEqual(
            result["real_factor_admission"], "DENIED"
        )

    def test_14_no_physical_replication_claim(self):
        with self.assertRaises(PairedContrastError):
            claim_physical_replication()


if __name__ == "__main__":
    unittest.main()
