import ast
import inspect
import math
import unittest
from pathlib import Path

import numpy as np

from trust_robot.analytic_15d_long_horizon_joint_stress_v1 import (
    SCHEMA,
    STATUS,
    IMU_MODES,
    OUTAGE_SCHEDULES,
    SCHEDULES,
    DENIALS,
    LongHorizonStressError,
    make_condition,
    verify_manufactured_interventions,
    run_case,
    run_matrix,
)

from trust_robot.analytic_marginalized_horizon import (
    NODE_FRAMES,
    long_fixture,
    long_factors,
)

from trust_robot.analytic_marginalized_fusion import (
    estimate_marginalized_with_support,
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


class LongHorizonJointStressTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.rows = run_matrix()
        cls.by = {
            (r["imu_mode"], r["outage_name"]): r
            for r in cls.rows
        }

    def test_01_twelve_node_chronology(self):
        self.assertEqual(
            NODE_FRAMES,
            tuple(range(0, 24, 2)),
        )

    def test_02_three_imu_modes(self):
        self.assertEqual(
            IMU_MODES,
            ("clean", "accel_bias", "gyro_bias"),
        )

    def test_03_five_outage_schedules(self):
        self.assertEqual(len(OUTAGE_SCHEDULES), 5)
        self.assertEqual(len(SCHEDULES), 5)
        self.assertEqual(SCHEDULES["none"], ())
        self.assertEqual(
            SCHEDULES["complete"], NODE_FRAMES
        )

    def test_04_fifteen_unique_configurations(self):
        self.assertEqual(len(self.rows), 15)
        self.assertEqual(len(self.by), 15)

    def test_05_manufactured_bias_receipt(self):
        receipt = verify_manufactured_interventions()

        self.assertEqual(
            receipt["accelerometer_changed_samples"],
            list(range(6, 15)),
        )
        self.assertEqual(
            receipt["gyroscope_changed_samples"],
            list(range(8, 18)),
        )

    def test_06_outage_affects_availability_only(self):
        clean = make_condition("clean", "none")
        outage = make_condition("clean", "mid_six")

        self.assertEqual(
            clean["imu"], outage["imu"]
        )

        self.assertTrue(all(
            np.array_equal(a, b)
            for a, b in zip(
                clean["scans"], outage["scans"]
            )
        ))

        self.assertEqual(
            [
                i for i, available in enumerate(
                    outage["available"]
                )
                if not available
            ],
            list(SCHEDULES["mid_six"]),
        )

    def test_07_imu_sample_inventory(self):
        for row in self.rows:
            self.assertEqual(
                row["imu_factor_count"], 11
            )
            self.assertEqual(
                row["unique_imu_sample_count"], 22
            )

    def test_08_lidar_factor_inventory(self):
        for row in self.rows:
            edges = {
                tuple(e) for e in row["lidar_edge_keys"]
            }

            self.assertEqual(
                len(edges),
                row["lidar_factor_count"],
            )
            self.assertLessEqual(len(edges), 21)

    def test_09_complete_outage_no_lidar(self):
        for mode in IMU_MODES:
            row = self.by[mode, "complete"]

            self.assertEqual(
                row["lidar_factor_count"], 0
            )

            if row["solver_outcome"] == "ACCEPTED":
                self.assertEqual(
                    row["windows_without_current_lidar"],
                    11,
                )

    def test_10_solver_outcomes_explicit(self):
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

    def test_11_accepted_schur_accounting(self):
        for row in self.rows:
            if row["solver_outcome"] != "ACCEPTED":
                continue

            self.assertEqual(
                row["accepted_window_count"], 11
            )
            self.assertEqual(
                row["schur_elimination_count"], 10
            )
            self.assertEqual(
                len(row["support_windows"]), 11
            )

    def test_12_numerical_support_separate(self):
        for row in self.rows:
            if row["solver_outcome"] != "ACCEPTED":
                continue

            for window in row["support_windows"]:
                self.assertIn(
                    window["status"],
                    (
                        "NUMERICALLY_SUPPORTED",
                        "NUMERICALLY_UNAVAILABLE",
                    ),
                )

                self.assertEqual(
                    window["current_lidar_factor_available"],
                    window["active_lidar_factor_count"] > 0,
                )

    def test_13_finite_solver_diagnostics(self):
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

    def test_14_clean_baseline_published_parity(self):
        fixture, reference = long_fixture("clean")
        del reference

        records, audit = estimate_marginalized_with_support(
            fixture,
            node_frames=NODE_FRAMES,
            factor_factory=long_factors,
            support_policy="report",
        )

        self.assertEqual(len(records), 12)
        self.assertEqual(
            audit["accepted_window_count"], 11
        )

        import hashlib
        import json

        digest = hashlib.sha256(
            json.dumps(
                records,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()

        self.assertEqual(
            digest,
            self.by["clean", "none"][
                "synthetic_state_sha256"
            ],
        )

    def test_15_repeatability(self):
        original = self.by["accel_bias", "mid_four"]
        repeat = run_case("accel_bias", "mid_four")

        self.assertEqual(
            original["solver_outcome"],
            repeat["solver_outcome"],
        )

        self.assertEqual(
            original["synthetic_state_sha256"],
            repeat["synthetic_state_sha256"],
        )

        self.assertEqual(
            original["support_windows"],
            repeat["support_windows"],
        )

    def test_16_strict_current_lidar_guard(self):
        fixture = make_condition("clean", "complete")

        with self.assertRaisesRegex(
            ValueError,
            "support unavailable",
        ):
            estimate_marginalized_with_support(
                fixture,
                node_frames=NODE_FRAMES,
                factor_factory=long_factors,
                support_policy="require",
                require_active_lidar=True,
            )

    def test_17_baseline_relative_diagnostics(self):
        for mode in IMU_MODES:
            row = self.by[mode, "none"]

            self.assertEqual(
                row["delta_from_same_imu_baseline_m"],
                0.0,
            )

        for row in self.rows:
            if row["solver_outcome"] == "ACCEPTED":
                self.assertTrue(math.isfinite(
                    row[
                        "delta_from_same_imu_baseline_m"
                    ]
                ))
                self.assertTrue(math.isfinite(
                    row[
                        "delta_from_clean_full_lidar_baseline_m"
                    ]
                ))

    def test_18_invalid_conditions_denied(self):
        invalid = (
            ("real", "none"),
            ("lidar_outage", "none"),
            ("clean", "unknown"),
            (None, "none"),
            ("clean", None),
            (True, "none"),
            ("clean", True),
        )

        for mode, outage in invalid:
            with self.subTest(mode=mode, outage=outage):
                with self.assertRaises(
                    LongHorizonStressError
                ):
                    run_case(mode, outage)

    def test_19_scientific_denials(self):
        for row in self.rows:
            self.assertEqual(row["schema"], SCHEMA)
            self.assertEqual(row["status"], STATUS)

            for key in DENIALS:
                self.assertIs(row[key], False, key)

        with self.assertRaises(
            HealthModelInterfaceError
        ):
            assert_inference_authorized()

        with self.assertRaises(
            HealthModelInterfaceError
        ):
            assert_training_authorized()

        with self.assertRaises(
            FactorConditioningContractError
        ):
            assert_factor_scale_execution_authorized()

    def test_20_api_and_import_scope(self):
        self.assertEqual(
            tuple(inspect.signature(
                run_case
            ).parameters),
            ("imu_mode", "outage_name"),
        )

        self.assertEqual(
            len(inspect.signature(
                run_matrix
            ).parameters),
            0,
        )

        path = ROOT / (
            "src/trust_robot/"
            "analytic_15d_long_horizon_joint_stress_v1.py"
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
            "trust_robot.analytic_marginalized_horizon",
            "trust_robot.analytic_inertial_15d",
            "trust_robot.analytic_marginalized_fusion",
        })


if __name__ == "__main__":
    unittest.main(verbosity=2)
