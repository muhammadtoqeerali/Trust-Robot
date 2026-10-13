"""Regression tests for linearized estimator support diagnostics."""
import unittest

import numpy as np

from trust_robot.analytic_factor_support import (
    FactorSupportError,
    analyze_factor_support,
    make_linear_factor,
)


def f(name, J, *ids):
    return make_linear_factor(name, ids, J)


class FactorSupportTests(unittest.TestCase):

    def test_empty_ledger_unavailable(self):
        out = analyze_factor_support(15, [])
        self.assertEqual(out["status"], "NUMERICALLY_UNAVAILABLE")
        self.assertEqual(out["nullity"], 15)

    def test_full_rank_with_anchor(self):
        factors = [
            f("anchor", np.eye(3), "anchor-source"),
        ]
        out = analyze_factor_support(3, factors)
        self.assertEqual(out["status"], "NUMERICALLY_SUPPORTED")
        self.assertEqual(out["numerical_rank"], 3)
        self.assertEqual(out["nullity"], 0)

    def test_gauge_without_anchor(self):
        J = np.array([[-1.0, 1.0]])
        out = analyze_factor_support(
            2, [f("relative", J, "relative-observation")]
        )
        self.assertEqual(out["status"], "NUMERICALLY_UNAVAILABLE")
        self.assertEqual(out["nullity"], 1)

    def test_restoration_with_anchor(self):
        relative = f(
            "relative", [[-1.0, 1.0]], "relative-observation"
        )
        anchor = f("anchor", [[1.0, 0.0]], "anchor-source")
        before = analyze_factor_support(2, [relative])
        after = analyze_factor_support(2, [relative, anchor])
        self.assertEqual(before["numerical_rank"], 1)
        self.assertEqual(after["numerical_rank"], 2)
        self.assertEqual(after["status"], "NUMERICALLY_SUPPORTED")

    def test_dropout_removes_one_direction(self):
        first = f("x", [[1.0, 0.0]], "x")
        second = f("y", [[0.0, 1.0]], "y")
        complete = analyze_factor_support(2, [first, second])
        dropout = analyze_factor_support(2, [first])
        self.assertEqual(complete["numerical_rank"], 2)
        self.assertEqual(dropout["numerical_rank"], 1)
        self.assertEqual(
            dropout["status"], "NUMERICALLY_UNAVAILABLE"
        )

    def test_ill_conditioned_full_rank_unavailable(self):
        out = analyze_factor_support(
            2,
            [f("weak", np.diag([1.0, 1e-8]), "weak")],
            maximum_condition=1e6,
        )
        self.assertEqual(out["numerical_rank"], 2)
        self.assertEqual(out["status"], "NUMERICALLY_UNAVAILABLE")

    def test_duplicate_factor_rejected(self):
        with self.assertRaises(FactorSupportError):
            analyze_factor_support(1, [
                f("repeat", [[1]], "a"),
                f("repeat", [[1]], "b"),
            ])

    def test_shared_measurement_rejected(self):
        with self.assertRaises(FactorSupportError):
            analyze_factor_support(1, [
                f("one", [[1]], "same"),
                f("two", [[1]], "same"),
            ])

    def test_repeated_measurement_inside_factor_rejected(self):
        with self.assertRaises(FactorSupportError):
            analyze_factor_support(
                1, [f("one", [[1]], "a", "a")]
            )

    def test_nonfinite_factor_rejected(self):
        for value in (np.nan, np.inf, -np.inf):
            with self.subTest(value=value):
                with self.assertRaises(FactorSupportError):
                    analyze_factor_support(
                        1, [f("bad", [[value]], "sample")]
                    )

    def test_invalid_dimension_rejected(self):
        for dim in (0, -1, 3001, True):
            with self.subTest(dim=dim):
                with self.assertRaises(FactorSupportError):
                    analyze_factor_support(dim, [])

    def test_invalid_tolerances_rejected(self):
        for kwargs in (
            {"relative_rank_tolerance": 0},
            {"relative_rank_tolerance": np.nan},
            {"maximum_condition": 1},
            {"maximum_condition": np.inf},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(FactorSupportError):
                    analyze_factor_support(2, [], **kwargs)

    def test_15d_partial_factor_support(self):
        J = np.eye(15)[:9]
        out = analyze_factor_support(
            15, [f("partial", J, "partial")]
        )
        self.assertEqual(out["numerical_rank"], 9)
        self.assertEqual(out["nullity"], 6)
        self.assertFalse(out["physical_observability_verified"])
        self.assertFalse(out["calibrated_uncertainty_available"])

    def test_15d_complete_linear_support(self):
        out = analyze_factor_support(
            15, [f("synthetic-anchor", np.eye(15), "anchor")]
        )
        self.assertEqual(out["numerical_rank"], 15)
        self.assertTrue(out["numerical_information_psd"])
        self.assertEqual(out["status"], "NUMERICALLY_SUPPORTED")
        self.assertFalse(out["physical_observability_verified"])

    def test_deterministic_repeat(self):
        rng = np.random.default_rng(173)
        J = rng.normal(size=(25, 15))
        factors = [f("seeded", J, "seeded-measurement")]
        a = analyze_factor_support(15, factors)
        b = analyze_factor_support(15, factors)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main(verbosity=2)
