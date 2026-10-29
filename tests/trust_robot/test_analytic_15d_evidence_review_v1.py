import ast
import inspect
import math
import unittest
from pathlib import Path

from trust_robot.analytic_15d_evidence_review_v1 import (
    SCHEMA,
    STATUS,
    BLOCKED_CAPABILITIES,
    EvidenceReviewError,
    run_review,
    evidence_digest,
)

from trust_robot.analytic_15d_combined_imu_faults_v1 import (
    run_case as published_combined_case,
)

from trust_robot.multimodal_health_model import (
    HealthModelInterfaceError,
    assert_training_authorized,
    assert_inference_authorized,
)

from trust_robot.factor_conditioning import (
    FactorConditioningContractError,
    assert_factor_scale_execution_authorized,
)

ROOT = Path(__file__).resolve().parents[2]


class EvidenceReviewRegressionTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.review = run_review()

    def test_01_schema(self):
        self.assertEqual(self.review["schema"], SCHEMA)
        self.assertEqual(self.review["status"], STATUS)

    def test_02_four_studies(self):
        self.assertEqual(
            set(self.review["studies"]),
            {"A17", "A18", "A19", "A20"},
        )

    def test_03_419_study_configurations(self):
        self.assertEqual(
            self.review["total_study_configurations"],
            419,
        )

    def test_04_study_inventory(self):
        expected = {
            "A17": 128,
            "A18": 256,
            "A19": 15,
            "A20": 20,
        }

        for name, count in expected.items():
            self.assertEqual(
                self.review["studies"][name][
                    "configuration_count"
                ],
                count,
            )

    def test_05_accounted_solver_outcomes(self):
        for row in self.review["studies"].values():
            self.assertEqual(
                row["accepted_count"]
                + row["numerically_rejected_count"],
                row["configuration_count"],
            )

    def test_06_five_node_parity(self):
        self.assertEqual(
            self.review["five_node_clean_parity_cases"],
            128,
        )

    def test_07_twelve_node_parity(self):
        self.assertEqual(
            self.review[
                "twelve_node_published_parity_cases"
            ],
            15,
        )

    def test_08_a17_support_gap(self):
        self.assertEqual(
            self.review[
                "a17_accepted_with_missing_current_lidar"
            ],
            78,
        )

    def test_09_a18_support_gap(self):
        self.assertEqual(
            self.review[
                "a18_accepted_with_missing_current_lidar"
            ],
            156,
        )

    def test_10_complete_dropout_accepted(self):
        self.assertEqual(
            self.review[
                "a17_complete_lidar_outage_outcome"
            ],
            "ACCEPTED",
        )

    def test_11_paired_imu_output_sensitivity(self):
        self.assertEqual(
            self.review[
                "five_node_clean_biased_accepted_pairs"
            ],
            128,
        )
        self.assertGreater(
            self.review[
                "five_node_max_imu_output_delta_m"
            ],
            0.0,
        )

    def test_12_five_long_horizon_outages(self):
        self.assertEqual(
            len(
                self.review[
                    "long_horizon_combined_outages"
                ]
            ),
            5,
        )

    def test_13_complete_outage_no_lidar(self):
        complete = self.review[
            "long_horizon_complete_outage"
        ]

        self.assertEqual(
            complete["current_lidar_factors"], 0
        )

    def test_14_finite_combined_interactions(self):
        for row in self.review[
            "long_horizon_combined_outages"
        ].values():
            value = row["interaction_norm_m"]

            if value is not None:
                self.assertTrue(math.isfinite(value))
                self.assertGreaterEqual(value, 0.0)

    def test_15_no_accuracy_inference(self):
        for key in (
            "numerical_solver_acceptance_proves_accuracy",
            "numeric_rank_proves_physical_observability",
            "baseline_delta_is_ground_truth_error",
            "physical_recovery_proven",
        ):
            self.assertIs(self.review[key], False)

    def test_16_real_admission_denied(self):
        for key in (
            "real_sensor_admission_authorized",
            "health_inference_authorized",
            "factor_weighting_authorized",
            "recorded_data_accessed",
            "held_out_confirmation_data_accessed",
        ):
            self.assertIs(self.review[key], False)

    def test_17_all_capabilities_blocked(self):
        decision = self.review["admission_decision"]

        self.assertEqual(
            set(decision),
            set(BLOCKED_CAPABILITIES),
        )

        self.assertTrue(all(
            value == "BLOCKED"
            for value in decision.values()
        ))

    def test_18_protected_split(self):
        self.assertEqual(
            self.review["m2dgr_gates_closed"], 11
        )
        self.assertEqual(
            self.review["m2dgr_split"],
            {
                "train": 22,
                "validation_calibration": 7,
                "confirmation_test": 7,
            },
        )

    def test_19_deterministic_digest_and_parity(self):
        first = evidence_digest(self.review)
        second = evidence_digest(self.review)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

        with self.assertRaises(EvidenceReviewError):
            evidence_digest({})

        repeated = published_combined_case(
            "combined_bias", "complete"
        )

        self.assertEqual(
            repeated["solver_outcome"],
            self.review[
                "long_horizon_complete_outage"
            ]["combined_solver_outcome"],
        )

    def test_20_closed_gates_and_import_scope(self):
        with self.assertRaises(
            HealthModelInterfaceError
        ):
            assert_training_authorized()

        with self.assertRaises(
            HealthModelInterfaceError
        ):
            assert_inference_authorized()

        with self.assertRaises(
            FactorConditioningContractError
        ):
            assert_factor_scale_execution_authorized()

        self.assertEqual(
            len(inspect.signature(run_review).parameters),
            0,
        )

        path = ROOT / (
            "src/trust_robot/"
            "analytic_15d_evidence_review_v1.py"
        )

        tree = ast.parse(path.read_text())

        imports = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.module
        }

        self.assertEqual(imports, {
            "__future__",
            "trust_robot.analytic_15d_exhaustive_lidar_dropout_v1",
            "trust_robot.analytic_15d_joint_imu_lidar_stress_v1",
            "trust_robot.analytic_15d_long_horizon_joint_stress_v1",
            "trust_robot.analytic_15d_combined_imu_faults_v1",
        })


if __name__ == "__main__":
    unittest.main(verbosity=2)
