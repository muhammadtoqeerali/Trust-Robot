import ast
import json
import unittest
from pathlib import Path

from trust_robot.analytic_15d_pose_slot_integration_v1 import (
    SCHEMA,
    STATUS,
    SCENARIOS,
    Synthetic15DIntegrationError,
    run_scenario,
    run_all_scenarios,
)

from trust_robot.multimodal_health_model import (
    HealthModelInterfaceError,
    assert_inference_authorized,
    assert_training_authorized,
)

from trust_robot.factor_conditioning import (
    FactorConditioningContractError,
    assert_factor_scale_execution_authorized,
)

ROOT = Path(__file__).resolve().parents[2]


class Synthetic15DIntegrationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.results = {
            row["scenario"]: row
            for row in run_all_scenarios()
        }

        assert set(cls.results) == set(SCENARIOS)

    def test_01_frozen_scenarios(self):
        self.assertEqual(
            SCENARIOS,
            (
                "baseline",
                "lidar_edge_removed",
                "camera_substitutes_lidar",
                "camera_on_removed_lidar_edge",
            ),
        )

    def test_02_schema_and_status(self):
        for row in self.results.values():
            self.assertEqual(row["schema"], SCHEMA)
            self.assertEqual(row["status"], STATUS)

    def test_03_baseline_seven_lidar_slots(self):
        r = self.results["baseline"]
        self.assertEqual(r["synthetic_lidar_input_factor_count"], 7)
        self.assertEqual(r["selected_lidar_slot_count"], 7)
        self.assertEqual(r["selected_camera_surrogate_slot_count"], 0)
        self.assertEqual(r["total_pose_slot_count"], 7)

    def test_04_lidar_removal_six_slots(self):
        r = self.results["lidar_edge_removed"]
        self.assertEqual(r["synthetic_lidar_input_factor_count"], 6)
        self.assertEqual(r["selected_lidar_slot_count"], 6)
        self.assertEqual(r["total_pose_slot_count"], 6)

    def test_05_camera_replaces_existing_lidar(self):
        r = self.results["camera_substitutes_lidar"]
        self.assertEqual(r["synthetic_lidar_input_factor_count"], 7)
        self.assertEqual(r["selected_lidar_slot_count"], 6)
        self.assertEqual(r["selected_camera_surrogate_slot_count"], 1)
        self.assertEqual(r["total_pose_slot_count"], 7)
        self.assertEqual(r["replaced_lidar_edges"], [[1, 2]])

    def test_06_camera_occupies_removed_edge(self):
        r = self.results["camera_on_removed_lidar_edge"]
        self.assertEqual(r["synthetic_lidar_input_factor_count"], 6)
        self.assertEqual(r["selected_lidar_slot_count"], 6)
        self.assertEqual(r["selected_camera_surrogate_slot_count"], 1)
        self.assertEqual(r["total_pose_slot_count"], 7)
        self.assertEqual(r["replaced_lidar_edges"], [])

    def test_07_five_node_15d_outputs(self):
        for row in self.results.values():
            self.assertEqual(row["node_count"], 5)
            self.assertEqual(row["state_dimension"], 15)

    def test_08_imu_factors_preserved(self):
        for row in self.results.values():
            self.assertEqual(row["synthetic_imu_factor_count"], 4)
            self.assertIs(row["imu_samples_reused"], False)

    def test_09_marginalization_completed(self):
        for row in self.results.values():
            self.assertEqual(row["accepted_window_count"], 4)
            self.assertEqual(row["schur_elimination_count"], 3)
            self.assertTrue(row["all_windows_numerically_full_rank"])

    def test_10_measurement_accounting(self):
        for row in self.results.values():
            self.assertEqual(row["unaccounted_factor_count"], 0)
            self.assertIs(
                row["factor_reuse_after_marginalization"],
                False
            )

    def test_11_disjoint_factor_ledger(self):
        for row in self.results.values():
            edges = [
                tuple(item["edge"])
                for item in row["factor_ledger"]
            ]

            self.assertEqual(
                len(edges),
                row["total_pose_slot_count"]
            )

            self.assertEqual(len(edges), len(set(edges)))

            for item in row["factor_ledger"]:
                self.assertEqual(
                    item["origin"],
                    "ANALYTIC_FIXTURE"
                )

    def test_12_identical_surrogate_solver_states(self):
        # All three cases have numerically identical pose
        # factors. The copied camera surrogate is NOT an
        # independent sensor observation.
        a = self.results["baseline"][
            "synthetic_state_content_sha256"
        ]

        b = self.results["camera_substitutes_lidar"][
            "synthetic_state_content_sha256"
        ]

        c = self.results["camera_on_removed_lidar_edge"][
            "synthetic_state_content_sha256"
        ]

        self.assertEqual(a, b)
        self.assertEqual(a, c)
        self.assertEqual(len(a), 64)

    def test_13_deterministic_repetition(self):
        first = self.results["baseline"]
        second = run_scenario("baseline")

        self.assertEqual(
            json.dumps(first,sort_keys=True,allow_nan=False),
            json.dumps(second,sort_keys=True,allow_nan=False)
        )

    def test_14_reject_nonfrozen_scenarios(self):
        for name in (
            None, True, 0, "",
            "M2DGR", "recorded",
            "healthy", "custom_factor"
        ):
            with self.subTest(name=name):
                with self.assertRaises(
                    Synthetic15DIntegrationError
                ):
                    run_scenario(name)

    def test_15_scientific_denials_and_import_scope(self):
        denied = (
            "independent_camera_evidence_available",
            "independent_camera_weighting_authorized",
            "physical_observability_proven",
            "posterior_consistency_proven",
            "physical_sensor_calibration_validated",
            "health_probabilities_generated",
            "health_labels_assigned",
            "factor_weights_modified",
            "recorded_ground_truth_accessed",
            "recorded_sensor_data_used",
            "localization_recovery_demonstrated",
            "real_factor_execution_authorized",
            "confirmation_test_accessed",
        )

        for row in self.results.values():
            self.assertTrue(
                row["camera_surrogate_copied_from_analytic_lidar"]
            )

            for key in denied:
                self.assertIs(row[key], False, key)

        module_path = ROOT / (
            "src/trust_robot/"
            "analytic_15d_pose_slot_integration_v1.py"
        )

        tree = ast.parse(module_path.read_text())

        modules = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }

        self.assertEqual(
            modules,
            {
                "__future__",
                "trust_robot.analytic_inertial_15d",
                "trust_robot.analytic_preintegrated_fusion",
                "trust_robot.analytic_marginalized_fusion",
                "trust_robot.multimodal_factor_interface",
            }
        )

    def test_16_health_and_weighting_gates_closed(self):
        with self.assertRaises(HealthModelInterfaceError):
            assert_training_authorized()

        with self.assertRaises(HealthModelInterfaceError):
            assert_inference_authorized()

        with self.assertRaises(FactorConditioningContractError):
            assert_factor_scale_execution_authorized()


if __name__ == "__main__":
    unittest.main(verbosity=2)
