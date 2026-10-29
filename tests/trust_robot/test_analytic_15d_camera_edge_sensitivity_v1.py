import ast
import inspect
import json
import math
import unittest
from pathlib import Path

from trust_robot.analytic_depth_camera_source_v1 import (
    EDGES, MODES, generate_packet,
)

from trust_robot.analytic_15d_camera_edge_sensitivity_v1 import (
    SCHEMA,
    STATUS,
    DENIALS,
    SyntheticSensitivityError,
    run_case,
    run_matrix,
)

from trust_robot.analytic_15d_depth_camera_integration_v1 import (
    run_scenario as published_scenario,
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


class SyntheticSevenEdgeSensitivityTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.rows = run_matrix()
        cls.by = {
            (
                tuple(r["edge"]) if r["edge"] is not None
                else None,
                r["camera_mode"],
            ): r
            for r in cls.rows
        }

    def test_01_frozen_public_interface(self):
        self.assertEqual(
            tuple(inspect.signature(run_case).parameters),
            ("edge", "mode"),
        )
        self.assertEqual(
            len(inspect.signature(run_matrix).parameters), 0
        )

    def test_02_frozen_edge_and_mode_inventory(self):
        self.assertEqual(len(EDGES), 7)
        self.assertEqual(MODES, ("ideal", "noisy", "biased"))

    def test_03_twenty_nine_configurations(self):
        self.assertEqual(len(self.rows), 29)

    def test_04_no_duplicate_configurations(self):
        self.assertEqual(len(self.by), 29)

    def test_05_baseline_factor_counts(self):
        row = self.by[None, None]
        self.assertEqual(row["total_pose_slot_count"], 7)
        self.assertEqual(row["selected_camera_slot_count"], 0)
        self.assertEqual(row["input_lidar_factor_count"], 7)

    def test_06_seven_single_lidar_removals(self):
        for edge in EDGES:
            row = self.by[edge, None]
            self.assertEqual(row["configuration"], "lidar_removed")
            self.assertEqual(row["total_pose_slot_count"], 6)
            self.assertEqual(row["selected_lidar_slot_count"], 6)
            self.assertEqual(row["selected_camera_slot_count"], 0)

    def test_07_twenty_one_camera_restorations(self):
        restored = [
            r for r in self.rows
            if r["configuration"] == "camera_restored"
        ]
        self.assertEqual(len(restored), 21)
        for row in restored:
            self.assertEqual(row["total_pose_slot_count"], 7)
            self.assertEqual(row["selected_camera_slot_count"], 1)
            self.assertEqual(row["selected_lidar_slot_count"], 6)

    def test_08_imu_chain_is_preserved(self):
        for row in self.rows:
            self.assertEqual(
                row["synthetic_imu_factor_count"], 4
            )
            self.assertIs(row["imu_samples_reused"], False)

    def test_09_schur_window_counts(self):
        for row in self.rows:
            self.assertEqual(row["accepted_window_count"], 4)
            self.assertEqual(row["schur_elimination_count"], 3)

    def test_10_factor_bookkeeping(self):
        for row in self.rows:
            self.assertEqual(
                row["unaccounted_factor_count"], 0
            )
            self.assertIs(
                row["factor_reuse_after_marginalization"],
                False,
            )

    def test_11_no_duplicate_graph_edges(self):
        for row in self.rows:
            edges = [
                tuple(x["edge"])
                for x in row["factor_ledger"]
            ]
            self.assertEqual(len(edges), len(set(edges)))
            self.assertEqual(
                len(edges), row["total_pose_slot_count"]
            )

    def test_12_factor_origin_is_manufactured(self):
        for row in self.rows:
            for item in row["factor_ledger"]:
                self.assertEqual(
                    item["origin"], "ANALYTIC_FIXTURE"
                )

    def test_13_camera_is_on_selected_edge(self):
        for edge in EDGES:
            for mode in MODES:
                row = self.by[edge, mode]
                cameras = [
                    x for x in row["factor_ledger"]
                    if x["modality"] == "camera"
                ]
                self.assertEqual(len(cameras), 1)
                self.assertEqual(
                    tuple(cameras[0]["edge"]), edge
                )

    def test_14_frozen_scientific_denials(self):
        for row in self.rows:
            for name in DENIALS:
                self.assertIs(row[name], False, name)

    def test_15_camera_source_receipts(self):
        for edge in EDGES:
            for mode in MODES:
                meta = self.by[edge, mode][
                    "camera_source_metadata"
                ]
                self.assertIs(
                    meta["lidar_pose_factor_copied"], False
                )
                self.assertIs(
                    meta["real_factor_execution_authorized"],
                    False,
                )
                self.assertIs(
                    meta["metric_depth_manufactured"], True
                )

    def test_16_three_distinct_measurements_per_edge(self):
        for edge in EDGES:
            packets = [
                generate_packet(edge, mode)[0]
                for mode in MODES
            ]
            self.assertEqual(
                len({p.measurement_id for p in packets}), 3
            )
            self.assertEqual(
                len({p.measurement for p in packets}), 3
            )

    def test_17_costs_are_finite(self):
        for row in self.rows:
            cost = row["total_window_cost_diagnostic"]
            self.assertTrue(math.isfinite(cost))
            self.assertGreaterEqual(cost, 0.0)

    def test_18_final_states_are_finite(self):
        for row in self.rows:
            self.assertEqual(row["state_dimension"], 15)
            self.assertEqual(row["node_count"], 5)
            self.assertEqual(
                len(row["synthetic_final_position_m"]), 3
            )
            self.assertTrue(all(
                math.isfinite(x)
                for x in row["synthetic_final_position_m"]
            ))

    def test_19_baseline_relative_diagnostics(self):
        self.assertEqual(
            self.by[None, None][
                "final_position_delta_from_synthetic_baseline_m"
            ],
            0.0,
        )
        for row in self.rows:
            self.assertTrue(math.isfinite(
                row[
                    "final_position_delta_from_synthetic_baseline_m"
                ]
            ))

    def test_20_ideal_restoration_closes_on_fixture(self):
        for edge in EDGES:
            self.assertLess(
                self.by[edge, "ideal"][
                    "final_position_delta_from_synthetic_baseline_m"
                ],
                1e-10,
            )

    def test_21_noisy_restoration_changes_output(self):
        for edge in EDGES:
            self.assertGreater(
                self.by[edge, "noisy"][
                    "final_position_delta_from_synthetic_baseline_m"
                ],
                0.0,
            )

    def test_22_biased_restoration_changes_output(self):
        for edge in EDGES:
            self.assertGreater(
                self.by[edge, "biased"][
                    "final_position_delta_from_synthetic_baseline_m"
                ],
                0.0,
            )

    def test_23_frozen_fixture_bias_cost(self):
        # Fixture-specific assertion only.
        # No general monotonic accuracy claim is made.
        for edge in EDGES:
            self.assertGreater(
                self.by[edge, "biased"][
                    "total_window_cost_diagnostic"
                ],
                self.by[edge, "noisy"][
                    "total_window_cost_diagnostic"
                ],
            )

    def test_24_published_baseline_and_edge_12(self):
        baseline = published_scenario("baseline_lidar")
        self.assertEqual(
            self.by[None, None]["synthetic_state_sha256"],
            baseline["synthetic_state_sha256"],
        )

        published = published_scenario(
            "depth_camera_noisy_restore"
        )
        self.assertEqual(
            self.by[(1, 2), "noisy"][
                "synthetic_state_sha256"
            ],
            published["synthetic_state_sha256"],
        )

    def test_25_determinism_and_invalid_inputs(self):
        original = self.by[(1, 2), "noisy"]
        repeat = run_case((1, 2), "noisy")

        self.assertEqual(
            original["synthetic_state_sha256"],
            repeat["synthetic_state_sha256"],
        )

        invalid = (
            (None, "noisy"),
            ([0, 1], None),
            ((0, True), None),
            ((False, 1), None),
            ((True, 2), None),
            ((0, 1.0), None),
            ((0, [1]), None),
            ((0, 1, 2), None),
            (("0", 1), None),
            ((0, 4), None),
            ((1, 2), "recorded"),
            ((1, 2), True),
            ((1, 2), "healthy"),
        )

        for edge, mode in invalid:
            with self.subTest(edge=edge, mode=mode):
                with self.assertRaises(
                    SyntheticSensitivityError
                ):
                    run_case(edge, mode)

    def test_26_health_gates_and_source_scope(self):
        with self.assertRaises(HealthModelInterfaceError):
            assert_training_authorized()

        with self.assertRaises(HealthModelInterfaceError):
            assert_inference_authorized()

        with self.assertRaises(
            FactorConditioningContractError
        ):
            assert_factor_scale_execution_authorized()

        path = ROOT / (
            "src/trust_robot/"
            "analytic_15d_camera_edge_sensitivity_v1.py"
        )

        tree = ast.parse(path.read_text())
        imported = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.module
        }

        self.assertEqual(imported, {
            "__future__",
            "trust_robot.analytic_inertial_15d",
            "trust_robot.analytic_preintegrated_fusion",
            "trust_robot.analytic_marginalized_fusion",
            "trust_robot.analytic_depth_camera_source_v1",
            "trust_robot.multimodal_factor_interface",
        })

        self.assertEqual(
            len({
                json.dumps(r, sort_keys=True, allow_nan=False)
                for r in self.rows
            }),
            29,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
