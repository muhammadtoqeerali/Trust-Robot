import inspect
import tempfile
import unittest
from pathlib import Path

import numpy as np

from trust_robot.analytic_inertial_15d import (
    make_fixture,
)
from trust_robot.analytic_imu_preintegration import (
    SIGMAS,
    GYRO_INJECTION,
    preintegrate,
    bias_correct,
    right_jacobian,
    error_and_whiten,
    finite_difference_jacobian,
    canonical,
    execute,
    run,
)


class PreintegrationTests(unittest.TestCase):

    def setUp(self):
        self.fixture, self.truth = make_fixture("clean")
        self.samples = self.fixture["imu"][:4]

    def test_right_jacobian_small_angle(self):
        np.testing.assert_allclose(
            right_jacobian(np.zeros(3)),
            np.eye(3),
        )

    def test_clean_analytic_closure(self):
        pre = preintegrate(
            self.fixture["imu"][:2]
        )
        np.testing.assert_allclose(
            error_and_whiten(
                pre, self.truth[0], self.truth[2]
            ),
            np.zeros(15),
            atol=1e-7,
        )

    def test_covariance_properties(self):
        p = preintegrate(self.samples)

        self.assertEqual(
            p["covariance"].shape, (15, 15)
        )
        self.assertEqual(
            p["jacobian_bias"].shape, (9, 6)
        )
        self.assertGreater(
            float(np.trace(p["covariance"])), 0
        )
        self.assertGreaterEqual(
            float(np.linalg.eigvalsh(
                p["covariance"]
            ).min()),
            -1e-12,
        )

    def test_noise_scaling(self):
        a = preintegrate(self.samples)

        b = preintegrate(
            self.samples,
            sigmas={
                k: 3*v
                for k, v in SIGMAS.items()
            },
        )

        np.testing.assert_allclose(
            b["covariance"],
            9*a["covariance"],
            atol=1e-10,
        )

    def test_bias_jacobian_finite_difference(self):
        self.assertLess(
            finite_difference_jacobian(
                self.samples
            ),
            2e-4,
        )

    def test_small_bias_correction(self):
        b = np.r_[
            GYRO_INJECTION,
            [0.06, -0.02, 0.03],
        ]

        nominal = preintegrate(self.samples)

        corrected = bias_correct(
            nominal, b[:3], b[3:]
        )

        exact = preintegrate(
            self.samples, b[:3], b[3:]
        )

        self.assertLess(
            np.linalg.norm(
                corrected["delta_p"] - exact["delta_p"]
            ),
            5e-4,
        )

        self.assertLess(
            np.linalg.norm(
                corrected["delta_v"] - exact["delta_v"]
            ),
            5e-4,
        )

        self.assertLess(
            (
                corrected["delta_R"].inv()
                * exact["delta_R"]
            ).magnitude(),
            5e-4,
        )

    def test_invalid_time_rejected(self):
        reading = dict(
            self.samples[0], dt_s=-0.1
        )

        with self.assertRaises(ValueError):
            preintegrate([reading])

    def test_unverified_source_rejected(self):
        reading = dict(
            self.samples[0],
            physical_clock_verified=True,
        )

        with self.assertRaises(ValueError):
            preintegrate([reading])

    def test_nonfinite_measurement_rejected(self):
        reading = dict(
            self.samples[0],
            gyro_rad_s=[float("nan"), 0, 0],
        )

        with self.assertRaises(ValueError):
            preintegrate([reading])

    def test_reference_not_preintegrator_input(self):
        self.assertNotIn(
            "truth",
            inspect.signature(
                preintegrate
            ).parameters,
        )

    def test_controlled_bias_effects(self):
        _, manifest = execute()

        self.assertLess(
            manifest["results"]["clean"][
                "mean_whitened_motion_residual"
            ],
            1e-7,
        )

        for condition in (
            "accel_bias", "gyro_bias"
        ):
            self.assertGreater(
                manifest["results"][condition][
                    "mean_whitened_motion_residual"
                ],
                0.1,
            )

        self.assertFalse(
            manifest["factor_graph_solver_integrated"]
        )

    def test_repeat_and_manifest(self):
        with tempfile.TemporaryDirectory() as root:
            result = run(
                Path(root) / "output"
            )
            self.assertTrue(
                result["repeat_derivation_identical"]
            )

    def test_nonfinite_json_rejected(self):
        with self.assertRaises(ValueError):
            canonical({
                "bad": float("nan")
            })


if __name__ == "__main__":
    unittest.main()
