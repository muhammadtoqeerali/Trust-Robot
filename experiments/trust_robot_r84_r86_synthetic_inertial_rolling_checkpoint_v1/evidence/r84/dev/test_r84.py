import copy
import math
import unittest

import r84_gap_frontend as g


class GapTests(unittest.TestCase):

    def test_clean_two_windows(self):
        a = g.analyze(g.fixture('continuous'))

        self.assertEqual(
            (
                a['safe_window_count'],
                a['integrated_pair_count'],
                a['gap_count']
            ),
            (2, 8, 0)
        )

    def test_gap_splits_and_skips(self):
        a = g.analyze(g.fixture('single_gap'))

        self.assertEqual(
            (
                a['safe_window_count'],
                a['integrated_pair_count'],
                a['gap_count']
            ),
            (2, 7, 1)
        )

        self.assertLess(
            a['windows'][0]['synthetic_end_ns'],
            a['windows'][1]['synthetic_start_ns']
        )

    def test_covariance_psd(self):
        rows = g.analyze(
            g.fixture('continuous')
        )['windows']

        for row in rows:
            self.assertGreater(
                row['covariance_15d_trace'], 0
            )

            self.assertGreaterEqual(
                row['covariance_15d_min_eigenvalue'],
                -1e-12
            )

    def test_bias_accuracy(self):
        rows = g.analyze(
            g.fixture('accel_injection')
        )['windows']

        for row in rows:
            self.assertLess(
                max(
                    row['bias_first_order_vs_exact_errors']
                ),
                1e-3
            )

    def test_gyro_dynamics_differ(self):
        a = g.analyze(g.fixture('continuous'))
        b = g.analyze(g.fixture('gyro_injection'))

        self.assertNotEqual(
            a['windows'][-1]['delta_rotation_quaternion_xyzw'],
            b['windows'][-1]['delta_rotation_quaternion_xyzw']
        )

    def test_accel_dynamics_differ(self):
        a = g.analyze(g.fixture('continuous'))
        b = g.analyze(g.fixture('accel_injection'))

        self.assertNotEqual(
            a['windows'][-1]['delta_velocity_m_s'],
            b['windows'][-1]['delta_velocity_m_s']
        )

    def test_repeat_determinism(self):
        self.assertEqual(
            g.analyze(g.fixture('single_gap')),
            g.analyze(g.fixture('single_gap'))
        )

    def reject(self, fn):
        items = copy.deepcopy(
            g.fixture('continuous')
        )

        fn(items)

        with self.assertRaises((
            g.InertialAdmissionError,
            ValueError,
            KeyError,
            TypeError
        )):
            g.analyze(items)

    def test_real_stream_rejected(self):
        self.reject(
            lambda a: a[0].update(
                source_id='/camera/imu'
            )
        )

    def test_gt_scope_rejected(self):
        self.reject(
            lambda a: a[0].update(
                reference_data_used=True
            )
        )

    def test_heldout_rejected(self):
        self.reject(
            lambda a: a[0].update(
                confirmation_test_accessed=True
            )
        )

    def test_physical_clock_claim_rejected(self):
        self.reject(
            lambda a: a[0].update(
                physical_clock_verified=True
            )
        )

    def test_wrong_split_rejected(self):
        self.reject(
            lambda a: a[0].update(
                split_role='train'
            )
        )

    def test_extra_authorization_rejected(self):
        self.reject(
            lambda a: a[0].update(
                real_factor_executable=True
            )
        )

    def test_bad_gyro_rejected(self):
        self.reject(
            lambda a: a[0].update(
                gyro_rad_s=[float('nan'), 0, 0]
            )
        )

    def test_bad_accel_rejected(self):
        self.reject(
            lambda a: a[0].update(
                specific_force_m_s2=[1, 2]
            )
        )

    def test_duplicate_stamp_rejected(self):
        self.reject(
            lambda a: a[1].update(
                timestamp_ns=a[0]['timestamp_ns']
            )
        )

    def test_backwards_stamp_rejected(self):
        self.reject(
            lambda a: a[1].update(
                timestamp_ns=a[0]['timestamp_ns'] - 1
            )
        )

    def test_huge_gap_only_rejected(self):
        a = g.fixture('continuous')

        for i, x in enumerate(a):
            x['timestamp_ns'] = (
                1_000_000_000 + 1_000_000_000*i
            )

        with self.assertRaises(g.InertialAdmissionError):
            g.analyze(a)

    def test_strict_window_size(self):
        with self.assertRaises(g.InertialAdmissionError):
            g.partition(
                g.fixture('continuous'),
                max_steps=0
            )

    def test_source_magnitude_not_axes(self):
        self.reject(
            lambda a: a[0].update(
                gyro_rad_s=[0.03]
            )
        )

    def test_no_usable_sampling_interval(self):
        with self.assertRaises(g.InertialAdmissionError):
            g.analyze(
                g.fixture('continuous')[:1]
            )


if __name__ == '__main__':
    unittest.main(verbosity=2)
