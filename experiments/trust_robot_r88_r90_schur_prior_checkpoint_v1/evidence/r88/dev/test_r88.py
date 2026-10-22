import unittest
import numpy as np

import r84_gap_frontend as gap
import r88_schur as m


class MarginalizationTests(unittest.TestCase):

    def test_spd_accepts(self):
        np.testing.assert_array_equal(
            m.require_spd(np.eye(15)),
            np.eye(15)
        )

    def test_indefinite_denied(self):
        with self.assertRaises(m.MarginalizationError):
            m.require_spd(-np.eye(15))

    def test_unsymmetric_denied(self):
        H = np.eye(15)
        H[0, 1] = 0.2

        with self.assertRaises(m.MarginalizationError):
            m.require_spd(H)

    def test_nan_denied(self):
        H = np.eye(15)
        H[0, 0] = float('nan')

        with self.assertRaises(m.MarginalizationError):
            m.require_spd(H)

    def test_schur_indefinite_old_denied(self):
        with self.assertRaises(m.MarginalizationError):
            m.schur(
                -np.eye(15),
                np.zeros(15),
                0.,
                np.eye(15),
                np.eye(15),
                np.ones(15)
            )

    def test_schur_wrong_shape_denied(self):
        with self.assertRaises(m.MarginalizationError):
            m.schur(
                np.eye(15),
                np.zeros(15),
                0.,
                np.eye(14),
                np.eye(15),
                np.ones(15)
            )

    def test_schur_positive(self):
        H, g, c = m.schur(
            np.eye(15),
            np.zeros(15),
            0.,
            np.eye(15),
            np.eye(15),
            np.ones(15)
        )

        self.assertEqual(H.shape, (15, 15))
        self.assertGreater(
            np.linalg.eigvalsh(H).min(), 0
        )
        self.assertTrue(np.isfinite(g).all())
        self.assertTrue(np.isfinite(c))

    def test_continuous_factor_window_count(self):
        parts, gaps = m.segment_groups(
            gap.fixture('continuous')
        )

        self.assertEqual(
            (
                len(parts),
                gaps,
                sum(map(len, parts))
            ),
            (1, 0, 4)
        )

    def test_timestamp_gap_starts_fresh(self):
        parts, gaps = m.segment_groups(
            gap.fixture('single_gap')
        )

        self.assertEqual(
            (
                len(parts),
                gaps,
                sum(map(len, parts))
            ),
            (2, 1, 4)
        )

        self.assertLess(
            parts[0][-1][1],
            parts[1][0][0]
        )

    def test_disconnected_batch_solve(self):
        x = m.solve_case(
            gap.fixture('single_gap')
        )

        self.assertEqual(
            x['cross_gap_schur_prior_carry_count'], 0
        )
        self.assertEqual(x['segments'], 2)

    def test_batch_equivalence_clean(self):
        x = m.solve_case(
            gap.fixture('continuous')
        )

        self.assertEqual(x['segments'], 1)
        self.assertEqual(x['marginalized_states'], 3)

        self.assertLess(
            x['segments_results'][0][
                'schur_vs_batch_state_l2_error'
            ],
            1e-4
        )

    def test_batch_equivalence_gap(self):
        x = m.solve_case(
            gap.fixture('single_gap')
        )

        self.assertEqual(
            [
                v['eliminated_state_count']
                for v in x['segments_results']
            ],
            [1, 1]
        )

    def test_covariance_consistency(self):
        x = m.solve_case(
            gap.fixture('continuous')
        )

        self.assertLess(
            x['segments_results'][0][
                'schur_vs_batch_covariance_relative_error'
            ],
            2e-3
        )

    def test_cost_consistency(self):
        x = m.solve_case(
            gap.fixture('continuous')
        )

        self.assertLess(
            x['segments_results'][0][
                'schur_vs_batch_optimum_cost_abs_error'
            ],
            1e-5
        )

    def test_synthetic_gyro_case(self):
        self.assertEqual(
            m.solve_case(
                gap.fixture('gyro_injection')
            )['segments'],
            1
        )

    def test_synthetic_accel_case(self):
        self.assertEqual(
            m.solve_case(
                gap.fixture('accel_injection')
            )['segments'],
            1
        )

    def test_deterministic(self):
        self.assertEqual(
            m.solve_case(
                gap.fixture('single_gap')
            ),
            m.solve_case(
                gap.fixture('single_gap')
            )
        )

    def test_real_stream_denied(self):
        p = gap.fixture('continuous')
        p[0]['source_id'] = '/camera/imu'

        with self.assertRaises((
            gap.InertialAdmissionError,
            m.MarginalizationError
        )):
            m.solve_case(p)

    def test_confirmation_denied(self):
        p = gap.fixture('continuous')
        p[0]['confirmation_test_accessed'] = True

        with self.assertRaises((
            gap.InertialAdmissionError,
            m.MarginalizationError
        )):
            m.solve_case(p)

    def test_duplicate_timestamp_denied(self):
        p = gap.fixture('continuous')
        p[1]['timestamp_ns'] = p[0]['timestamp_ns']

        with self.assertRaises((
            gap.InertialAdmissionError,
            m.MarginalizationError
        )):
            m.solve_case(p)

    def test_train_split_denied(self):
        p = gap.fixture('continuous')
        p[0]['split_role'] = 'train'

        with self.assertRaises((
            gap.InertialAdmissionError,
            m.MarginalizationError
        )):
            m.solve_case(p)


if __name__ == '__main__':
    unittest.main(verbosity=2)
