import unittest
from unittest.mock import patch
from trust_robot.clean_backbone import PoseSE3
from trust_robot import synthetic_joint_fault_identifiability_v1 as a

class JointFaultContractTests(unittest.TestCase):

    def test_cases_frozen(self):
        self.assertEqual(len(a.DESIGNS), 6)

    def test_shift_identity(self):
        p = PoseSE3.identity()
        self.assertEqual(a.shift_x(p, 0.0), p)

    def test_shift_magnitude(self):
        p = a.shift_x(PoseSE3.identity(), 0.125)
        self.assertAlmostEqual(p.translation_m[0], 0.125)

    def test_pose_input_unchanged(self):
        p = PoseSE3.identity()
        a.shift_x(p, 0.125)
        self.assertEqual(p, PoseSE3.identity())

    def test_invalid_shift(self):
        for x in (True, 1, 1.0, 0.02, '0.125', None):
            with self.subTest(x=x), self.assertRaises(a.ContractError):
                a.shift_x(PoseSE3.identity(), x)

    def test_invalid_pose(self):
        with self.assertRaises(a.ContractError):
            a.shift_x('not_a_pose', 0.125)

    def test_symmetrical_gap_same_under_equal_translation(self):
        c = PoseSE3((0.01, 0, 0), (1, 0, 0, 0))
        l = PoseSE3.identity()
        x = a.gap(c, l)
        self.assertEqual(
            x,
            a.gap(
                a.shift_x(c, 0.125),
                a.shift_x(l, 0.125),
            ),
        )

    def test_pair_hash_changes_under_common_mode(self):
        c = PoseSE3((0.01, 0, 0), (1, 0, 0, 0))
        l = PoseSE3.identity()
        self.assertNotEqual(
            a.pair_signature(c, l),
            a.pair_signature(
                a.shift_x(c, 0.125),
                a.shift_x(l, 0.125),
            ),
        )

    def test_single_camera_shift_changes_gap(self):
        c = PoseSE3((0.01, 0, 0), (1, 0, 0, 0))
        l = PoseSE3.identity()
        self.assertNotEqual(
            a.gap(c, l),
            a.gap(a.shift_x(c, 0.125), l),
        )

    def test_reject_real_origins_before_solver(self):
        for x in (
            'NOVA_LIVE', 'NOVA_RECORDED',
            'M2DGR', None, 7, {},
        ):
            with self.subTest(x=x), patch(
                'trust_robot.analytic_separated_modalities.estimate_separated',
                side_effect=AssertionError('SOLVER_CALLED'),
            ):
                with self.assertRaises(a.ContractError):
                    a.run_case('baseline', 13, origin=x)

    def test_reject_unknown_scenario(self):
        with self.assertRaises(a.ContractError):
            a.construct('physical')

    def test_reject_unknown_seed(self):
        for x in (True, 0, 4, '13', 13.0, None):
            with self.subTest(x=x), self.assertRaises(a.ContractError):
                a.construct('baseline', x)

    def test_source_attribution_stays_closed(self):
        a.guard('ANALYTIC_FIXTURE')

    def test_unexpectedly_open_attribution_refused(self):
        with patch(
            'trust_robot.auxiliary_consistency.assert_source_attribution_authorized',
            return_value=None,
        ):
            with self.assertRaises(a.ContractError):
                a.guard('ANALYTIC_FIXTURE')

    def test_camera_provenance_not_relabelled(self):
        *_, packets, expected = a.construct('camera_only')
        self.assertEqual(len(packets), 2)
        self.assertTrue(all(
            p.origin == 'ANALYTIC_FIXTURE'
            and p.modality == 'camera'
            for p in packets
        ))

    def test_baseline_frontend_topology(self):
        _, _, lidar, _, _, e = a.construct('baseline')
        self.assertEqual(len(lidar), 7)
        self.assertEqual(e['required_shadow_holds'], [])

    def test_dropout_frontend_topology(self):
        _, _, lidar, _, _, e = a.construct('dropout_and_camera')
        self.assertEqual(len(lidar), 3)
        self.assertEqual(e['required_shadow_holds'], [2, 3])

    def test_solver_smoke_and_ledger(self):
        r = a.run_case('baseline', 13)
        self.assertEqual(
            (r['camera_factors'], r['lidar_factors']),
            (2, 7),
        )
        self.assertEqual(r['real_factor_admission'], 'DENIED')

    def test_json_determinism(self):
        self.assertEqual(
            a.canonical({'b': 2, 'a': 1}),
            a.canonical({'a': 1, 'b': 2}),
        )
