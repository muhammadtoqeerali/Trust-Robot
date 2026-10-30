import copy
import unittest

from trust_robot.synthetic_15d_kalman_v1 import (
    SyntheticKalmanError,
    propose_toy_kalman_update,
    apply_physical_state_update,
)

from trust_robot.synthetic_15d_innovation_v1 import (
    SyntheticInnovationError,
)


def eye(n, value=1.0):
    return [
        [value if i == j else 0.0 for j in range(n)]
        for i in range(n)
    ]


def descriptor(value=1, kind="toy_position_xyz"):
    return {
        "source_kind": "SYNTHETIC_ONLY",
        "stream": "imu",
        "factor_kind": kind,
        "sequence": 0,
        "clock_domain": "synthetic_clock",
        "event_stamp_ns": 10**18,
        "measurement_xyz": [value, 0, 0],
        "noise_covariance_3x3": eye(3),
    }


def update(value=1):
    return propose_toy_kalman_update(
        [0.0] * 15,
        eye(15),
        descriptor(value),
    )


class KalmanTests(unittest.TestCase):

    def test_01_state_dimension(self):
        r = update()
        self.assertEqual(r["state_dimension"], 15)

    def test_02_posterior_mean(self):
        r = update()
        self.assertAlmostEqual(
            r["posterior_state_15"][0], 0.5
        )

    def test_03_full_innovation_nis(self):
        r = update()
        self.assertAlmostEqual(
            r["toy_full_innovation_nis"], 0.5
        )

    def test_04_different_from_measurement_only_nis(self):
        r = update()
        self.assertAlmostEqual(
            r["toy_measurement_only_nis"], 1.0
        )

    def test_05_posterior_variance(self):
        r = update()
        self.assertAlmostEqual(
            r["posterior_covariance_15x15"][0][0],
            0.5,
        )

    def test_06_unobserved_variance(self):
        r = update()
        self.assertAlmostEqual(
            r["posterior_covariance_15x15"][10][10],
            1.0,
        )

    def test_07_zero_residual(self):
        r = update(0)
        self.assertEqual(r["posterior_state_15"][0], 0)

    def test_08_high_innovation(self):
        r = update(3)
        self.assertAlmostEqual(
            r["toy_full_innovation_nis"], 4.5
        )

    def test_09_deterministic(self):
        self.assertEqual(
            update(),
            propose_toy_kalman_update(
                copy.deepcopy([0.0] * 15),
                copy.deepcopy(eye(15)),
                copy.deepcopy(descriptor()),
            ),
        )

    def test_10_reject_singular_prior(self):
        with self.assertRaises(SyntheticKalmanError):
            propose_toy_kalman_update(
                [0] * 15,
                eye(15, 0),
                descriptor(),
            )

    def test_11_reject_asymmetric_prior(self):
        p = eye(15)
        p[0][1] = 0.1
        with self.assertRaises(SyntheticKalmanError):
            propose_toy_kalman_update(
                [0] * 15, p, descriptor()
            )

    def test_12_reject_negative_variance(self):
        p = eye(15)
        p[0][0] = -1
        with self.assertRaises(SyntheticKalmanError):
            propose_toy_kalman_update(
                [0] * 15, p, descriptor()
            )

    def test_13_reject_physical_source(self):
        d = descriptor()
        d["source_kind"] = "PHYSICAL_UNQUALIFIED"

        with self.assertRaises(SyntheticInnovationError):
            propose_toy_kalman_update(
                [0] * 15, eye(15), d
            )

    def test_14_covariance_remains_symmetric(self):
        c = update()["posterior_covariance_15x15"]
        self.assertTrue(all(
            abs(c[i][j] - c[j][i]) < 1e-10
            for i in range(15)
            for j in range(15)
        ))

    def test_15_no_physical_admission(self):
        r = update()
        self.assertFalse(r["physical_state_estimated"])
        self.assertEqual(r["real_factor_count"], 0)
        self.assertEqual(
            r["real_factor_admission"], "DENIED"
        )

    def test_16_real_update_denied(self):
        with self.assertRaises(SyntheticKalmanError):
            apply_physical_state_update()


if __name__ == "__main__":
    unittest.main()
