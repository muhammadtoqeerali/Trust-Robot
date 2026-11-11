import unittest
from unittest.mock import patch
from trust_robot.clean_backbone import PoseSE3
from trust_robot import synthetic_cross_modal_ambiguity_v1 as b

class AmbiguityUnitTests(unittest.TestCase):

    def test_identity_gap_zero(self):
        d=b.pose_gap(
            PoseSE3.identity(),PoseSE3.identity()
        )
        self.assertEqual(
            d['relative_translation_difference_m'],0
        )
        self.assertEqual(
            d['relative_rotation_difference_deg'],0
        )

    def test_translation_gap(self):
        p=PoseSE3((0.1,0,0),(1,0,0,0))
        self.assertAlmostEqual(
            b.pose_gap(
                PoseSE3.identity(),p
            )['relative_translation_difference_m'],
            0.1
        )

    def test_reverse_pair_has_same_gap(self):
        p=PoseSE3(
            (0.1,-0.2,0.3),
            (0.999,0.0,0.0,0.04)
        )
        self.assertEqual(
            b.pose_gap(p,PoseSE3.identity()),
            b.pose_gap(PoseSE3.identity(),p)
        )

    def test_wrong_pose_type_rejected(self):
        for x in ('lidar',None,{},0):
            with self.subTest(x=x):
                with self.assertRaises(b.EvidenceBoundary):
                    b.pose_gap(x,PoseSE3.identity())

    def test_two_hypotheses_same_observation(self):
        evidence=b.pose_gap(
            PoseSE3.identity(),
            PoseSE3((1,0,0),(1,0,0,0))
        )
        obj=b.competing_hypotheses(evidence)
        self.assertEqual(
            len(obj['compatible_unverified_hypotheses']),2
        )
        self.assertEqual(
            obj['responsible_modality'],'UNRESOLVED'
        )
        self.assertFalse(
            obj['hypothesis_probability_assigned']
        )

    def test_refuse_culprit(self):
        for origin in ('camera','lidar','imu',None):
            with self.subTest(origin=origin):
                with self.assertRaises(b.EvidenceBoundary):
                    b.refuse_attribution(origin)

    def test_reject_spoofed_metric(self):
        z=b.pose_gap(
            PoseSE3.identity(),PoseSE3.identity()
        )
        for key in (
            'physical_metric_calibrated',
            'selected_physical_threshold'
        ):
            v=dict(z)
            v[key]=True
            with self.assertRaises(b.EvidenceBoundary):
                b.competing_hypotheses(v)

    def test_reject_negative_metric(self):
        z=b.pose_gap(
            PoseSE3.identity(),PoseSE3.identity()
        )
        z['relative_translation_difference_m']=-1.0
        with self.assertRaises(b.EvidenceBoundary):
            b.competing_hypotheses(z)

    def test_refuse_non_synthetic_origins_before_generator(self):
        for s in (
            'NOVA_RECORDED','NOVA_LIVE',
            'M2DGR',None,{},7
        ):
            with self.subTest(source=s):
                with patch(
                    'trust_robot.analytic_inertial_15d.make_fixture',
                    side_effect=AssertionError('CALLED')
                ):
                    with self.assertRaises(b.EvidenceBoundary):
                        b.paired_fixture(origin=s)

    def test_only_frozen_seeds(self):
        for v in (0,42,True,None,13.0):
            with self.subTest(seed=v):
                with self.assertRaises(b.EvidenceBoundary):
                    b.paired_fixture(seed=v)

    def test_solver_controls_validate_inputs_before_call(self):
        for c,e in (
            ('bad',True),
            ('clean','yes'),
            ('clean',1)
        ):
            with self.subTest(case=(c,e)):
                with self.assertRaises(b.EvidenceBoundary):
                    b.solver_control(c,e)

    def test_frozen_scientific_gates_closed(self):
        b.guard('ANALYTIC_FIXTURE')

    def test_json_reproducible(self):
        self.assertEqual(
            b.canonical({'b':2,'a':1}),
            b.canonical({'a':1,'b':2})
        )

    def test_actual_frontend_substitution(self):
        row=b.paired_fixture(13)
        self.assertEqual(
            row['camera_lidar_edge_overlap_count'],2
        )
        self.assertEqual(
            row['frozen_legacy_pose_slot']['camera_substitutions'],2
        )
        self.assertFalse(
            row['frozen_legacy_pose_slot']['same_edge_double_counted']
        )

    def test_different_seed_still_unknown_culprit(self):
        row=b.paired_fixture(31)
        self.assertEqual(
            row['physical_sensor_source_attribution'],
            'UNRESOLVED'
        )
        self.assertEqual(
            len(row['paired_camera_lidar_edges']),2
        )

    def test_real_case_never_invokes_solver(self):
        with patch(
            'trust_robot.analytic_three_modality_bridge.execute_case',
            side_effect=AssertionError('CALLED')
        ):
            with self.assertRaises(b.EvidenceBoundary):
                b.solver_control(
                    'clean',True,origin='NOVA_LIVE'
                )

if __name__=='__main__':
    unittest.main()

class PublishedCrossModalIntegrationTests(unittest.TestCase):
    def test_published_pairwise_discrepancies_not_attribution(self):
        rows = b.paired_fixture(seed=13)['paired_camera_lidar_edges']
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(
            x['diagnostic_only']['responsible_modality'] == 'UNRESOLVED'
            for x in rows
        ))

    def test_published_legacy_camera_slot_ownership(self):
        clean = b.solver_control('clean', True)
        dropout = b.solver_control('lidar_dropout', True)
        self.assertEqual(
            (clean['camera_slots'], clean['lidar_slots'], clean['total_pose_slots']),
            (2, 5, 7)
        )
        self.assertEqual(
            (dropout['camera_slots'], dropout['lidar_slots'], dropout['total_pose_slots']),
            (2, 2, 4)
        )
        self.assertEqual(dropout['physical_attribution'], 'UNRESOLVED')
