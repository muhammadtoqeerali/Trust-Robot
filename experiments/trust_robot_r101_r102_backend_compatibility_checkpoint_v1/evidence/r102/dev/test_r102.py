import copy
import unittest

import r102_compatibility as m

class Tests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.report=m.execute()

    def test_schema(self):
        self.assertEqual(self.report['schema'],m.SCHEMA)

    def test_status(self):
        self.assertEqual(
            self.report['status'],
            'PASS_FAIL_CLOSED_COMPATIBILITY_AUDIT'
        )

    def test_shared_dimension(self):
        self.assertTrue(self.report['shared_15d_state_size'])

    def test_shared_residual(self):
        self.assertTrue(
            self.report['shared_inertial_residual_function']
        )

    def test_eight_blockers(self):
        self.assertEqual(
            self.report['compatibility_blocker_count'],8
        )

    def test_frame_mismatch(self):
        self.assertIn(
            m.REASONS[0],
            self.report['compatibility_blockers']
        )

    def test_clock_mismatch(self):
        self.assertIn(
            m.REASONS[1],
            self.report['compatibility_blockers']
        )

    def test_duration_mismatch(self):
        self.assertEqual(
            self.report['source']['window_duration_ns'],
            100000000
        )
        self.assertEqual(
            self.report['target']['window_duration_ns'],
            200000000
        )

    def test_anchor_mismatch(self):
        self.assertIn(
            m.REASONS[3],
            self.report['compatibility_blockers']
        )

    def test_prior_dimension_mismatch(self):
        self.assertEqual(
            self.report['source']['prior_dimension'],15
        )
        self.assertEqual(
            self.report['target']['prior_dimension'],30
        )

    def test_prior_node_ids(self):
        self.assertEqual(
            self.report['source']['retained_node_ids'],
            [100]
        )
        self.assertEqual(
            self.report['target']['retained_node_ids'],
            [1,2]
        )

    def test_regularization_not_equated(self):
        self.assertIn(
            m.REASONS[6],
            self.report['compatibility_blockers']
        )

    def test_factor_history_unmapped(self):
        self.assertIn(
            m.REASONS[7],
            self.report['compatibility_blockers']
        )

    def test_three_real_s6_marginalizations(self):
        self.assertEqual(
            self.report['target']['actual_marginalizations'],
            3
        )

    def test_factor_ledger_disjoint(self):
        t=self.report['target']
        self.assertFalse(
            set(t['consumed_pose_ids'])
            &set(t['remaining_pose_ids'])
        )

    def test_r95_fingerprint_present(self):
        self.assertEqual(
            len(self.report['source']['record_fingerprint']),
            64
        )

    def test_binding_denied(self):
        with self.assertRaises(m.CompatibilityError):
            m.bind_to_live_s6(
                self.report['source'],
                self.report['target']
            )

    def test_spoofed_profiles_still_denied(self):
        source=copy.deepcopy(self.report['source'])
        target=copy.deepcopy(self.report['target'])

        for key in (
            'frame_namespace','timestamp_epoch_ns',
            'window_duration_ns','initial_anchor',
            'prior_dimension','retained_node_ids'
        ):
            source[key]=copy.deepcopy(target[key])

        with self.assertRaises(m.CompatibilityError):
            m.bind_to_live_s6(source,target)

    def test_incomplete_profile_rejected(self):
        with self.assertRaises(m.CompatibilityError):
            m.diagnose({},self.report['target'])

    def test_bad_anchor_rejected(self):
        a=copy.deepcopy(self.report['source'])
        a['initial_anchor']=[0]*14

        with self.assertRaises(m.CompatibilityError):
            m.diagnose(a,self.report['target'])

    def test_no_backend_merger(self):
        self.assertFalse(
            self.report['r95_backend_merged_into_s6']
        )

    def test_no_physical_alignment(self):
        self.assertFalse(
            self.report['source_trajectory_alignment_verified']
        )

    def test_no_real_factors(self):
        self.assertFalse(
            self.report['real_sensor_factors_authorized']
        )

    def test_no_health_or_ate(self):
        self.assertFalse(
            self.report['health_training_authorized']
        )
        self.assertFalse(
            self.report['ate_rpe_authorized']
        )

    def test_confirmation_sealed(self):
        self.assertFalse(
            self.report['confirmation_test_accessed']
        )

    def test_synthetic_only(self):
        self.assertFalse(
            self.report['raw_gt_or_rosbags_opened']
        )
        self.assertEqual(
            self.report['scientific_gates_closed'],11
        )

    def test_deterministic(self):
        self.assertEqual(
            m.canonical(self.report),
            m.canonical(m.execute())
        )

if __name__=='__main__':
    unittest.main(verbosity=2)
