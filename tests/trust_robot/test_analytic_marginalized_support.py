"""Integration tests of support admission in the 15D estimator."""
import unittest

import numpy as np

from trust_robot.analytic_factor_support import FactorSupportError
from trust_robot.analytic_inertial_15d import (
    initial_state,
    make_fixture,
)
from trust_robot.analytic_preintegrated_fusion import make_factors
from trust_robot.analytic_schur_marginalization import (
    synthetic_initial_anchor,
)
from trust_robot.analytic_marginalized_fusion import (
    estimate_marginalized,
    estimate_marginalized_with_support,
)
from trust_robot.analytic_marginalized_support import (
    audit_marginalized_window,
)


def no_lidar_factors(fixture):
    imu, lidar, counts = make_factors(fixture)
    counts = dict(counts)
    counts["lidar_factor_count"] = 0
    return imu, {}, counts


class MarginalizedSupportIntegrationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.fixture, _ = make_fixture("clean")

    def test_real_estimator_legacy_report_parity(self):
        baseline, old = estimate_marginalized(self.fixture)
        measured, new = estimate_marginalized_with_support(
            self.fixture,
            support_policy="report",
        )

        self.assertEqual(baseline, measured)
        self.assertEqual(
            len(old["windows"]),
            len(new["windows"]),
        )

        for before, after in zip(old["windows"], new["windows"]):
            support = after["factor_support"]
            without = {
                k: v for k, v in after.items()
                if k != "factor_support"
            }
            self.assertEqual(before, without)
            self.assertEqual(
                support["factor_count"],
                1
                + after["active_imu_factor_count"]
                + after["active_lidar_factor_count"],
            )
            self.assertEqual(
                support["state_dimension"],
                after["required_rank"],
            )
            self.assertTrue(
                support["fitted_nonlinear_jacobian_used"]
            )
            self.assertFalse(
                support["physical_observability_verified"]
            )
            self.assertFalse(
                support["calibrated_uncertainty_available"]
            )

    def test_real_estimator_strict_supported_execution(self):
        _, result = estimate_marginalized_with_support(
            self.fixture,
            support_policy="require",
            support_max_condition=1e14,
            support_relative_rank_tolerance=1e-12,
        )
        self.assertEqual(len(result["windows"]), 4)
        for row in result["windows"]:
            self.assertEqual(
                row["factor_support"]["status"],
                "NUMERICALLY_SUPPORTED",
            )

    def test_condition_requirement_rejects(self):
        with self.assertRaisesRegex(
            ValueError, "support unavailable"
        ):
            estimate_marginalized_with_support(
                self.fixture,
                support_policy="require",
                support_max_condition=1.000001,
            )

    def test_no_current_lidar_report_is_explicit(self):
        _, result = estimate_marginalized_with_support(
            self.fixture,
            factor_factory=no_lidar_factors,
            support_policy="report",
        )
        for row in result["windows"]:
            support = row["factor_support"]
            self.assertFalse(
                support["current_lidar_factor_available"]
            )
            self.assertNotEqual(
                support["availability_diagnostic"],
                "CURRENT_LIDAR_SUPPORTED",
            )

    def test_current_lidar_requirement_fails_closed(self):
        with self.assertRaisesRegex(
            ValueError, "support unavailable"
        ):
            estimate_marginalized_with_support(
                self.fixture,
                factor_factory=no_lidar_factors,
                support_policy="require",
                require_active_lidar=True,
            )

    def test_invalid_policy_rejected(self):
        with self.assertRaisesRegex(
            ValueError, "Invalid estimator support policy"
        ):
            estimate_marginalized_with_support(
                self.fixture,
                support_policy="unsafe",
            )

    def test_invalid_lidar_requirement_rejected(self):
        with self.assertRaisesRegex(
            ValueError, "Invalid current-LiDAR requirement"
        ):
            estimate_marginalized_with_support(
                self.fixture,
                require_active_lidar="yes",
            )

    def test_prior_active_imu_overlap_rejected(self):
        imu, _, _ = make_factors(self.fixture)
        anchor = synthetic_initial_anchor(
            initial_state(), sigma=0.01
        )
        x = np.r_[initial_state(), initial_state()]
        J = np.zeros((30, 30))

        with self.assertRaises(FactorSupportError):
            audit_marginalized_window(
                J, x, [0, 1],
                (0, 2, 4, 6, 8),
                anchor,
                {(0, 1): imu[(0, 1)]},
                {},
                {(0, 1)},
                set(),
            )

    def test_jacobian_row_mismatch_rejected(self):
        anchor = synthetic_initial_anchor(
            initial_state(), sigma=0.01
        )
        x = np.r_[initial_state(), initial_state()]
        J = np.zeros((14, 30))

        with self.assertRaises(FactorSupportError):
            audit_marginalized_window(
                J, x, [0, 1],
                (0, 2, 4, 6, 8),
                anchor, {}, {}, set(), set(),
            )

    def test_nonfinite_fitted_jacobian_rejected(self):
        anchor = synthetic_initial_anchor(
            initial_state(), sigma=0.01
        )
        x = np.r_[initial_state(), initial_state()]
        J = np.zeros((15, 30))
        J[0, 0] = np.nan

        with self.assertRaises(FactorSupportError):
            audit_marginalized_window(
                J, x, [0, 1],
                (0, 2, 4, 6, 8),
                anchor, {}, {}, set(), set(),
            )

    def test_twelve_node_outage_support_reporting(self):
        from trust_robot.analytic_marginalized_horizon import (
            NODE_FRAMES,
            long_fixture,
            long_factors,
        )

        generated = long_fixture("lidar_outage")
        fixture = (
            generated[0]
            if isinstance(generated, tuple)
            else generated
        )

        records, result = estimate_marginalized_with_support(
            fixture,
            node_frames=NODE_FRAMES,
            factor_factory=long_factors,
            support_policy="report",
        )

        self.assertEqual(len(records), 12)
        self.assertEqual(len(result["windows"]), 11)

        for row in result["windows"]:
            support = row["factor_support"]
            self.assertEqual(
                support["state_dimension"],
                row["required_rank"],
            )
            self.assertFalse(
                support["physical_observability_verified"]
            )
            self.assertFalse(
                support["operational_safety_availability_verified"]
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
