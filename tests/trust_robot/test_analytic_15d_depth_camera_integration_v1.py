import ast
import inspect
import json
import math
import unittest
from pathlib import Path

from trust_robot.analytic_depth_camera_source_v1 import (
    generate_packet,
)

from trust_robot.analytic_15d_depth_camera_integration_v1 import (
    SCHEMA,
    STATUS,
    SCENARIOS,
    SyntheticDepth15DIntegrationError,
    run_scenario,
    run_all_scenarios,
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


class SyntheticDepth15DIntegrationTests(unittest.TestCase):

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
                "baseline_lidar",
                "lidar_edge_removed",
                "depth_camera_ideal_restore",
                "depth_camera_noisy_restore",
                "depth_camera_biased_restore",
                "depth_camera_noisy_replace",
            ),
        )

    def test_02_schema_and_status(self):
        for r in self.results.values():
            self.assertEqual(r["schema"], SCHEMA)
            self.assertEqual(r["status"], STATUS)

    def test_03_baseline_pose_slots(self):
        r = self.results["baseline_lidar"]
        self.assertEqual(r["input_lidar_factor_count"], 7)
        self.assertEqual(r["selected_lidar_slot_count"], 7)
        self.assertEqual(r["selected_camera_slot_count"], 0)
        self.assertEqual(r["total_pose_slot_count"], 7)

    def test_04_lidar_removal(self):
        r = self.results["lidar_edge_removed"]
        self.assertEqual(r["input_lidar_factor_count"], 6)
        self.assertEqual(r["selected_lidar_slot_count"], 6)
        self.assertEqual(r["total_pose_slot_count"], 6)

    def test_05_ideal_camera_restoration(self):
        r = self.results["depth_camera_ideal_restore"]
        self.assertEqual(r["camera_mode"], "ideal")
        self.assertEqual(r["selected_camera_slot_count"], 1)
        self.assertEqual(r["total_pose_slot_count"], 7)
        self.assertEqual(r["replaced_lidar_edges"], [])

    def test_06_noisy_camera_restoration(self):
        r = self.results["depth_camera_noisy_restore"]
        self.assertEqual(r["camera_mode"], "noisy")
        self.assertEqual(r["selected_camera_slot_count"], 1)
        self.assertEqual(r["total_pose_slot_count"], 7)

    def test_07_biased_camera_restoration(self):
        r = self.results["depth_camera_biased_restore"]
        self.assertEqual(r["camera_mode"], "biased")
        self.assertEqual(r["selected_camera_slot_count"], 1)
        self.assertEqual(r["total_pose_slot_count"], 7)

    def test_08_noisy_camera_replacement(self):
        r = self.results["depth_camera_noisy_replace"]
        self.assertEqual(r["camera_mode"], "noisy")
        self.assertEqual(r["selected_camera_slot_count"], 1)
        self.assertEqual(r["replaced_lidar_edges"], [[1, 2]])

    def test_09_disjoint_factor_ledgers(self):
        for r in self.results.values():
            rows = r["factor_ledger"]
            edges = [tuple(x["edge"]) for x in rows]

            self.assertEqual(
                len(rows), r["total_pose_slot_count"]
            )
            self.assertEqual(len(edges), len(set(edges)))

            for item in rows:
                self.assertEqual(
                    item["origin"],
                    "ANALYTIC_FIXTURE",
                )
                self.assertIn(
                    item["modality"],
                    ("camera", "lidar"),
                )

    def test_10_five_nodes_and_15d_states(self):
        for r in self.results.values():
            self.assertEqual(r["node_count"], 5)
            self.assertEqual(r["state_dimension"], 15)
            self.assertEqual(
                len(r["synthetic_final_position_m"]), 3
            )

    def test_11_imu_chain_and_ownership(self):
        for r in self.results.values():
            self.assertEqual(
                r["synthetic_imu_factor_count"], 4
            )
            self.assertIs(r["imu_samples_reused"], False)
            self.assertEqual(
                r["unaccounted_factor_count"], 0
            )
            self.assertIs(
                r["factor_reuse_after_marginalization"],
                False,
            )

    def test_12_schur_marginalization(self):
        for r in self.results.values():
            self.assertEqual(
                r["accepted_window_count"], 4
            )
            self.assertEqual(
                r["schur_elimination_count"], 3
            )
            self.assertTrue(
                r["all_windows_numerically_full_rank"]
            )

    def test_13_finite_numerical_diagnostics(self):
        for r in self.results.values():
            self.assertTrue(math.isfinite(
                r["total_window_cost_diagnostic"]
            ))
            self.assertGreaterEqual(
                r["total_window_cost_diagnostic"], 0.0
            )
            self.assertEqual(
                len(r["synthetic_state_sha256"]), 64
            )
            self.assertTrue(math.isfinite(
                r[
                    "final_position_delta_from_synthetic_baseline_m"
                ]
            ))

    def test_14_distinct_camera_measurements(self):
        packets = [
            generate_packet((1, 2), mode)[0]
            for mode in ("ideal", "noisy", "biased")
        ]

        self.assertEqual(
            len({p.measurement_id for p in packets}), 3
        )

        self.assertEqual(
            len({p.measurement for p in packets}), 3
        )

    def test_15_restore_and_replace_are_equivalent(self):
        restored = self.results[
            "depth_camera_noisy_restore"
        ]
        replaced = self.results[
            "depth_camera_noisy_replace"
        ]

        self.assertEqual(
            restored["synthetic_state_sha256"],
            replaced["synthetic_state_sha256"],
        )

        self.assertEqual(
            restored["total_window_cost_diagnostic"],
            replaced["total_window_cost_diagnostic"],
        )

    def test_16_deterministic_repetition(self):
        first = self.results["baseline_lidar"]
        again = run_scenario("baseline_lidar")

        # run_scenario has no baseline-relative delta.
        original = {
            k: v for k, v in first.items()
            if k != (
                "final_position_delta_from_synthetic_baseline_m"
            )
        }

        self.assertEqual(
            json.dumps(original, sort_keys=True, allow_nan=False),
            json.dumps(again, sort_keys=True, allow_nan=False),
        )

    def test_17_distinct_numerical_response(self):
        base = self.results["baseline_lidar"]
        noisy = self.results[
            "depth_camera_noisy_restore"
        ]
        biased = self.results[
            "depth_camera_biased_restore"
        ]

        self.assertGreater(
            noisy["total_window_cost_diagnostic"],
            base["total_window_cost_diagnostic"],
        )

        self.assertGreater(
            biased["total_window_cost_diagnostic"],
            noisy["total_window_cost_diagnostic"],
        )

        self.assertNotEqual(
            noisy["synthetic_state_sha256"],
            biased["synthetic_state_sha256"],
        )

    def test_18_reject_unapproved_scenarios(self):
        for invalid in (
            None,
            True,
            0,
            "",
            "M2DGR",
            "recorded_camera",
            "healthy",
            "custom_weight",
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(
                    SyntheticDepth15DIntegrationError
                ):
                    run_scenario(invalid)

    def test_19_scientific_denials_and_import_scope(self):
        denied = (
            "camera_factor_copied_from_lidar",
            "independent_physical_camera_evidence",
            "independent_camera_weighting_supported",
            "factor_weights_modified",
            "physical_localization_accuracy_established",
            "physical_localization_recovery_demonstrated",
            "ground_truth_scoring_performed",
            "health_probabilities_generated",
            "health_labels_assigned",
            "recorded_data_accessed",
            "real_factor_execution_authorized",
            "confirmation_test_accessed",
        )

        for r in self.results.values():
            self.assertIs(
                r["camera_metric_depth_is_manufactured"],
                True,
            )
            self.assertIs(
                r["shared_analytic_motion_model"],
                True,
            )

            for key in denied:
                self.assertIs(r[key], False, key)

        path = ROOT / (
            "src/trust_robot/"
            "analytic_15d_depth_camera_integration_v1.py"
        )

        tree = ast.parse(path.read_text())

        imports = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }

        self.assertEqual(imports, {
            "__future__",
            "trust_robot.analytic_inertial_15d",
            "trust_robot.analytic_preintegrated_fusion",
            "trust_robot.analytic_marginalized_fusion",
            "trust_robot.analytic_depth_camera_source_v1",
            "trust_robot.multimodal_factor_interface",
        })

        self.assertEqual(
            tuple(inspect.signature(
                run_scenario
            ).parameters),
            ("name",),
        )

    def test_20_health_and_conditioning_gates(self):
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
