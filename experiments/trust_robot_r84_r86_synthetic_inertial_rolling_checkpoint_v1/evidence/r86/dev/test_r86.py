import copy
import unittest
import numpy as np
import r84_gap_frontend as gap
import r86_rolling as rolling

class RollingTests(unittest.TestCase):
    def test_clean_rolling_solves(self):
        r=rolling.solve(gap.fixture('continuous'))
        self.assertEqual((r['nonlinear_window_solves'],r['segments_with_independent_anchors'],r['inertial_pairs_integrated']),(2,1,8))
        self.assertTrue(all(w['jacobian_rank']==15 for w in r['windows']))
    def test_gap_reanchors(self):
        r=rolling.solve(gap.fixture('single_gap'))
        self.assertEqual((r['rejected_gap_pairs'],r['segments_with_independent_anchors'],r['inertial_pairs_integrated']),(1,2,7))
        self.assertEqual([w['synthetic_anchor_reset_here'] for w in r['windows']],[True,True])
    def test_clean_boundary_carries(self):
        r=rolling.solve(gap.fixture('continuous'))
        self.assertEqual([w['synthetic_anchor_reset_here'] for w in r['windows']],[True,False])
        self.assertEqual(r['windows'][0]['to_node'],r['windows'][1]['from_node'])
    def test_gap_disjoint(self):
        r=rolling.solve(gap.fixture('single_gap'))
        self.assertNotEqual(r['windows'][0]['to_node'],r['windows'][1]['from_node'])
        self.assertEqual(r['cross_gap_factor_count'],0)
    def test_solver_reduces_objective(self):
        r=rolling.solve(gap.fixture('continuous'))
        for w in r['windows']:
            self.assertGreater(w['initial_residual_norm'],100*w['final_residual_norm'])
            self.assertLess(w['final_residual_norm'],1e-6)
    def test_state_recovery(self):
        r=rolling.solve(gap.fixture('continuous'))
        self.assertLess(r['max_constructed_endpoint_recovery_error'],1e-4)
    def test_no_marginalization_claim(self):
        r=rolling.solve(gap.fixture('single_gap'))
        self.assertFalse(r['schur_marginalization_implemented'])
        self.assertTrue(all(not w['schur_marginalization_applied'] for w in r['windows']))
    def test_no_reference_truth_claim(self):
        r=rolling.solve(gap.fixture('continuous'))
        self.assertFalse(r['independent_gt_or_pose_used'])
        self.assertTrue(all(not w['constructed_endpoint_independent_reference'] for w in r['windows']))
    def test_gyro_case(self):
        r=rolling.solve(gap.fixture('gyro_injection'))
        self.assertEqual(r['nonlinear_window_solves'],2)
    def test_accel_case(self):
        r=rolling.solve(gap.fixture('accel_injection'))
        self.assertEqual(r['nonlinear_window_solves'],2)
    def test_repeat(self):
        a=rolling.solve(gap.fixture('single_gap'))
        b=rolling.solve(gap.fixture('single_gap'))
        self.assertEqual(a,b)
    def test_bad_boundary_rejected(self):
        with self.assertRaises(rolling.RollingError):
            rolling.constructed_endpoint(np.zeros(14),{})
    def test_unknown_real_packet_denied(self):
        a=gap.fixture('continuous');a[0]['source_id']='/handsfree/imu'
        with self.assertRaises((rolling.RollingError,gap.InertialAdmissionError)):
            rolling.solve(a)
    def test_train_packet_denied(self):
        a=gap.fixture('continuous');a[0]['split_role']='train'
        with self.assertRaises((rolling.RollingError,gap.InertialAdmissionError)):
            rolling.solve(a)
    def test_physical_clock_claim_denied(self):
        a=gap.fixture('continuous');a[0]['physical_clock_verified']=True
        with self.assertRaises((rolling.RollingError,gap.InertialAdmissionError)):
            rolling.solve(a)
    def test_duplicate_stamp_denied(self):
        a=gap.fixture('continuous');a[1]['timestamp_ns']=a[0]['timestamp_ns']
        with self.assertRaises((rolling.RollingError,gap.InertialAdmissionError)):
            rolling.solve(a)
    def test_reversed_stamp_denied(self):
        a=gap.fixture('continuous');a[1]['timestamp_ns']=a[0]['timestamp_ns']-1
        with self.assertRaises((rolling.RollingError,gap.InertialAdmissionError)):
            rolling.solve(a)
    def test_gt_claim_denied(self):
        a=gap.fixture('continuous');a[0]['reference_data_used']=True
        with self.assertRaises((rolling.RollingError,gap.InertialAdmissionError)):
            rolling.solve(a)
    def test_confirmation_denied(self):
        a=gap.fixture('continuous');a[0]['confirmation_test_accessed']=True
        with self.assertRaises((rolling.RollingError,gap.InertialAdmissionError)):
            rolling.solve(a)
    def test_no_safe_intervals(self):
        a=gap.fixture('continuous')
        for i,p in enumerate(a):p['timestamp_ns']=1_000_000_000+1_000_000_000*i
        with self.assertRaises((rolling.RollingError,gap.InertialAdmissionError)):
            rolling.solve(a)
    def test_nonfinite_axes_denied(self):
        a=gap.fixture('continuous');a[0]['gyro_rad_s']=[float('nan'),0,0]
        with self.assertRaises((rolling.RollingError,gap.InertialAdmissionError)):
            rolling.solve(a)

if __name__=='__main__':
    unittest.main(verbosity=2)
