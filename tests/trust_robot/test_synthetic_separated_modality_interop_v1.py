import unittest
from unittest.mock import patch
from trust_robot import synthetic_separated_modality_interop_v1 as b

class SyntheticSeparatedInteropTests(unittest.TestCase):

    def test_mirror_pairwise_gap_invariant(self):
        d = b.mirrored_ambiguity()
        self.assertEqual(
            d['manufactured_translation_gap_m'], 0.125
        )
        self.assertEqual(
            d['manufactured_translation_gap_m'],
            d['swapped_source_gap_m']
        )

    def test_no_causal_inference(self):
        d = b.mirrored_ambiguity()
        self.assertEqual(
            d['physical_responsible_modality'],
            'UNRESOLVED'
        )
        self.assertFalse(d['causal_probability_calibrated'])

    def test_canonical_deterministic(self):
        self.assertEqual(
            b.canonical({'a': 1, 'b': 2}),
            b.canonical({'b': 2, 'a': 1})
        )

    def test_refuse_live_and_recorded_before_backend(self):
        for origin in (
            'NOVA_LIVE', 'NOVA_RECORDED',
            'M2DGR', '', None, 2, {}
        ):
            with self.subTest(origin=origin):
                with patch(
                    'trust_robot.analytic_separated_modalities.estimate_separated',
                    side_effect=AssertionError('BACKEND_CALLED')
                ):
                    with self.assertRaises(b.BoundaryError):
                        b.run_case('clean', 13, True, origin)

    def test_unknown_condition_rejected(self):
        with self.assertRaises(b.BoundaryError):
            b.run_case('physical', 13, True)

    def test_invalid_seed_rejected(self):
        for seed in (0, 14, True, 13.0, '13', None):
            with self.subTest(seed=seed):
                with self.assertRaises(b.BoundaryError):
                    b.run_case('clean', seed, True)

    def test_bad_camera_toggle_rejected(self):
        for enabled in (1, 0, 'on', None):
            with self.subTest(enabled=enabled):
                with self.assertRaises(b.BoundaryError):
                    b.run_case('clean', 13, enabled)

    def test_id_partition_rejects_duplicate(self):
        with self.assertRaises(b.BoundaryError):
            b.check_id_partition(
                ['a', 'a'], [], ['a']
            )

    def test_id_partition_rejects_missing(self):
        with self.assertRaises(b.BoundaryError):
            b.check_id_partition(
                ['a'], [], ['a', 'b']
            )

    def test_id_partition_rejects_reused(self):
        with self.assertRaises(b.BoundaryError):
            b.check_id_partition(
                ['a'], ['a'], ['a']
            )

    def test_id_partition_accepts_consumed_and_remaining(self):
        b.check_id_partition(
            ['a'], ['b'], ['a', 'b']
        )

    def test_closed_health_and_attribution_gates(self):
        b.guard('ANALYTIC_FIXTURE')

    def test_source_attribution_cannot_be_reenabled(self):
        with patch(
            'trust_robot.auxiliary_consistency.assert_source_attribution_authorized',
            return_value=None
        ):
            with self.assertRaises(b.BoundaryError):
                b.guard('ANALYTIC_FIXTURE')

    def test_clean_separate_same_edge(self):
        r = b.run_case('clean', 13, True)
        self.assertEqual(
            (
                r['legacy_pose_slots'],
                r['separated_pose_factors']
            ),
            (7, 9)
        )
        self.assertEqual(
            r['same_edge_separate_source_pairs'], 2
        )
        self.assertTrue(
            r['separate_source_factor_ownership_verified']
        )

    def test_dropout_separate_same_edge(self):
        r = b.run_case('lidar_dropout', 13, True)
        self.assertEqual(
            (
                r['legacy_pose_slots'],
                r['separated_pose_factors']
            ),
            (4, 5)
        )
        self.assertEqual(
            r['same_edge_separate_source_pairs'], 1
        )
        self.assertEqual(
            r['shadow_only_lidar_hold_windows'],
            [2, 3]
        )

    def test_camera_disabled_parity_in_factor_count(self):
        r = b.run_case('clean', 13, False)
        self.assertEqual(
            (
                r['legacy_pose_slots'],
                r['separated_pose_factors']
            ),
            (7, 7)
        )
        self.assertEqual(
            r['camera_measurement_id_count'], 0
        )

if __name__ == '__main__':
    unittest.main()

class PublishedSeparatedInteropIntegrationTests(unittest.TestCase):
    def test_published_clean_and_dropout_counts(self):
        clean = b.run_case('clean', 13, True)
        dropout = b.run_case('lidar_dropout', 13, True)
        self.assertEqual((clean['legacy_pose_slots'], clean['separated_pose_factors']), (7, 9))
        self.assertEqual((dropout['legacy_pose_slots'], dropout['separated_pose_factors']), (4, 5))
        self.assertEqual(dropout['shadow_only_lidar_hold_windows'], [2, 3])
        self.assertFalse(clean['fixed_camera_residual_scales_calibrated'])

    def test_published_second_seed_stays_unattributed(self):
        row = b.run_case('clean', 31, True)
        self.assertEqual(row['same_edge_separate_source_pairs'], 2)
        self.assertEqual(row['real_source_attribution'], 'UNRESOLVED')
        self.assertEqual(row['real_factor_admission'], 'DENIED')
