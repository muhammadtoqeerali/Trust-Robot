import unittest
from unittest.mock import patch
from trust_robot.clean_backbone import PoseSE3
from trust_robot import synthetic_tri_modal_consistency_limits_v1 as b

class SyntheticTriadTests(unittest.TestCase):

    def test_identity_triad_zero(self):
        z = b.triad(
            PoseSE3.identity(),
            PoseSE3.identity(),
            PoseSE3.identity()
        )
        self.assertEqual(z['camera_vs_lidar_translation_m'], 0.0)
        self.assertEqual(z['camera_vs_imu_translation_m'], 0.0)

    def test_triad_requires_typed_poses(self):
        with self.assertRaises(b.BoundaryError):
            b.triad(
                None, PoseSE3.identity(), PoseSE3.identity()
            )

    def test_canonical_deterministic(self):
        self.assertEqual(
            b.canonical({'b': 1, 'a': 2}),
            b.canonical({'a': 2, 'b': 1})
        )

    def test_invalid_origin_denied_before_fixture(self):
        for origin in (
            'NOVA_LIVE', 'NOVA_RECORDED',
            'M2DGR', None, {}, 0
        ):
            with self.subTest(origin=origin), patch(
                'trust_robot.synthetic_joint_fault_identifiability_v1.construct',
                side_effect=AssertionError('CONSTRUCT_CALLED')
            ):
                with self.assertRaises(b.BoundaryError):
                    b.case('baseline', 13, origin)

    def test_unknown_scenario_denied(self):
        with self.assertRaises(b.BoundaryError):
            b.case('physical_fault')

    def test_unknown_seed_denied(self):
        for seed in (True, 14, 0, 13.0, None):
            with self.subTest(seed=seed), self.assertRaises(b.BoundaryError):
                b.case('baseline', seed)

    def test_current_attribution_gate_closed(self):
        b.guard('ANALYTIC_FIXTURE')

    def test_malformed_imu_sequence_denied(self):
        from trust_robot.synthetic_joint_fault_identifiability_v1 import construct
        fixture, *_ = construct('baseline', 13)
        fixture['imu'][0]['measurement_origin'] = 'NOVA_LIVE'

        with self.assertRaises(b.BoundaryError):
            b.imu_edge_proxy(fixture)

    def test_imu_proxy_is_derived_from_two_samples(self):
        r = b.case('baseline', 13)
        self.assertEqual(
            r['imu_proxy_derived_from_samples'], [0, 1]
        )
        self.assertFalse(
            r['imu_proxy_is_independent_physical_reference']
        )

    def test_frozen_clean_factor_count(self):
        self.assertEqual(
            b.case('baseline', 13)['lidar_factor_count'], 7
        )

    def test_dropout_factor_count_and_hold(self):
        r = b.case('dropout_and_camera', 13)
        self.assertEqual(r['lidar_factor_count'], 3)
        self.assertEqual(r['known_lidar_hold_windows'], [2, 3])

    def test_camera_only_does_not_change_lidar_imu_metric(self):
        c = b.contrast(
            b.case('baseline', 13)['triad'],
            b.case('camera_only', 13)['triad']
        )
        self.assertEqual(
            c['lidar_vs_imu_translation_m'], 0.0
        )

    def test_lidar_only_does_not_change_camera_imu_metric(self):
        c = b.contrast(
            b.case('baseline', 13)['triad'],
            b.case('lidar_only', 13)['triad']
        )
        self.assertEqual(
            c['camera_vs_imu_translation_m'], 0.0
        )

    def test_joint_common_mode_blind_for_camera_lidar(self):
        d = b.contrast(
            b.case('baseline', 13)['triad'],
            b.case('joint_common_mode', 13)['triad']
        )
        self.assertEqual(
            d['camera_vs_lidar_translation_m'], 0.0
        )
        self.assertGreater(
            d['camera_vs_imu_translation_m'], 0.08
        )
        self.assertGreater(
            d['lidar_vs_imu_translation_m'], 0.08
        )

    def test_two_seeds_common_mode_third_proxy(self):
        for seed in b.SEEDS:
            with self.subTest(seed=seed):
                row = b.shifted_imu_proxy(seed)
                self.assertTrue(
                    row['translation_pairwise_metrics_unchanged']
                )
                self.assertFalse(
                    row['imu_proxy_shift_is_raw_imu_corruption']
                )

    def test_contrast_rejects_bad_data(self):
        with self.assertRaises(b.BoundaryError):
            b.contrast(
                {'camera_vs_lidar_translation_m': 1.0}, {}
            )

    def test_no_physical_health_attribution(self):
        result = b.case('camera_only', 13)
        self.assertEqual(
            result['physical_responsible_modality'],
            'UNRESOLVED'
        )
        self.assertEqual(
            result['real_factor_admission'], 'DENIED'
        )

    def test_probe_counterexample_only_manufactured_seed(self):
        with self.assertRaises(b.BoundaryError):
            b.shifted_imu_proxy(1)
