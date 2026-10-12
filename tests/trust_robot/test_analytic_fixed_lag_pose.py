import inspect
import math
import unittest

import numpy as np
from scipy.spatial.transform import Rotation

from trust_robot.clean_backbone import PoseSE3
from trust_robot.factor_conditioning import (
    FactorConditioningContractError,
    assert_factor_scale_execution_authorized,
)
from trust_robot.auxiliary_consistency import (
    AuxiliaryConsistencyContractError,
    assert_consistency_execution_authorized,
)
from trust_robot.analytic_se3_geometry_benchmark import (
    make_fixture,
)
from trust_robot.analytic_fixed_lag_pose import (
    CONDITIONS,
    WINDOW_LENGTH,
    canonical,
    estimate_fixed_lag,
    execute,
    parameters_to_pose,
    pose_to_parameters,
    refine_window,
    relative_residual,
)


class FixedLagPoseTests(unittest.TestCase):
    def test_reference_cannot_enter_estimator_api(self):
        self.assertEqual(
            list(inspect.signature(
                estimate_fixed_lag
            ).parameters),
            ["clouds"],
        )

    def test_se3_parameter_round_trip(self):
        qx, qy, qz, qw = Rotation.from_euler(
            "xyz", [0.1, -0.2, 0.3]
        ).as_quat()

        p = PoseSE3(
            (1.0, 2.0, 3.0),
            (qw, qx, qy, qz),
        )

        restored = parameters_to_pose(
            pose_to_parameters(p)
        )

        self.assertLess(
            math.dist(
                p.translation_m, restored.translation_m
            ),
            1e-12,
        )

        self.assertLess(
            np.linalg.norm(
                relative_residual(
                    PoseSE3.identity(), p, restored
                )
            ),
            1e-12,
        )

    def test_relative_pose_convention(self):
        p0 = PoseSE3.identity()
        p1 = PoseSE3(
            (0.3, -0.2, 0.1),
            (1.0, 0.0, 0.0, 0.0),
        )
        p2 = PoseSE3(
            (0.5, 0.1, 0.2),
            (1.0, 0.0, 0.0, 0.0),
        )

        observation = p1.inverse().compose(p2)
        error = relative_residual(
            p1, p2, observation
        )

        self.assertLess(np.linalg.norm(error), 1e-12)

    def test_full_rank_two_pose_window(self):
        boundary = PoseSE3.identity()
        actual = PoseSE3(
            (0.2, -0.1, 0.3),
            (1.0, 0.0, 0.0, 0.0),
        )
        perturbed = PoseSE3(
            (0.3, -0.1, 0.2),
            (1.0, 0.0, 0.0, 0.0),
        )

        poses = {0: boundary, 1: perturbed}
        factor = {
            "previous": 0,
            "current": 1,
            "measurement": actual,
        }

        updated, status = refine_window(
            poses, 0, 1, [factor]
        )

        self.assertIsNotNone(updated)
        self.assertEqual(
            status["jacobian_rank"], 6
        )
        self.assertFalse(
            status[
                "local_rank_is_physical_sensor_observability"
            ]
        )
        self.assertLess(
            math.dist(
                updated[1].translation_m,
                actual.translation_m,
            ),
            1e-7,
        )

    def test_invalid_window_rejected(self):
        with self.assertRaises(ValueError):
            refine_window(
                {0: PoseSE3.identity()},
                0, WINDOW_LENGTH, [],
            )

    def test_estimator_rejects_single_scan(self):
        lanes, _, _ = make_fixture()

        with self.assertRaises(ValueError):
            estimate_fixed_lag(lanes["clean"][:1])

    def test_clean_fixture_pose_window(self):
        lanes, _, _ = make_fixture()

        poses, status = estimate_fixed_lag(
            lanes["clean"][:8]
        )

        self.assertEqual(len(poses), 8)
        self.assertEqual(status["window_count"], 7)
        self.assertEqual(
            status["optimized_window_count"], 7
        )
        self.assertTrue(all(
            r["reference_pose"] is None for r in poses
        ))

    def test_four_condition_development_run(self):
        _, result = execute()

        self.assertEqual(
            result["conditions"], list(CONDITIONS)
        )
        self.assertEqual(result["window_length"], 5)
        self.assertFalse(
            result["reference_passed_to_estimator"]
        )
        self.assertFalse(
            result[
                "full_multimodal_fixed_lag_state_estimator_complete"
            ]
        )

        clean = result["metrics_by_condition"]["clean"]
        self.assertLess(
            clean["rolling_window"][
                "fixture_translation_rmse_m"
            ],
            1e-5,
        )

    def test_frozen_trust_gates_not_bypassed(self):
        with self.assertRaises(
            FactorConditioningContractError
        ):
            assert_factor_scale_execution_authorized()

        with self.assertRaises(
            AuxiliaryConsistencyContractError
        ):
            assert_consistency_execution_authorized()

    def test_nonfinite_output_rejected(self):
        with self.assertRaises(ValueError):
            canonical({"x": float("nan")})


if __name__ == "__main__":
    unittest.main()
