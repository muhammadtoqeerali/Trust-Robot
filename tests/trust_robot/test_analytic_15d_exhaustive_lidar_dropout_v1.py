import ast
import inspect
import math
import unittest
from collections import Counter
from pathlib import Path

from trust_robot.analytic_15d_exhaustive_lidar_dropout_v1 import (
    SCHEMA,
    STATUS,
    DROPSETS,
    DENIALS,
    SyntheticDropoutError,
    run_case,
    run_matrix,
)

from trust_robot.analytic_depth_camera_source_v1 import EDGES

from trust_robot.analytic_15d_camera_edge_sensitivity_v1 import (
    run_case as published_single_edge,
)

from trust_robot.analytic_15d_pair_fault_stress_v1 import (
    PAIRS,
    run_case as published_pair,
)

from trust_robot.analytic_inertial_15d import make_fixture
from trust_robot.analytic_preintegrated_fusion import make_factors
from trust_robot.analytic_marginalized_fusion import (
    estimate_marginalized_with_support,
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


class ExhaustiveSyntheticLiDARDropoutTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.rows = run_matrix()
        cls.by = {
            tuple(tuple(edge) for edge in row["removed_edges"]):
                row
            for row in cls.rows
        }

    def test_01_all_128_patterns(self):
        self.assertEqual(len(self.rows), 128)
        self.assertEqual(len(self.by), 128)

    def test_02_binomial_dropout_inventory(self):
        expected = (1, 7, 21, 35, 35, 21, 7, 1)
        counts = Counter(len(x) for x in DROPSETS)
        self.assertEqual(
            tuple(counts[n] for n in range(8)),
            expected,
        )

    def test_03_all_patterns_are_unique(self):
        self.assertEqual(len(DROPSETS), len(set(DROPSETS)))
        self.assertEqual(len(EDGES), 7)

    def test_04_public_interface_is_restricted(self):
        signature = inspect.signature(run_case)
        self.assertEqual(
            tuple(signature.parameters),
            ("removed_edges",),
        )
        self.assertEqual(
            len(inspect.signature(run_matrix).parameters),
            0,
        )

    def test_05_baseline_has_all_lidar(self):
        row = self.by[()]
        self.assertEqual(
            row["remaining_lidar_factor_count"], 7
        )
        self.assertEqual(
            row["removed_lidar_factor_count"], 0
        )
        self.assertEqual(row["solver_outcome"], "ACCEPTED")

    def test_06_total_dropout_has_zero_lidar(self):
        row = self.by[tuple(EDGES)]
        self.assertEqual(
            row["remaining_lidar_factor_count"], 0
        )
        self.assertEqual(
            row["removed_lidar_factor_count"], 7
        )

    def test_07_all_factor_counts_are_consistent(self):
        for row in self.rows:
            self.assertEqual(
                row["removed_lidar_factor_count"]
                + row["remaining_lidar_factor_count"],
                7,
            )
            self.assertEqual(
                row["synthetic_imu_factor_count"], 4
            )

    def test_08_solver_outcome_is_explicit(self):
        for row in self.rows:
            self.assertIn(
                row["solver_outcome"],
                ("ACCEPTED", "NUMERICALLY_REJECTED"),
            )

    def test_09_numerical_rejections_are_bounded(self):
        for row in self.rows:
            if row["solver_outcome"] == "NUMERICALLY_REJECTED":
                self.assertTrue(
                    row["numerical_rejection"].startswith(
                        "Marginalized window solve failed at "
                    )
                )
                self.assertIsNone(
                    row["synthetic_final_position_m"]
                )

    def test_10_accepted_windows_and_support(self):
        for row in self.rows:
            if row["solver_outcome"] != "ACCEPTED":
                continue

            self.assertEqual(row["accepted_window_count"], 4)
            self.assertEqual(row["schur_elimination_count"], 3)
            self.assertEqual(len(row["support_windows"]), 4)

            for support in row["support_windows"]:
                self.assertIn(
                    support["status"],
                    ("NUMERICALLY_SUPPORTED",
                     "NUMERICALLY_UNAVAILABLE"),
                )
                self.assertFalse(
                    support["physical_observability_verified"]
                )

    def test_11_zero_lidar_cannot_claim_current_support(self):
        row = self.by[tuple(EDGES)]
        self.assertIs(
            row["all_windows_have_current_lidar"], False
        )

        if row["solver_outcome"] == "ACCEPTED":
            self.assertEqual(
                row["windows_without_current_lidar"], 4
            )
            for window in row["support_windows"]:
                self.assertIs(
                    window["current_lidar_factor_available"],
                    False,
                )

    def test_12_finite_accepted_numerical_diagnostics(self):
        for row in self.rows:
            if row["solver_outcome"] != "ACCEPTED":
                continue

            self.assertTrue(math.isfinite(
                row["total_window_cost_diagnostic"]
            ))
            self.assertEqual(
                len(row["synthetic_final_position_m"]), 3
            )
            self.assertEqual(
                len(row["synthetic_state_sha256"]), 64
            )

    def test_13_baseline_matches_published_study(self):
        published = published_single_edge()
        self.assertEqual(
            self.by[()]["synthetic_state_sha256"],
            published["synthetic_state_sha256"],
        )

    def test_14_single_and_pair_parity(self):
        for removed, old in (
            ((EDGES[0],), published_single_edge(EDGES[0])),
            (PAIRS[0], published_pair(PAIRS[0])),
        ):
            new = self.by[removed]
            if len(removed) == 1:
                # R135-A15 returns only accepted solver records,
                # without the later solver_outcome field.
                self.assertNotIn("solver_outcome", old)
                self.assertEqual(
                    new["solver_outcome"],
                    "ACCEPTED",
                )
            else:
                # R135-A16 explicitly reports solver_outcome.
                self.assertEqual(
                    new["solver_outcome"],
                    old["solver_outcome"],
                )
            self.assertEqual(
                new["synthetic_state_sha256"],
                old["synthetic_state_sha256"],
            )

    def test_15_deterministic_repeat(self):
        removed = (EDGES[0], EDGES[1], EDGES[2])
        first = self.by[removed]
        repeat = run_case(removed)

        self.assertEqual(
            first["solver_outcome"],
            repeat["solver_outcome"],
        )
        self.assertEqual(
            first["synthetic_state_sha256"],
            repeat["synthetic_state_sha256"],
        )
        self.assertEqual(
            first["support_windows"],
            repeat["support_windows"],
        )

    def test_16_invalid_edge_types_are_blocked(self):
        invalid = (
            None,
            "all",
            [EDGES[0]],
            ((0, True),),
            ((False, 1),),
            ((0, 1.0),),
            ((0, [1]),),
            (EDGES[0], EDGES[0]),
            (EDGES[1], EDGES[0]),
            ((0, 4),),
        )

        for item in invalid:
            with self.subTest(item=item):
                with self.assertRaises(
                    SyntheticDropoutError
                ):
                    run_case(item)

    def test_17_strict_current_lidar_requirement(self):
        fixture, _ = make_fixture("clean")

        def no_lidar_factory(internal):
            self.assertIs(internal, fixture)
            inertial, lidar, counts = make_factors(internal)
            self.assertEqual(len(lidar), 7)
            metadata = dict(counts)
            metadata["lidar_factor_count"] = 0
            return inertial, {}, metadata

        with self.assertRaisesRegex(
            ValueError, "support unavailable"
        ):
            estimate_marginalized_with_support(
                fixture,
                factor_factory=no_lidar_factory,
                support_policy="require",
                require_active_lidar=True,
            )

    def test_18_scientific_denials_and_scope(self):
        for row in self.rows:
            self.assertEqual(row["schema"], SCHEMA)
            self.assertEqual(row["status"], STATUS)
            for key in DENIALS:
                self.assertIs(row[key], False, key)

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
            "analytic_15d_exhaustive_lidar_dropout_v1.py"
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
            "itertools",
            "trust_robot.analytic_inertial_15d",
            "trust_robot.analytic_preintegrated_fusion",
            "trust_robot.analytic_marginalized_fusion",
            "trust_robot.analytic_depth_camera_source_v1",
        })


if __name__ == "__main__":
    unittest.main(verbosity=2)
