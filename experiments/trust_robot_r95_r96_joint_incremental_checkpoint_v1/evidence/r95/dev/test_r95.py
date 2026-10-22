import copy
import json
import unittest

import numpy as np

import r84_gap_frontend as gap
import r90_prior_guard as guard
import r95_incremental as m

class LifecycleTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.report=m.execute()

    def test_four_scenarios(self):
        self.assertEqual(
            self.report['synthetic_scenarios'],4
        )

    def test_all_windows(self):
        self.assertEqual(
            self.report['incremental_prefix_windows'],16
        )

    def test_marginalization_count(self):
        self.assertEqual(
            self.report['marginalized_old_states'],11
        )

    def test_single_gap(self):
        g=self.report['cases']['single_gap']
        self.assertEqual(g['segments'],2)
        self.assertEqual(g['timestamp_gaps'],1)

    def test_no_cross_gap_prior(self):
        for case in self.report['cases'].values():
            self.assertEqual(
                case['cross_gap_prior_carries'],0
            )
            for row in case['rows']:
                self.assertFalse(
                    row['prior_copied_from_previous_segment']
                )

    def test_new_anchor_for_every_segment(self):
        for case in self.report['cases'].values():
            for row in case['rows']:
                self.assertTrue(
                    row['first_window_new_anchor']
                )

    def test_batch_checks(self):
        for case in self.report['cases'].values():
            for row in case['rows']:
                for w in row['windows']:
                    self.assertLess(
                        w['full_batch_state_l2_error'],1e-4
                    )
                    self.assertLess(
                        w['full_batch_cost_abs_error'],1e-5
                    )

    def test_condensed_information_checks(self):
        for case in self.report['cases'].values():
            for row in case['rows']:
                for w in row['windows']:
                    self.assertLess(
                        w['information_max_abs_error'],1e-7
                    )

    def test_no_health_labels(self):
        self.assertFalse(
            self.report['health_labels_generated']
        )

    def test_no_real_factor_permission(self):
        self.assertFalse(
            self.report['real_sensor_factors_executed']
        )

    def test_invalid_scenario_denied(self):
        with self.assertRaises(m.LifecycleError):
            m.run_case('room_02')

    def test_recorded_source_denied(self):
        packets=copy.deepcopy(gap.fixture('continuous'))
        packets[0]['source_id']='/camera/imu'
        with self.assertRaises(
            gap.InertialAdmissionError
        ):
            m.run_case('continuous',packets)

    def test_confirmation_packet_denied(self):
        packets=copy.deepcopy(gap.fixture('continuous'))
        packets[0]['confirmation_test_accessed']=True
        with self.assertRaises(
            gap.InertialAdmissionError
        ):
            m.run_case('continuous',packets)

    def test_physical_clock_claim_denied(self):
        packets=copy.deepcopy(gap.fixture('continuous'))
        packets[0]['physical_clock_verified']=True
        with self.assertRaises(
            gap.InertialAdmissionError
        ):
            m.run_case('continuous',packets)

    def test_stale_token_denied(self):
        rec=guard.make_record(
            np.eye(15),np.zeros(15),0.,0
        )
        with self.assertRaises(
            guard.PriorAdmissionError
        ):
            guard.admit(
                rec,0,'STALE_TOKEN',np.zeros(15)
            )

    def test_cross_gap_reuse_denied(self):
        rec=guard.make_record(
            np.eye(15),np.zeros(15),0.,0
        )
        with self.assertRaises(
            guard.PriorAdmissionError
        ):
            guard.admit(
                rec,1,guard.token(0),np.zeros(15)
            )

    def test_fingerprint_tamper_denied(self):
        rec=guard.make_record(
            np.eye(15),np.zeros(15),0.,0
        )
        rec['g'][0]=1.
        with self.assertRaises(
            guard.PriorAdmissionError
        ):
            guard.validate(rec)

    def test_nonlinear_refresh_denied(self):
        rec=guard.make_record(
            np.eye(15),np.zeros(15),0.,0
        )
        with self.assertRaises(
            guard.PriorAdmissionError
        ):
            guard.admit(
                rec,0,guard.token(0),np.zeros(15),
                operation='NONLINEAR_RELINEARIZE'
            )

    def test_excessive_recentering_denied(self):
        rec=guard.make_record(
            np.eye(15),np.zeros(15),0.,0
        )
        with self.assertRaises(
            guard.PriorAdmissionError
        ):
            guard.admit(
                rec,0,guard.token(0),np.ones(15)*0.1
            )

if __name__=='__main__':
    unittest.main(verbosity=2)
