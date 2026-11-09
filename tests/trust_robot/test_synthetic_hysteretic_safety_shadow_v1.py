import copy
import unittest
from trust_robot.synthetic_hysteretic_safety_shadow_v1 import (
    MODALITIES, TestOnlyWindows, ShadowTimelineContractError,
    synth_frame, simulate_shadow_timeline,
)

def hd(camera='healthy',imu='healthy',lidar='healthy'):
    return {'camera':camera,'imu':imu,'lidar':lidar}

def sequence_camera_fault():
    return [synth_frame(0),synth_frame(1,health=hd(camera='unusable')),
            synth_frame(2,health=hd(camera='unusable')),
            synth_frame(3,health=hd(camera='healthy')),
            synth_frame(4,health=hd(camera='healthy')),
            synth_frame(5,health=hd(camera='healthy'))]

class TimelineTests(unittest.TestCase):
    def test_healthy_nominal(self):
        r=simulate_shadow_timeline([synth_frame(0)])
        self.assertEqual(r['trace'][0]['decision'],'SHADOW_NOMINAL_CONTINUATION_CANDIDATE_ONLY')
    def test_first_fault_pending(self):
        r=simulate_shadow_timeline(sequence_camera_fault())
        self.assertIn('SHADOW_SUPPRESSION_PENDING_CAMERA',r['trace'][1]['shadow_events'])
        self.assertEqual(r['trace'][1]['shadow_suppressed_modalities'],[])
    def test_second_fault_is_shadow_suppressed(self):
        r=simulate_shadow_timeline(sequence_camera_fault())
        self.assertIn('SHADOW_SUPPRESSION_COMPLETED_CAMERA',r['trace'][2]['shadow_events'])
        self.assertEqual(r['trace'][2]['shadow_suppressed_modalities'],['camera'])
        self.assertEqual(r['trace'][2]['decision'],'SHADOW_DEGRADED_CONTINUATION_CANDIDATE_ONLY')
    def test_recovery_needs_three_windows(self):
        r=simulate_shadow_timeline(sequence_camera_fault())
        self.assertEqual(r['trace'][4]['shadow_suppressed_modalities'],['camera'])
        self.assertEqual(r['trace'][5]['shadow_suppressed_modalities'],[])
        self.assertIn('SHADOW_RECOVERY_COMPLETED_CAMERA',r['trace'][5]['shadow_events'])
    def test_no_auto_health_from_delivery_gap(self):
        r=simulate_shadow_timeline([synth_frame(0,delivery=hd(camera='missing',imu='present',lidar='present'),health=hd()),
                                    synth_frame(1,delivery=hd(camera='missing',imu='present',lidar='present'),health=hd())])
        self.assertTrue(all(not x['shadow_suppressed_modalities'] for x in r['trace']))
        self.assertTrue(all(x['decision']=='SHADOW_SAFE_HOLD_REVIEW_REQUEST' for x in r['trace']))
    def test_unknown_health_no_suppression(self):
        r=simulate_shadow_timeline([synth_frame(0,health=hd(camera='unknown'))])
        self.assertEqual(r['trace'][0]['decision'],'SHADOW_SAFE_HOLD_REVIEW_REQUEST')
    def test_support_unverified_blocks_suppression(self):
        r=simulate_shadow_timeline([synth_frame(i,health=hd(camera='unusable'),support='unverified') for i in range(3)])
        self.assertEqual(r['trace'][2]['shadow_suppressed_modalities'],[])
        self.assertIn('SHADOW_SUPPRESSION_BLOCKED_SUPPORT_CAMERA',r['trace'][2]['shadow_events'])
    def test_support_insufficient_blocks_suppression(self):
        r=simulate_shadow_timeline([synth_frame(i,health=hd(camera='unusable'),support='fixture_insufficient') for i in range(3)])
        self.assertEqual(r['trace'][2]['shadow_suppressed_modalities'],[])
    def test_no_alternative_blocks_suppression(self):
        r=simulate_shadow_timeline([synth_frame(i,health=hd('unusable','unusable','unusable')) for i in range(2)])
        self.assertEqual(r['trace'][1]['shadow_suppressed_modalities'],[])
    def test_missing_delivery_cannot_trigger_recovery(self):
        s=sequence_camera_fault()[:3]+[synth_frame(i,health=hd(),delivery=hd('missing','present','present')) for i in range(3,6)]
        r=simulate_shadow_timeline(s)
        self.assertEqual(r['trace'][-1]['shadow_suppressed_modalities'],['camera'])
    def test_one_recovered_then_unusable_restarts_recovery(self):
        s=sequence_camera_fault()[:3]+[synth_frame(3),synth_frame(4,health=hd('unusable')),synth_frame(5),synth_frame(6)]
        r=simulate_shadow_timeline(s)
        self.assertEqual(r['trace'][-1]['shadow_suppressed_modalities'],['camera'])
    def test_return_unverified_route_holds(self):
        r=simulate_shadow_timeline([synth_frame(0,return_requested=True,route='unverified')])
        self.assertEqual(r['trace'][0]['decision'],'SHADOW_SAFE_HOLD_REVIEW_REQUEST')
    def test_return_fixture_safe_candidate_only(self):
        r=simulate_shadow_timeline([synth_frame(0,return_requested=True)])
        self.assertEqual(r['trace'][0]['decision'],'SHADOW_RETURN_HOME_CANDIDATE_ONLY')
        self.assertFalse(r['trace'][0]['return_home_execution_authorized'])
    def test_cross_modal_disagreement_no_attribution(self):
        r=simulate_shadow_timeline([synth_frame(0,consistency='unattributed_disagreement')])
        self.assertEqual(r['trace'][0]['decision'],'SHADOW_SAFE_HOLD_REVIEW_REQUEST')
        self.assertIn('CONSISTENCY_UNRESOLVED',r['trace'][0]['reason_codes'])
    def test_solver_failure_holds(self):
        r=simulate_shadow_timeline([synth_frame(0,solver='invalid')]);self.assertEqual(r['trace'][0]['decision'],'SHADOW_SAFE_HOLD_REVIEW_REQUEST')
    def test_tracking_loss_holds(self):
        r=simulate_shadow_timeline([synth_frame(0,tracking='lost')]);self.assertEqual(r['trace'][0]['decision'],'SHADOW_SAFE_HOLD_REVIEW_REQUEST')
    def test_invalid_frame_origin_refused(self):
        x=synth_frame(0);x['origin']='REAL';
        with self.assertRaises(ShadowTimelineContractError):simulate_shadow_timeline([x])
    def test_nonconsecutive_indexes_refused(self):
        with self.assertRaises(ShadowTimelineContractError):simulate_shadow_timeline([synth_frame(0),synth_frame(2)])
    def test_missing_modality_refused(self):
        x=synth_frame(0);del x['health']['imu'];
        with self.assertRaises(ShadowTimelineContractError):simulate_shadow_timeline([x])
    def test_extra_field_refused(self):
        x=synth_frame(0);x['physical_health_probability']=1;
        with self.assertRaises(ShadowTimelineContractError):simulate_shadow_timeline([x])
    def test_bad_test_threshold_refused(self):
        for value in (True,0,65,2.0):
            with self.subTest(value=value):
                with self.assertRaises(ShadowTimelineContractError):TestOnlyWindows(entry=value)
    def test_untuned_parameters_explicit(self):
        r=simulate_shadow_timeline([synth_frame(0)]);self.assertEqual((r['test_only_entry_windows'],r['test_only_recovery_windows']),(2,3))
    def test_never_issues_robot_command(self):
        r=simulate_shadow_timeline(sequence_camera_fault())
        self.assertTrue(all(x['robot_command'] is None and not x['physical_suppression_executed'] for x in r['trace']))
        self.assertIsNone(r['robot_command'])
    def test_input_immutable(self):
        x=sequence_camera_fault(); y=copy.deepcopy(x);simulate_shadow_timeline(x);self.assertEqual(x,y)
    def test_deterministic(self):
        x=sequence_camera_fault();self.assertEqual(simulate_shadow_timeline(x),simulate_shadow_timeline(x))
    def test_boolean_frame_index_refused(self):
        x=synth_frame(True)
        with self.assertRaises(ShadowTimelineContractError):simulate_shadow_timeline([x])
    def test_bounded_frame_count(self):
        with self.assertRaises(ShadowTimelineContractError):simulate_shadow_timeline([])
        with self.assertRaises(ShadowTimelineContractError):simulate_shadow_timeline([synth_frame(i) for i in range(129)])
    def test_shadow_not_physical(self):
        r=simulate_shadow_timeline(sequence_camera_fault())
        self.assertEqual(r['real_health_state'],'UNKNOWN_NOT_INFERRED')
        self.assertEqual(r['real_factor_admission'],'DENIED')
        self.assertFalse(r['physical_safety_claim'])

if __name__ == '__main__': unittest.main()
