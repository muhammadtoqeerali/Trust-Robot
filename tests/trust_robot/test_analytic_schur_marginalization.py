import unittest

import numpy as np

from trust_robot.analytic_schur_marginalization import (
    synthetic_initial_anchor,
    information_prior,
    finite_difference_linearization,
    marginalize_one,
)


class MarginalizationTests(unittest.TestCase):

    def test_anchor_information(self):
        x = np.zeros(15)
        prior = synthetic_initial_anchor(
            x,
            sigma=0.2,
        )

        H, g = prior.normal_equations()

        np.testing.assert_allclose(
            H,
            25 * np.eye(15),
        )
        np.testing.assert_allclose(
            g,
            np.zeros(15),
        )

    def test_analytic_two_state_schur(self):
        anchor = synthetic_initial_anchor(
            np.zeros(15),
            0.2,
        )

        target = np.linspace(
            -0.3,
            0.3,
            15,
        )
        obs_sigma = 0.4

        def residual(states):
            return np.r_[
                anchor.residual(states),
                (
                    states[1]
                    - states[0]
                    - target
                ) / obs_sigma,
            ]

        prior, meta = marginalize_one(
            (0, 1),
            {
                0: np.zeros(15),
                1: np.zeros(15),
            },
            residual,
            0,
        )

        H, g = prior.normal_equations()

        np.testing.assert_allclose(
            H,
            np.eye(15) / (
                0.2**2 + obs_sigma**2
            ),
            rtol=1e-7,
            atol=1e-7,
        )

        np.testing.assert_allclose(
            np.linalg.solve(H, -g),
            target,
            atol=1e-7,
        )

        self.assertLess(
            np.linalg.norm(
                prior.residual({1: target})
            ),
            1e-7,
        )

        self.assertEqual(
            meta["retained_prior_rank"],
            15,
        )
        self.assertFalse(
            meta["physical_observability_proven"]
        )

    def test_repeated_elimination(self):
        anchor = synthetic_initial_anchor(
            np.zeros(15),
            0.1,
        )

        target1 = np.linspace(
            0.1, 0.2, 15
        )
        target2 = np.linspace(
            -0.15, 0.15, 15
        )

        first, _ = marginalize_one(
            (0, 1),
            {
                0: np.zeros(15),
                1: np.zeros(15),
            },
            lambda s: np.r_[
                anchor.residual(s),
                (
                    s[1] - s[0] - target1
                ) / 0.25,
            ],
            0,
        )

        second, _ = marginalize_one(
            (1, 2),
            {
                1: target1,
                2: target1 + target2,
            },
            lambda s: np.r_[
                first.residual(s),
                (
                    s[2] - s[1] - target2
                ) / 0.3,
            ],
            1,
        )

        self.assertEqual(
            second.node_ids,
            (2,),
        )

        self.assertLess(
            np.linalg.norm(
                second.residual({
                    2: target1 + target2
                })
            ),
            1e-7,
        )

        H, _ = second.normal_equations()

        np.testing.assert_allclose(
            H,
            np.eye(15) / (
                0.1**2
                + 0.25**2
                + 0.3**2
            ),
            rtol=1e-7,
            atol=1e-7,
        )

    def test_singular_elimination_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "singular information pivot",
        ):
            marginalize_one(
                (0, 1),
                {
                    0: np.zeros(15),
                    1: np.zeros(15),
                },
                lambda s: s[1].copy(),
                0,
            )

    def test_negative_information_rejected(self):
        H = np.eye(15)
        H[0, 0] = -1

        with self.assertRaisesRegex(
            ValueError,
            "Negative information",
        ):
            information_prior(
                (0,),
                np.zeros(15),
                H,
                np.zeros(15),
            )

    def test_nullspace_gradient_rejected(self):
        H = np.eye(15)
        H[-1, -1] = 0

        g = np.zeros(15)
        g[-1] = 1

        with self.assertRaisesRegex(
            ValueError,
            "unsupported",
        ):
            information_prior(
                (0,),
                np.zeros(15),
                H,
                g,
            )

    def test_nonfinite_residual_rejected(self):
        with self.assertRaises(ValueError):
            finite_difference_linearization(
                lambda x: np.array([np.nan]),
                np.zeros(15),
            )

    def test_duplicate_node_ids_rejected(self):
        with self.assertRaises(ValueError):
            marginalize_one(
                (0, 0),
                {0: np.zeros(15)},
                lambda s: s[0],
                0,
            )

    def test_unobserved_directions_not_invented(self):
        H = np.eye(15)
        H[-1, -1] = 0

        prior = information_prior(
            (0,),
            np.zeros(15),
            H,
            np.zeros(15),
        )

        self.assertEqual(
            prior.square_root_information.shape,
            (14, 15),
        )

        self.assertAlmostEqual(
            np.linalg.norm(
                prior.residual({
                    0: np.eye(15)[-1]
                })
            ),
            0,
        )

    def test_nonlinear_jacobian(self):
        x = np.linspace(
            0.01,
            0.2,
            15,
        )

        r, J = finite_difference_linearization(
            lambda z: np.sin(z),
            x,
        )

        np.testing.assert_allclose(
            r,
            np.sin(x),
        )

        np.testing.assert_allclose(
            J,
            np.diag(np.cos(x)),
            rtol=1e-8,
            atol=1e-8,
        )


if __name__ == "__main__":
    unittest.main()
