import copy
import math
import unittest

from trust_robot.se3_covariance_propagation_v1 import (
    CovarianceError,
    check_pose,
    compose_independent_poses,
    invert_uncertain_pose,
    admit_real_covariance,
)


def eye(n, variance=0):
    return [
        [variance if i == j else 0.0 for j in range(n)]
        for i in range(n)
    ]


def pose(target="base", source="camera",
         translation=(1, 0, 0), variance=0):
    t = eye(4)
    t[3][3] = 1.0
    for i in range(3):
        t[i][i] = 1.0
        t[i][3] = translation[i]

    return {
        "target_frame": target,
        "source_frame": source,
        "T_target_source": t,
        "covariance_6x6": eye(6, variance),
        "origin": "SYNTHETIC_ONLY",
    }


class SE3CovarianceTests(unittest.TestCase):

    def test_01_valid_pose(self):
        self.assertEqual(len(check_pose(pose())), 2)

    def test_02_reject_implicit_independence(self):
        with self.assertRaises(CovarianceError):
            compose_independent_poses(
                pose(), pose("camera", "lidar")
            )

    def test_03_chain_translation(self):
        r = compose_independent_poses(
            pose(),
            pose("camera", "lidar", (0, 2, 0)),
            independent_errors=True,
        )
        t = r["pose"]["T_target_source"]
        self.assertAlmostEqual(t[0][3], 1)
        self.assertAlmostEqual(t[1][3], 2)

    def test_04_invert_translation(self):
        r = invert_uncertain_pose(pose())
        self.assertAlmostEqual(
            r["pose"]["T_target_source"][0][3], -1
        )

    def test_05_identity_covariance(self):
        r = compose_independent_poses(
            pose(variance=0),
            pose("camera", "lidar", variance=0),
            independent_errors=True,
        )
        self.assertEqual(
            r["pose"]["covariance_6x6"], eye(6)
        )

    def test_06_variance_addition(self):
        a = pose(translation=(0, 0, 0), variance=2)
        b = pose("camera", "lidar", (0, 0, 0), 3)
        r = compose_independent_poses(
            a, b, independent_errors=True
        )
        self.assertAlmostEqual(
            r["pose"]["covariance_6x6"][0][0], 5
        )

    def test_07_adjoint_translation_rotation_coupling(self):
        a = pose(variance=0)
        b = pose("camera", "lidar", (0, 0, 0), 0)
        b["covariance_6x6"][5][5] = 1.0

        r = compose_independent_poses(
            a, b, independent_errors=True
        )
        c = r["pose"]["covariance_6x6"]

        self.assertAlmostEqual(c[1][1], 1)
        self.assertAlmostEqual(c[1][5], -1)

    def test_08_rotation_composition(self):
        a = pose()
        a["T_target_source"][0][0] = 0.0
        a["T_target_source"][0][1] = -1.0
        a["T_target_source"][1][0] = 1.0
        a["T_target_source"][1][1] = 0.0

        b = pose("camera", "lidar")
        r = compose_independent_poses(
            a, b, independent_errors=True
        )

        self.assertAlmostEqual(
            r["pose"]["T_target_source"][1][3], 1
        )

    def test_09_reject_bad_frames(self):
        with self.assertRaises(CovarianceError):
            compose_independent_poses(
                pose(), pose("wrong", "lidar"),
                independent_errors=True,
            )

    def test_10_reject_reflection(self):
        p = pose()
        p["T_target_source"][0][0] = -1
        with self.assertRaises(CovarianceError):
            check_pose(p)

    def test_11_reject_boolean(self):
        p = pose()
        p["covariance_6x6"][0][0] = True
        with self.assertRaises(CovarianceError):
            check_pose(p)

    def test_12_reject_negative_covariance(self):
        p = pose(variance=1)
        p["covariance_6x6"][0][0] = -1
        with self.assertRaises(CovarianceError):
            check_pose(p)

    def test_13_reject_asymmetry(self):
        p = pose(variance=1)
        p["covariance_6x6"][0][1] = 0.5
        with self.assertRaises(CovarianceError):
            check_pose(p)

    def test_14_inverse_determinism(self):
        self.assertEqual(
            invert_uncertain_pose(pose(variance=1)),
            invert_uncertain_pose(
                copy.deepcopy(pose(variance=1))
            ),
        )

    def test_15_no_physical_admission(self):
        r = invert_uncertain_pose(pose())
        self.assertFalse(
            r["physical_calibration_qualified"]
        )
        self.assertEqual(r["real_factor_count"], 0)
        self.assertEqual(
            r["real_factor_admission"], "DENIED"
        )

    def test_16_admission_refused(self):
        with self.assertRaises(CovarianceError):
            admit_real_covariance(pose())


if __name__ == "__main__":
    unittest.main()
