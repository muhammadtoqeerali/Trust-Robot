import unittest
from trust_robot import observation_aware_support_shadow_v1 as b

class ShadowTests(unittest.TestCase):

    def windows(self):
        return [
            {
                'end_node': i,
                'active_lidar_factor_count': 1,
                'factor_support': {
                    'status': 'NUMERICALLY_SUPPORTED',
                    'current_lidar_factor_available': True
                }
            }
            for i in range(1, 5)
        ]

    def flags(self):
        return [True] * 9

    def check(self, flags=None, windows=None):
        return b.assess(
            self.flags() if flags is None else flags,
            (0, 2, 4, 6, 8),
            self.windows() if windows is None else windows
        )

    def test_all_present_eligible_synthetic_only(self):
        self.assertEqual(
            self.check()['global_shadow_decision'],
            'ELIGIBLE_SYNTHETIC_SHADOW_ONLY'
        )

    def test_dropout_blocked_even_with_full_numeric_rank(self):
        f = self.flags()
        f[4] = False
        z = self.check(f)

        self.assertEqual(
            z['global_shadow_decision'],
            'HOLD_SYNTHETIC_SHADOW'
        )
        self.assertEqual(z['missing_node_frames'], [4])
        self.assertEqual(
            [
                v['end_node']
                for v in z['window_decisions']
                if v['shadow_decision'].startswith('HOLD')
            ],
            [2, 3]
        )

    def test_missing_first_frame(self):
        f = self.flags()
        f[0] = False
        self.assertEqual(
            [
                x['end_node']
                for x in self.check(f)['window_decisions']
                if x['shadow_decision'].startswith('HOLD')
            ],
            [1]
        )

    def test_missing_last_frame(self):
        f = self.flags()
        f[8] = False
        self.assertEqual(
            [
                x['end_node']
                for x in self.check(f)['window_decisions']
                if x['shadow_decision'].startswith('HOLD')
            ],
            [4]
        )

    def test_missing_non_node_frame_not_claimed(self):
        f = self.flags()
        f[3] = False
        self.assertEqual(
            self.check(f)['missing_node_frames'],
            []
        )

    def test_numerically_unsupported_hold(self):
        w = self.windows()
        w[0]['factor_support']['status'] = 'INSUFFICIENT'
        self.assertEqual(
            self.check(windows=w)['window_decisions'][0]['shadow_decision'],
            'HOLD_NUMERIC_OR_LIDAR_SUPPORT'
        )

    def test_current_lidar_absent_hold(self):
        w = self.windows()
        w[0]['active_lidar_factor_count'] = 0
        w[0]['factor_support']['current_lidar_factor_available'] = False
        self.assertEqual(
            self.check(windows=w)['global_shadow_decision'],
            'HOLD_SYNTHETIC_SHADOW'
        )

    def test_active_count_mismatch_refused(self):
        w = self.windows()
        w[0]['active_lidar_factor_count'] = 0
        with self.assertRaises(b.ShadowDenied):
            self.check(windows=w)

    def test_bad_window_chronology_refused(self):
        w = self.windows()
        w[1]['end_node'] = 3
        with self.assertRaises(b.ShadowDenied):
            self.check(windows=w)

    def test_missing_support_refused(self):
        w = self.windows()
        del w[0]['factor_support']
        with self.assertRaises(b.ShadowDenied):
            self.check(windows=w)

    def test_bool_count_spoof_refused(self):
        w = self.windows()
        w[0]['active_lidar_factor_count'] = True
        with self.assertRaises(b.ShadowDenied):
            self.check(windows=w)

    def test_bad_mask_shapes_refused(self):
        for mask in (
            [], [True] * 8, [True] * 10,
            'x', [1] + [True] * 8
        ):
            with self.subTest(mask=mask):
                with self.assertRaises(b.ShadowDenied):
                    self.check(mask)

    def test_bad_schedule_refused(self):
        with self.assertRaises(b.ShadowDenied):
            b.assess(
                self.flags(), (0, 1, 2, 3, 4),
                self.windows()
            )

    def test_real_origins_denied_before_solver(self):
        for origin in (
            'NOVA_RECORDED', 'NOVA_LIVE',
            'M2DGR', None, 123, {}
        ):
            with self.subTest(origin=origin):
                with self.assertRaises(b.ShadowDenied):
                    b.run_case('clean', origin)

    def test_unknown_fixture_denied(self):
        with self.assertRaises(b.ShadowDenied):
            b.run_case('outside_fixture')

    def test_gates_closed(self):
        b.frozen_gates()

    def test_deterministic_encoding(self):
        self.assertEqual(
            b.canonical({'a': 1, 'b': 2}),
            b.canonical({'b': 2, 'a': 1})
        )

class PublishedSolverIntegrationTests(unittest.TestCase):
    def test_full_clean_fixture_eligible_but_not_physical(self):
        x = b.run_case('clean')
        self.assertEqual(
            x['shadow']['global_shadow_decision'],
            'ELIGIBLE_SYNTHETIC_SHADOW_ONLY'
        )
        self.assertFalse(x['real_sensor_health_inferred'])
        self.assertEqual(x['real_factor_admission'], 'DENIED')

    def test_full_manufactured_bias_is_not_a_health_label(self):
        x = b.run_case('accel_bias')
        self.assertEqual(
            x['shadow']['global_shadow_decision'],
            'ELIGIBLE_SYNTHETIC_SHADOW_ONLY'
        )
        self.assertFalse(x['real_sensor_health_inferred'])
        self.assertFalse(x['source_blame_assigned'])

    def test_full_manufactured_dropout_holds_two_intervals(self):
        x = b.run_case('lidar_dropout')
        d = x['shadow']
        self.assertEqual(d['missing_node_frames'], [4])
        self.assertEqual(
            [
                v['end_node']
                for v in d['window_decisions']
                if v['shadow_decision'].startswith('HOLD')
            ],
            [2, 3]
        )
        self.assertTrue(
            all(
                v['numeric_support_status'] == 'NUMERICALLY_SUPPORTED'
                for v in d['window_decisions']
            )
        )
        self.assertEqual(
            d['global_shadow_decision'],
            'HOLD_SYNTHETIC_SHADOW'
        )
