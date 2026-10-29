import ast
import inspect
import math
import unittest
from collections import Counter
from pathlib import Path

from trust_robot.analytic_15d_joint_imu_lidar_stress_v1 import (
    SCHEMA,
    STATUS,
    DROPSETS,
    IMU_MODES,
    DENIALS,
    SyntheticDropoutError,
    manufactured_imu_intervention,
    run_case,
    run_matrix,
)

from trust_robot.analytic_15d_exhaustive_lidar_dropout_v1 import (
    run_case as published_clean_case,
)

from trust_robot.analytic_depth_camera_source_v1 import EDGES

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


class SyntheticJointIMULiDARStressTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.rows = run_matrix()
        cls.by = {
            (
                r["imu_mode"],
                tuple(tuple(e) for e in r["removed_edges"]),
            ): r
            for r in cls.rows
        }

    def test_01_frozen_modes(self):
        self.assertEqual(
            IMU_MODES, ("clean", "accel_bias")
        )

    def test_02_all_256_configurations(self):
        self.assertEqual(len(self.rows), 256)
        self.assertEqual(len(self.by), 256)

    def test_03_128_dropouts_per_imu_mode(self):
        counts = Counter(r["imu_mode"] for r in self.rows)
        self.assertEqual(
            counts, {"clean": 128, "accel_bias": 128}
        )

    def test_04_binomial_dropout_inventory(self):
        counts = Counter(len(x) for x in DROPSETS)
        self.assertEqual(
            tuple(counts[i] for i in range(8)),
            (1, 7, 21, 35, 35, 21, 7, 1),
        )

    def test_05_manufactured_accel_intervention(self):
        receipt = manufactured_imu_intervention()

        self.assertEqual(
            receipt["changed_imu_sample_indices"],
            [3, 4, 5],
        )

        self.assertEqual(
            receipt["original_imu_samples"], 8
        )

        self.assertFalse(
            receipt["physical_health_label_assigned"]
        )

        self.assertFalse(
            receipt["physical_calibration_verified"]
        )

    def test_06_clean_baseline_parity(self):
        for removed in (
            (),
            (EDGES[0],),
            tuple(EDGES),
        ):
            actual = self.by["clean", removed]
            previous = published_clean_case(removed)

            self.assertEqual(
                actual["solver_outcome"],
                previous["solver_outcome"],
            )

            self.assertEqual(
                actual["synthetic_state_sha256"],
                previous["synthetic_state_sha256"],
            )

    def test_07_both_full_lidar_baselines(self):
        for mode in IMU_MODES:
            row = self.by[mode, ()]

            self.assertEqual(
                row["solver_outcome"], "ACCEPTED"
            )

            self.assertEqual(
                row["remaining_lidar_factor_count"], 7
            )

            self.assertEqual(
                row[
                    "final_position_delta_from_same_imu_baseline_m"
                ],
                0.0,
            )

    def test_08_full_lidar_dropout_both_modes(self):
        for mode in IMU_MODES:
            row = self.by[mode, tuple(EDGES)]

            self.assertEqual(
                row["remaining_lidar_factor_count"], 0
            )

            self.assertFalse(
                row["all_windows_have_current_lidar"]
            )

            if row["solver_outcome"] == "ACCEPTED":
                self.assertEqual(
                    row["windows_without_current_lidar"], 4
                )

    def test_09_factor_accounting(self):
        for row in self.rows:
            self.assertEqual(
                row["removed_lidar_factor_count"]
                + row["remaining_lidar_factor_count"],
                7,
            )
            self.assertEqual(
                row["synthetic_imu_factor_count"], 4
            )

    def test_10_solver_outcomes_are_explicit(self):
        for row in self.rows:
            self.assertIn(
                row["solver_outcome"],
                ("ACCEPTED", "NUMERICALLY_REJECTED"),
            )

            if row["solver_outcome"] == "NUMERICALLY_REJECTED":
                self.assertTrue(
                    row["numerical_rejection"].startswith(
                        "Marginalized window solve failed at "
                    )
                )

    def test_11_numerical_support_invariants(self):
        for row in self.rows:
            if row["solver_outcome"] != "ACCEPTED":
                continue

            self.assertEqual(
                len(row["support_windows"]), 4
            )

            for window in row["support_windows"]:
                self.assertIn(
                    window["status"],
                    (
                        "NUMERICALLY_SUPPORTED",
                        "NUMERICALLY_UNAVAILABLE",
                    ),
                )

                self.assertFalse(
                    window["physical_observability_verified"]
                )

    def test_12_accepted_diagnostics_are_finite(self):
        for row in self.rows:
            if row["solver_outcome"] != "ACCEPTED":
                continue

            self.assertTrue(math.isfinite(
                row["total_window_cost_diagnostic"]
            ))

            self.assertTrue(math.isfinite(
                row[
                    "final_position_delta_from_same_imu_baseline_m"
                ]
            ))

            self.assertTrue(math.isfinite(
                row[
                    "final_position_delta_from_clean_baseline_m"
                ]
            ))

    def test_13_imu_mode_provenance(self):
        for row in self.rows:
            self.assertIs(
                row["manufactured_accel_bias_injected"],
                row["imu_mode"] == "accel_bias",
            )

    def test_14_pairing_all_dropout_sets(self):
        for removed in DROPSETS:
            for mode in IMU_MODES:
                self.assertIn((mode, removed), self.by)

    def test_15_repeatability(self):
        removed = tuple(EDGES)
        first = self.by["accel_bias", removed]
        second = run_case(removed, "accel_bias")

        self.assertEqual(
            first["solver_outcome"],
            second["solver_outcome"],
        )

        self.assertEqual(
            first["synthetic_state_sha256"],
            second["synthetic_state_sha256"],
        )

        self.assertEqual(
            first["support_windows"],
            second["support_windows"],
        )

    def test_16_invalid_inputs_rejected(self):
        invalid = (
            (None, "clean"),
            ([EDGES[0]], "clean"),
            (((0, True),), "clean"),
            (((0, 1.0),), "clean"),
            ((EDGES[0], EDGES[0]), "clean"),
            ((EDGES[1], EDGES[0]), "clean"),
            ((), True),
            ((), None),
            ((), "recorded"),
            ((), "lidar_dropout"),
        )

        for removed, mode in invalid:
            with self.subTest(removed=removed, mode=mode):
                with self.assertRaises(
                    SyntheticDropoutError
                ):
                    run_case(removed, mode)

    def test_17_health_and_weighting_denials(self):
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

        for row in self.rows:
            for key in DENIALS:
                self.assertIs(row[key], False, key)

    def test_18_schema_and_import_scope(self):
        for row in self.rows:
            self.assertEqual(row["schema"], SCHEMA)
            self.assertEqual(row["status"], STATUS)

        self.assertEqual(
            tuple(inspect.signature(run_case).parameters),
            ("removed_edges", "imu_mode"),
        )

        self.assertEqual(
            len(inspect.signature(run_matrix).parameters),
            0,
        )

        path = ROOT / (
            "src/trust_robot/"
            "analytic_15d_joint_imu_lidar_stress_v1.py"
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
            "itertools",
            "trust_robot.analytic_inertial_15d",
            "trust_robot.analytic_preintegrated_fusion",
            "trust_robot.analytic_marginalized_fusion",
            "trust_robot.analytic_depth_camera_source_v1",
        })


if __name__ == "__main__":
    unittest.main(verbosity=2)
