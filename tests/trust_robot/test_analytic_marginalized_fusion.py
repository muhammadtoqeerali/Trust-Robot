import inspect
import unittest

import numpy as np

from trust_robot.analytic_inertial_15d import (
    make_fixture,
)
from trust_robot.analytic_preintegrated_fusion import (
    make_factors,
)
from trust_robot.analytic_marginalized_fusion import (
    CONDITIONS,
    NODE_FRAMES,
    active_factors,
    canonical,
    estimate_marginalized,
    execute,
)


class MarginalizedFusionTests(unittest.TestCase):

    def setUp(self):
        self.fixture, self.truth = make_fixture(
            "clean"
        )

    def test_reference_excluded_from_estimator_api(self):
        signature = inspect.signature(estimate_marginalized)
        parameters = list(signature.parameters.values())

        self.assertEqual(
            [p.name for p in parameters],
            ["fixture", "node_frames", "factor_factory"],
        )

        self.assertEqual(
            parameters[0].kind,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )
        self.assertIs(
            parameters[0].default,
            inspect.Parameter.empty,
        )

        for parameter in parameters[1:]:
            self.assertEqual(
                parameter.kind,
                inspect.Parameter.KEYWORD_ONLY,
            )

        self.assertEqual(
            parameters[1].default,
            NODE_FRAMES,
        )
        self.assertIs(
            parameters[2].default,
            make_factors,
        )

        self.assertNotIn("truth", signature.parameters)
        self.assertNotIn("reference", signature.parameters)
        self.assertNotIn("truth", self.fixture)

    def test_factor_selection_excludes_consumed(self):
        factors = {
            (0, 1): "a",
            (0, 2): "b",
            (1, 2): "c",
            (2, 3): "d",
        }

        selected = active_factors(
            factors,
            [1, 2, 3],
            {(0, 1), (1, 2)},
        )

        self.assertEqual(
            list(selected),
            [(2, 3)],
        )

    def test_clean_solver_integrates_schur_prior(self):
        records, audit = estimate_marginalized(
            self.fixture
        )

        self.assertEqual(len(records), 5)
        self.assertEqual(
            audit["accepted_window_count"], 4
        )
        self.assertEqual(
            audit["schur_elimination_count"], 3
        )
        self.assertEqual(
            audit["final_live_nodes"], [3, 4]
        )
        self.assertEqual(
            audit["final_prior_nodes"], [3, 4]
        )

    def test_imu_factors_consumed_once(self):
        _, audit = estimate_marginalized(
            self.fixture
        )

        consumed = {
            tuple(x)
            for x in audit["consumed_imu_keys"]
        }
        remaining = {
            tuple(x)
            for x in audit["remaining_imu_keys"]
        }

        self.assertFalse(
            consumed & remaining
        )
        self.assertEqual(
            consumed | remaining,
            {(0, 1), (1, 2), (2, 3), (3, 4)},
        )
        self.assertEqual(
            len(consumed), 3
        )

    def test_lidar_factors_not_double_counted(self):
        factors, lidar, _ = make_factors(
            self.fixture
        )
        self.assertEqual(len(lidar), 7)

        _, audit = estimate_marginalized(
            self.fixture
        )

        consumed = {
            tuple(x)
            for x in audit["consumed_lidar_keys"]
        }
        remaining = {
            tuple(x)
            for x in audit["remaining_lidar_keys"]
        }

        self.assertFalse(
            consumed & remaining
        )
        self.assertEqual(
            consumed | remaining,
            set(lidar),
        )

    def test_dropouts_preserve_measurement_accounting(self):
        fixture, _ = make_fixture(
            "lidar_dropout"
        )

        _, lidar, _ = make_factors(
            fixture
        )
        _, audit = estimate_marginalized(
            fixture
        )

        self.assertEqual(len(lidar), 3)
        self.assertEqual(
            len(audit["consumed_lidar_keys"])
            + len(audit["remaining_lidar_keys"]),
            3,
        )

        self.assertEqual(
            audit["schur_elimination_count"], 3
        )

    def test_departing_states_have_no_future_factors(self):
        _, audit = estimate_marginalized(
            self.fixture
        )

        for event in audit["eliminations"]:
            departing = event["eliminated_node"]

            for key in (
                event["consumed_imu_factor_keys"]
                + event["consumed_lidar_factor_keys"]
            ):
                self.assertIn(departing, key)

    def test_all_states_remain_finite(self):
        records, _ = estimate_marginalized(
            self.fixture
        )

        for index, row in enumerate(records):
            self.assertEqual(
                row["node_index"], index
            )
            self.assertEqual(
                row["source_frame_index"],
                NODE_FRAMES[index],
            )

            self.assertEqual(
                row["state_dimension"], 15
            )
            self.assertIsNone(
                row["reference_pose"]
            )

            for key in (
                "position_m",
                "velocity_m_s",
                "gyro_bias_rad_s",
                "accel_bias_m_s2",
                "orientation_quaternion_wxyz",
            ):
                self.assertTrue(
                    np.isfinite(row[key]).all()
                )

    def test_three_conditions_and_scientific_limits(self):
        _, result = execute()

        self.assertEqual(
            result["conditions"],
            list(CONDITIONS),
        )
        self.assertTrue(
            result["factor_ownership_checked"]
        )
        self.assertTrue(
            result["schur_marginalization_integrated"]
        )

        self.assertFalse(
            result["physical_observability_proven"]
        )
        self.assertFalse(
            result["posterior_consistency_proven"]
        )
        self.assertFalse(
            result["full_trust_robot_system_complete"]
        )

    def test_nonfinite_output_rejected(self):
        with self.assertRaises(ValueError):
            canonical({
                "invalid": float("nan")
            })


if __name__ == "__main__":
    unittest.main()
