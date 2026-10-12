import math
import unittest

import numpy as np

from trust_robot.clean_backbone import (
    CleanBackboneConfig,
    FixedCleanBackbone,
    PoseSE3,
    RelativePoseIncrement,
)
from trust_robot.factor_conditioning import (
    FactorConditioningContractError,
    assert_factor_scale_execution_authorized,
)
from trust_robot.auxiliary_consistency import (
    AuxiliaryConsistencyContractError,
    assert_consistency_execution_authorized,
)
from trust_robot.isaacsim_v15_odometry_chain import (
    BODY_FRAME,
    ODOM_FRAME,
    SOURCE,
    json_line,
    logical_time_ns,
    register_bounded,
)


class OdometryChainTests(unittest.TestCase):
    def setUp(self):
        self.cloud = np.array([
            [0., 0., 0.],
            [1., 0., 0.],
            [0., 1., 0.],
            [0., 0., 1.],
            [2., 1., 3.],
            [3., 2., 1.],
            [1., 3., 2.],
            [3., 1., 2.],
        ], dtype=np.float32)

    def test_identity_cloud_registration(self):
        result = register_bounded(self.cloud, self.cloud)
        pose = result.previous_lidar_T_current_lidar
        self.assertLess(
            math.dist(pose.translation_m, (0., 0., 0.)),
            1e-8,
        )

    def test_nontrivial_se3_pose_chain_composition(self):
        q = math.sqrt(0.5)
        rotation = PoseSE3(
            translation_m=(1., 2., 3.),
            quaternion_wxyz=(q, 0., 0., q),
        )
        step = PoseSE3(
            translation_m=(1., 0., 0.),
            quaternion_wxyz=(1., 0., 0., 0.),
        )

        config = CleanBackboneConfig(
            world_frame_id=ODOM_FRAME,
            body_frame_id=BODY_FRAME,
            relative_pose_source_id=SOURCE,
            initial_timestamp_ns=0,
            initial_pose_world_T_body=rotation,
        )
        backbone = FixedCleanBackbone(config)
        state = backbone.apply(RelativePoseIncrement(
            timestamp_ns=1,
            body_frame_id=BODY_FRAME,
            source_id=SOURCE,
            delta_prev_body_T_current_body=step,
        ))

        self.assertLess(
            math.dist(
                state.pose_world_T_body.translation_m,
                (1., 3., 3.),
            ),
            1e-10,
        )

    def test_invalid_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            logical_time_ns({"lidar_read_step_time_s": -1.})

    def test_simulation_step_not_physical_clock(self):
        self.assertEqual(
            logical_time_ns({"lidar_read_step_time_s": 0.5}),
            500_000_000,
        )

    def test_registration_invalid_points(self):
        bad = self.cloud.copy()
        bad[0, 0] = np.nan
        with self.assertRaises(ValueError):
            register_bounded(self.cloud, bad)

    def test_unfrozen_factor_weighting_blocked(self):
        with self.assertRaises(FactorConditioningContractError):
            assert_factor_scale_execution_authorized()

    def test_unfrozen_consistency_execution_blocked(self):
        with self.assertRaises(AuxiliaryConsistencyContractError):
            assert_consistency_execution_authorized()

    def test_nan_output_rejected(self):
        with self.assertRaises(ValueError):
            json_line({"x": float("nan")})


if __name__ == "__main__":
    unittest.main()
