import copy
import unittest

from trust_robot.synthetic_truth_consistency_v1 import (
    ToyConsistencyError,
    review_toy_consistency,
    summarize_toy_consistency,
    certify_physical_consistency,
)


def eye(n):
    return [
        [1.0 if i == j else 0.0 for j in range(n)]
        for i in range(n)
    ]


def truth(position=0):
    state = [0.0] * 15
    state[0] = position

    return {
        "source_kind": "SYNTHETIC_TRUTH_ONLY",
        "state_15": state,
        "reference_protocol": "DECLARED_TOY_KINEMATICS_V1",
    }


class ConsistencyTests(unittest.TestCase):

    def test_01_zero_nees(self):
        r = review_toy_consistency(
            [0] * 15, eye(15), truth()
        )
        self.assertEqual(r["toy_nees_15d"], 0)

    def test_02_unit_nees(self):
        r = review_toy_consistency(
            [0] * 15, eye(15), truth(1)
        )
        self.assertAlmostEqual(r["toy_nees_15d"], 1)

    def test_03_normalized_nees(self):
        r = review_toy_consistency(
            [0] * 15, eye(15), truth(1)
        )
        self.assertAlmostEqual(
            r["toy_normalized_nees_15d"], 1 / 15
        )

    def test_04_position_squared_error(self):
        r = review_toy_consistency(
            [0] * 15, eye(15), truth(2)
        )
        self.assertEqual(
            r["toy_position_squared_error"], 4
        )

    def test_05_aggregate_rmse(self):
        rows = [
            review_toy_consistency(
                [0] * 15, eye(15), truth(1)
            ),
            review_toy_consistency(
                [0] * 15, eye(15), truth(3)
            ),
        ]
        s = summarize_toy_consistency(rows)
        self.assertAlmostEqual(
            s["toy_position_rmse"], (5.0) ** 0.5
        )

    def test_06_determinism(self):
        a = review_toy_consistency(
            [0] * 15, eye(15), truth(1)
        )
        b = review_toy_consistency(
            [0] * 15,
            copy.deepcopy(eye(15)),
            copy.deepcopy(truth(1)),
        )
        self.assertEqual(a, b)

    def test_07_reject_fake_physical_truth(self):
        t = truth()
        t["source_kind"] = "PHYSICAL_REFERENCE"
        with self.assertRaises(ToyConsistencyError):
            review_toy_consistency([0] * 15, eye(15), t)

    def test_08_reject_extra_truth_field(self):
        t = truth()
        t["ground_truth_verified"] = True
        with self.assertRaises(ToyConsistencyError):
            review_toy_consistency([0] * 15, eye(15), t)

    def test_09_reject_singular_covariance(self):
        p = eye(15)
        p[0][0] = 0
        with self.assertRaises(ValueError):
            review_toy_consistency([0] * 15, p, truth())

    def test_10_reject_nonfinite_truth(self):
        t = truth()
        t["state_15"][0] = float("nan")
        with self.assertRaises(ValueError):
            review_toy_consistency([0] * 15, eye(15), t)

    def test_11_reject_empty_summary(self):
        with self.assertRaises(ToyConsistencyError):
            summarize_toy_consistency([])

    def test_12_no_statistical_calibration_claim(self):
        r = review_toy_consistency(
            [0] * 15, eye(15), truth()
        )
        self.assertFalse(
            r["statistical_calibration_established"]
        )
        self.assertFalse(
            r["physical_ground_truth_verified"]
        )

    def test_13_no_factor_admission(self):
        r = review_toy_consistency(
            [0] * 15, eye(15), truth()
        )
        self.assertEqual(r["real_factor_count"], 0)
        self.assertEqual(
            r["real_factor_admission"], "DENIED"
        )

    def test_14_physical_certification_denied(self):
        with self.assertRaises(ToyConsistencyError):
            certify_physical_consistency()


if __name__ == "__main__":
    unittest.main()
