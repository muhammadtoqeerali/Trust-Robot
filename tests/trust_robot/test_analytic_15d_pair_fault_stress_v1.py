import ast
import inspect
import math
import unittest
from pathlib import Path

from trust_robot.analytic_15d_pair_fault_stress_v1 import (
    SCHEMA,
    STATUS,
    PAIRS,
    DENIALS,
    SyntheticPairFaultError,
    run_case,
    run_matrix,
)

from trust_robot.analytic_depth_camera_source_v1 import (
    EDGES,
    MODES,
)

from trust_robot.analytic_15d_camera_edge_sensitivity_v1 import (
    run_case as published_single_edge,
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


class SyntheticDoubleFaultTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.rows = run_matrix()
        cls.by = {
            (
                None if row["pair"] is None
                else tuple(
                    tuple(x) for x in row["pair"]
                ),
                row["camera_mode"],
            ): row
            for row in cls.rows
        }

    def test_01_frozen_pairs(self):
        self.assertEqual(len(PAIRS), 21)
        self.assertEqual(len(set(PAIRS)), 21)
        self.assertEqual(len(EDGES), 7)

    def test_02_all_eighty_five_cases(self):
        self.assertEqual(len(self.rows), 85)
        self.assertEqual(len(self.by), 85)

    def test_03_public_api_accepts_no_external_data(self):
        self.assertEqual(
            tuple(inspect.signature(run_case).parameters),
            ("pair", "mode"),
        )
        self.assertEqual(
            len(inspect.signature(run_matrix).parameters),
            0,
        )

    def test_04_baseline_is_accepted(self):
        row = self.by[None, None]
        self.assertEqual(row["solver_outcome"], "ACCEPTED")
        self.assertEqual(row["total_pose_slot_count"], 7)
        self.assertEqual(row["selected_camera_slot_count"], 0)

    def test_05_baseline_matches_published_solver(self):
        published = published_single_edge()
        self.assertEqual(
            self.by[None, None]["synthetic_state_sha256"],
            published["synthetic_state_sha256"],
        )

    def test_06_twenty_one_double_removals(self):
        for pair in PAIRS:
            row = self.by[pair, None]
            self.assertEqual(
                row["configuration"], "two_lidar_removed"
            )
            self.assertEqual(row["total_pose_slot_count"], 5)
            self.assertEqual(row["selected_camera_slot_count"], 0)
            self.assertEqual(row["selected_lidar_slot_count"], 5)

    def test_07_sixty_three_dual_restorations(self):
        restored = [
            r for r in self.rows
            if r["configuration"] == "two_camera_restored"
        ]
        self.assertEqual(len(restored), 63)
        for row in restored:
            self.assertEqual(row["total_pose_slot_count"], 7)
            self.assertEqual(row["selected_camera_slot_count"], 2)
            self.assertEqual(row["selected_lidar_slot_count"], 5)

    def test_08_three_modes_per_pair(self):
        self.assertEqual(
            MODES, ("ideal", "noisy", "biased")
        )
        for pair in PAIRS:
            for mode in MODES:
                self.assertIn((pair, mode), self.by)

    def test_09_camera_edges_match_missing_edges(self):
        for pair in PAIRS:
            for mode in MODES:
                row = self.by[pair, mode]
                observed = {
                    tuple(x["edge"])
                    for x in row["factor_ledger"]
                    if x["modality"] == "camera"
                }
                self.assertEqual(observed, set(pair))

    def test_10_no_duplicate_pose_edges(self):
        for row in self.rows:
            edges = [
                tuple(item["edge"])
                for item in row["factor_ledger"]
            ]
            self.assertEqual(len(edges), len(set(edges)))
            self.assertEqual(
                len(edges),
                row["total_pose_slot_count"],
            )

    def test_11_no_duplicate_measurement_ids(self):
        for row in self.rows:
            ids = [
                item["measurement_id"]
                for item in row["factor_ledger"]
            ]
            self.assertEqual(len(ids), len(set(ids)))

    def test_12_provenance_is_analytic_only(self):
        for row in self.rows:
            for item in row["factor_ledger"]:
                self.assertEqual(
                    item["origin"], "ANALYTIC_FIXTURE"
                )

    def test_13_imu_chain_remains_frozen(self):
        for row in self.rows:
            self.assertEqual(
                row["synthetic_imu_factor_count"], 4
            )
            self.assertEqual(row["node_count"], 5)
            self.assertEqual(row["state_dimension"], 15)

    def test_14_accepted_or_explicitly_rejected(self):
        allowed = {
            "ACCEPTED", "NUMERICALLY_REJECTED"
        }
        for row in self.rows:
            self.assertIn(
                row["solver_outcome"], allowed
            )
            if row["solver_outcome"] == "ACCEPTED":
                self.assertIsNone(
                    row["numerical_rejection"]
                )
                self.assertEqual(
                    row["accepted_window_count"], 4
                )
                self.assertEqual(
                    row["schur_elimination_count"], 3
                )
            else:
                self.assertTrue(
                    row["numerical_rejection"].startswith(
                        "Marginalized window solve failed at "
                    )
                )

    def test_15_finite_accepted_diagnostics(self):
        for row in self.rows:
            if row["solver_outcome"] != "ACCEPTED":
                self.assertIsNone(
                    row["synthetic_final_position_m"]
                )
                self.assertIsNone(
                    row["total_window_cost_diagnostic"]
                )
                continue

            self.assertTrue(math.isfinite(
                row["total_window_cost_diagnostic"]
            ))
            self.assertTrue(math.isfinite(
                row["final_position_delta_from_baseline_m"]
            ))
            self.assertEqual(
                len(row["synthetic_state_sha256"]), 64
            )

    def test_16_two_camera_source_receipts(self):
        for pair in PAIRS:
            for mode in MODES:
                row = self.by[pair, mode]
                receipts = row["camera_source_receipts"]
                self.assertEqual(len(receipts), 2)
                self.assertTrue(all(
                    r["lidar_pose_factor_copied"] is False
                    and r["metric_depth_manufactured"] is True
                    and r["factor_weight_selected"] is False
                    for r in receipts
                ))

    def test_17_scientific_denials(self):
        for row in self.rows:
            self.assertEqual(row["schema"], SCHEMA)
            self.assertEqual(row["status"], STATUS)
            self.assertIs(
                row["shared_analytic_motion_model"], True
            )
            self.assertIs(
                row[
                    "numerical_rank_proves_physical_observability"
                ], False,
            )
            for key in DENIALS:
                self.assertIs(row[key], False, key)

    def test_18_deterministic_repetition(self):
        pair = PAIRS[0]
        row = self.by[pair, "noisy"]
        repeat = run_case(pair, "noisy")

        self.assertEqual(
            row["solver_outcome"],
            repeat["solver_outcome"],
        )
        self.assertEqual(
            row["synthetic_state_sha256"],
            repeat["synthetic_state_sha256"],
        )
        self.assertEqual(
            row["total_window_cost_diagnostic"],
            repeat["total_window_cost_diagnostic"],
        )

    def test_19_invalid_inputs_are_rejected(self):
        invalid = (
            (None, "ideal"),
            ((EDGES[0],), None),
            ((EDGES[0], EDGES[0]), None),
            ((EDGES[1], EDGES[0]), None),
            ((EDGES[0], (0, True)), None),
            ((EDGES[0], [1, 2]), None),
            ((EDGES[0], (1, 2.0)), None),
            ((EDGES[0], EDGES[1]), True),
            ((EDGES[0], EDGES[1]), "real"),
        )

        for pair, mode in invalid:
            with self.subTest(pair=pair, mode=mode):
                with self.assertRaises(
                    SyntheticPairFaultError
                ):
                    run_case(pair, mode)

    def test_20_source_scope_and_closed_gates(self):
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
            "analytic_15d_pair_fault_stress_v1.py"
        )

        tree = ast.parse(path.read_text())

        imports = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.module
        }

        expected = {
            "__future__",
            "itertools",
            "trust_robot.analytic_inertial_15d",
            "trust_robot.analytic_preintegrated_fusion",
            "trust_robot.analytic_marginalized_fusion",
            "trust_robot.analytic_depth_camera_source_v1",
            "trust_robot.multimodal_factor_interface",
        }

        self.assertEqual(imports, expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
