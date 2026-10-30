"""Synthetic toy innovation tests; never access physical data."""

import copy
import unittest

from trust_robot.synthetic_15d_innovation_v1 import (
    SyntheticInnovationError,
    innovation,
    make_real_factor,
)


def factor(
    kind="toy_position_xyz",
    stream="lidar",
    measurement=(1, 0, 0),
):
    return {
        "source_kind": "SYNTHETIC_ONLY",
        "stream": stream,
        "factor_kind": kind,
        "sequence": 0,
        "clock_domain": "synthetic_clock",
        "event_stamp_ns": 10**18,
        "measurement_xyz": list(measurement),
        "noise_covariance_3x3": [
            [1 if i == j else 0 for j in range(3)]
            for i in range(3)
        ],
    }


class ToyInnovationTests(unittest.TestCase):

    def test_01_zero_residual(self):
        f = factor(measurement=(0, 0, 0))
        r = innovation([0] * 15, f)
        self.assertEqual(r["normalized_innovation_squared"], 0)

    def test_02_nis(self):
        r = innovation([0] * 15, factor())
        self.assertAlmostEqual(
            r["normalized_innovation_squared"], 1
        )

    def test_03_position_jacobian(self):
        h = innovation(
            [0] * 15, factor()
        )["jacobian_3x15"]
        self.assertEqual(h[0][0], 1)
        self.assertEqual(h[0][3], 0)

    def test_04_velocity_jacobian(self):
        h = innovation(
            [0] * 15, factor("toy_velocity_xyz")
        )["jacobian_3x15"]
        self.assertEqual(h[1][4], 1)

    def test_05_attitude_jacobian(self):
        h = innovation(
            [0] * 15, factor("toy_attitude_xyz")
        )["jacobian_3x15"]
        self.assertEqual(h[2][8], 1)

    def test_06_state_subtraction(self):
        x = [0] * 15
        x[0] = 2
        r = innovation(x, factor())
        self.assertEqual(r["residual_xyz"], [-1, 0, 0])

    def test_07_noise_scaling(self):
        f = factor()
        f["noise_covariance_3x3"][0][0] = 4
        r = innovation([0] * 15, f)
        self.assertAlmostEqual(
            r["normalized_innovation_squared"], .25
        )

    def test_08_correlated_noise(self):
        f = factor(measurement=(1, 1, 0))
        f["noise_covariance_3x3"][0][1] = .5
        f["noise_covariance_3x3"][1][0] = .5
        r = innovation([0] * 15, f)
        self.assertAlmostEqual(
            r["normalized_innovation_squared"], 4 / 3
        )

    def test_09_determinism(self):
        self.assertEqual(
            innovation([0] * 15, factor()),
            innovation([0] * 15, copy.deepcopy(factor())),
        )

    def test_10_reject_physical_source(self):
        f = factor()
        f["source_kind"] = "PHYSICAL"
        with self.assertRaises(SyntheticInnovationError):
            innovation([0] * 15, f)

    def test_11_reject_extra_payload(self):
        f = factor()
        f["raw_lidar_points"] = [1]
        with self.assertRaises(SyntheticInnovationError):
            innovation([0] * 15, f)

    def test_12_reject_bad_state(self):
        with self.assertRaises(SyntheticInnovationError):
            innovation([0] * 14, factor())

    def test_13_reject_singular_covariance(self):
        f = factor()
        f["noise_covariance_3x3"][2][2] = 0
        with self.assertRaises(SyntheticInnovationError):
            innovation([0] * 15, f)

    def test_14_reject_asymmetric_covariance(self):
        f = factor()
        f["noise_covariance_3x3"][0][1] = .1
        with self.assertRaises(SyntheticInnovationError):
            innovation([0] * 15, f)

    def test_15_reject_bool_timestamp(self):
        f = factor()
        f["event_stamp_ns"] = True
        with self.assertRaises(SyntheticInnovationError):
            innovation([0] * 15, f)

    def test_16_reject_nonfinite_measurement(self):
        f = factor()
        f["measurement_xyz"][0] = float("nan")
        with self.assertRaises(SyntheticInnovationError):
            innovation([0] * 15, f)

    def test_17_factor_denied(self):
        with self.assertRaises(SyntheticInnovationError):
            make_real_factor()

    def test_18_no_estimator_or_real_factors(self):
        result = innovation([0] * 15, factor())
        self.assertFalse(result["estimator_invoked"])
        self.assertEqual(result["real_factor_count"], 0)
        self.assertEqual(
            result["m2dgr_gates"], "11_CLOSED"
        )


if __name__ == "__main__":
    unittest.main()
