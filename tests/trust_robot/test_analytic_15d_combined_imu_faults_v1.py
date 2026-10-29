import ast
import inspect
import math
import unittest
from pathlib import Path

import numpy as np

from trust_robot.analytic_15d_combined_imu_faults_v1 import (
    SCHEMA,
    STATUS,
    IMU_MODES,
    SCHEDULES,
    DENIALS,
    LongHorizonStressError,
    make_condition,
    verify_manufactured_interventions,
    verify_combined_intervention,
    run_case,
    run_matrix,
)

from trust_robot.analytic_15d_long_horizon_joint_stress_v1 import (
    run_case as published_case,
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


class CombinedIMUFaultTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.rows = run_matrix()
        cls.by = {
            (r["imu_mode"], r["outage_name"]): r
            for r in cls.rows
        }

    def test_01_four_modes(self):
        self.assertEqual(
            IMU_MODES,
            ("clean", "accel_bias", "gyro_bias",
             "combined_bias"),
        )

    def test_02_five_schedules(self):
        self.assertEqual(len(SCHEDULES), 5)

    def test_03_twenty_configurations(self):
        self.assertEqual(len(self.rows), 20)
        self.assertEqual(len(self.by), 20)

    def test_04_all_cartesian_combinations(self):
        self.assertEqual(
            set(self.by),
            {
                (m, outage)
                for m in IMU_MODES
                for outage in SCHEDULES
            },
        )

    def test_05_original_imu_receipt(self):
        r = verify_manufactured_interventions()
        self.assertEqual(
            r["accelerometer_changed_samples"],
            list(range(6, 15)),
        )
        self.assertEqual(
            r["gyroscope_changed_samples"],
            list(range(8, 18)),
        )

    def test_06_combined_imu_receipt(self):
        r = verify_combined_intervention()
        self.assertEqual(
            r["accel_sample_indices"],
            list(range(6, 15)),
        )
        self.assertEqual(
            r["gyro_sample_indices"],
            list(range(8, 18)),
        )
        self.assertFalse(r["health_label_generated"])
        self.assertFalse(r["factor_weights_modified"])

    def test_07_combined_matches_frozen_fields(self):
        a = make_condition("accel_bias", "none")
        g = make_condition("gyro_bias", "none")
        b = make_condition("combined_bias", "none")
        for i in range(22):
            self.assertEqual(
                b["imu"][i]["specific_force_m_s2"],
                a["imu"][i]["specific_force_m_s2"],
            )
            self.assertEqual(
                b["imu"][i]["gyro_rad_s"],
                g["imu"][i]["gyro_rad_s"],
            )

    def test_08_combined_does_not_change_scans(self):
        a = make_condition("clean", "none")
        b = make_condition("combined_bias", "none")
        self.assertTrue(all(
            np.array_equal(x, y)
            for x, y in zip(a["scans"], b["scans"])
        ))

    def test_09_outage_provenance(self):
        a = make_condition("combined_bias", "none")
        b = make_condition("combined_bias", "mid_six")
        self.assertEqual(a["imu"], b["imu"])
        self.assertEqual(
            [
                i for i, available in
                enumerate(b["available"])
                if not available
            ],
            list(SCHEDULES["mid_six"]),
        )

    def test_10_original_published_parity(self):
        for mode, outage in (
            ("clean", "none"),
            ("accel_bias", "mid_six"),
            ("gyro_bias", "complete"),
        ):
            current = self.by[mode, outage]
            published = published_case(mode, outage)
            self.assertEqual(
                current["solver_outcome"],
                published["solver_outcome"],
            )
            self.assertEqual(
                current["synthetic_state_sha256"],
                published["synthetic_state_sha256"],
            )

    def test_11_all_factor_counts(self):
        for row in self.rows:
            self.assertEqual(row["imu_factor_count"], 11)
            self.assertEqual(
                row["unique_imu_sample_count"], 22
            )
            self.assertLessEqual(
                row["lidar_factor_count"], 21
            )

    def test_12_full_lidar_outages(self):
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

    def test_13_solver_outcomes(self):
        for row in self.rows:
            self.assertIn(
                row["solver_outcome"],
                ("ACCEPTED", "NUMERICALLY_REJECTED"),
            )

    def test_14_support_accounting(self):
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

    def test_15_finite_accepted_results(self):
        for row in self.rows:
            if row["solver_outcome"] != "ACCEPTED":
                continue
            self.assertTrue(math.isfinite(
                row["total_window_cost_diagnostic"]
            ))
            self.assertEqual(
                len(row["synthetic_state_sha256"]), 64
            )

    def test_16_combined_provenance_flag(self):
        for row in self.rows:
            self.assertIs(
                row["simultaneous_manufactured_imu_faults"],
                row["imu_mode"] == "combined_bias",
            )

    def test_17_interaction_is_combined_only(self):
        for row in self.rows:
            value = row[
                "synthetic_joint_interaction_norm_m"
            ]
            if row["imu_mode"] != "combined_bias":
                self.assertIsNone(value)
            elif value is not None:
                self.assertTrue(math.isfinite(value))
                self.assertGreaterEqual(value, 0.0)

    def test_18_interaction_arithmetic(self):
        for outage in SCHEDULES:
            c, a, g, b = [
                self.by[mode, outage]
                for mode in IMU_MODES
            ]
            if not all(
                r["solver_outcome"] == "ACCEPTED"
                for r in (c, a, g, b)
            ):
                self.assertIsNone(
                    b["synthetic_joint_interaction_norm_m"]
                )
                continue
            vector = (
                np.asarray(
                    b["synthetic_final_position_m"]
                )
                - np.asarray(
                    a["synthetic_final_position_m"]
                )
                - np.asarray(
                    g["synthetic_final_position_m"]
                )
                + np.asarray(
                    c["synthetic_final_position_m"]
                )
            )
            self.assertAlmostEqual(
                float(np.linalg.norm(vector)),
                b["synthetic_joint_interaction_norm_m"],
                places=12,
            )

    def test_19_invalid_inputs_and_closed_gates(self):
        invalid = (
            ("recorded", "none"),
            (True, "none"),
            ("combined_bias", "unknown"),
            ("combined_bias", None),
            (None, "complete"),
        )
        for mode, outage in invalid:
            with self.subTest(mode=mode, outage=outage):
                with self.assertRaises(
                    LongHorizonStressError
                ):
                    run_case(mode, outage)

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

    def test_20_denials_repeatability_and_scope(self):
        for row in self.rows:
            self.assertEqual(row["schema"], SCHEMA)
            self.assertEqual(row["status"], STATUS)
            for key in DENIALS:
                self.assertIs(row[key], False, key)

        r = run_case("combined_bias", "complete")
        old = self.by["combined_bias", "complete"]

        self.assertEqual(
            r["solver_outcome"],
            old["solver_outcome"],
        )
        self.assertEqual(
            r["synthetic_state_sha256"],
            old["synthetic_state_sha256"],
        )

        self.assertEqual(
            tuple(inspect.signature(run_case).parameters),
            ("imu_mode", "outage_name"),
        )

        path = ROOT / (
            "src/trust_robot/"
            "analytic_15d_combined_imu_faults_v1.py"
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
            "trust_robot.analytic_marginalized_horizon",
            "trust_robot.analytic_inertial_15d",
            "trust_robot.analytic_marginalized_fusion",
        })


if __name__ == "__main__":
    unittest.main(verbosity=2)
