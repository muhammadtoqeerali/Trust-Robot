import copy
import unittest

import numpy as np

import r84_gap_frontend as gap
import r90_prior_guard as g


class PriorGuardTests(unittest.TestCase):

    def record(self):
        H = 3*np.eye(15)
        info = np.arange(15, dtype=float)/10
        return g.make_record(
            H, info, 0.25, 0
        )

    def test_valid_prior(self):
        self.assertEqual(
            g.validate(self.record())[3],
            1.0
        )

    def test_valid_recenter(self):
        r = self.record()

        v = g.admit(
            r, 0, g.token(0),
            np.ones(15)*0.0001
        )

        self.assertLess(
            v['quadratic_energy_abs_error'],
            1e-5
        )

    def test_optimum_invariance(self):
        v = g.admit(
            self.record(), 0, g.token(0),
            np.ones(15)*0.0001
        )

        self.assertLess(
            v['optimum_transform_l2_error'],
            1e-6
        )

    def test_covariance_invariance(self):
        v = g.admit(
            self.record(), 0, g.token(0),
            np.zeros(15)
        )

        self.assertLess(
            v['covariance_invariance_l2_error'],
            1e-12
        )

    def reject_record(self, change):
        r = self.record()
        change(r)

        with self.assertRaises(g.PriorAdmissionError):
            g.validate(r)

    def test_matrix_tampering(self):
        self.reject_record(
            lambda r: r['H'].__setitem__((0, 0), 9.)
        )

    def test_information_vector_tampering(self):
        self.reject_record(
            lambda r: r['g'].__setitem__(0, 99.)
        )

    def test_constant_tampering(self):
        self.reject_record(
            lambda r: r.update(c=99.)
        )

    def test_fingerprint_tampering(self):
        self.reject_record(
            lambda r: r.update(fingerprint='bad')
        )

    def test_unanchored_prior_rejected(self):
        self.reject_record(
            lambda r: r.update(anchor_fixed=False)
        )

    def test_real_source_rejected(self):
        self.reject_record(
            lambda r: r.update(source='RECORDED_IMU')
        )

    def test_unauthorized_factor_rejected(self):
        self.reject_record(
            lambda r: r.update(real_factor_executable=True)
        )

    def test_physical_clock_claim_rejected(self):
        self.reject_record(
            lambda r: r.update(physical_clock_verified=True)
        )

    def test_missing_field_rejected(self):
        self.reject_record(
            lambda r: r.pop('anchor')
        )

    def test_cross_segment_rejected(self):
        with self.assertRaises(g.PriorAdmissionError):
            g.admit(
                self.record(), 1, g.token(0),
                np.zeros(15)
            )

    def test_stale_linearization_rejected(self):
        with self.assertRaises(g.PriorAdmissionError):
            g.admit(
                self.record(), 0, 'STALE',
                np.zeros(15)
            )

    def test_nonlinear_refresh_rejected(self):
        with self.assertRaises(g.PriorAdmissionError):
            g.admit(
                self.record(), 0, g.token(0),
                np.zeros(15),
                operation='NONLINEAR_RELINEARIZE'
            )

    def test_excessive_shift_rejected(self):
        with self.assertRaises(g.PriorAdmissionError):
            g.admit(
                self.record(), 0, g.token(0),
                np.ones(15)*0.1
            )

    def test_nonfinite_shift_rejected(self):
        d = np.zeros(15)
        d[0] = float('nan')

        with self.assertRaises(g.PriorAdmissionError):
            g.admit(
                self.record(), 0, g.token(0), d
            )

    def test_singular_prior_rejected(self):
        with self.assertRaises(g.PriorAdmissionError):
            g.make_record(
                np.diag([0.]+[1.]*14),
                np.zeros(15), 0., 0
            )

    def test_near_singular_prior_rejected(self):
        with self.assertRaises(g.PriorAdmissionError):
            g.make_record(
                np.diag([1e-16]+[1.]*14),
                np.zeros(15), 0., 0
            )

    def test_asymmetric_prior_rejected(self):
        H = np.eye(15)
        H[0, 1] = 0.2

        with self.assertRaises(g.PriorAdmissionError):
            g.make_record(
                H, np.zeros(15), 0., 0
            )

    def test_nonfinite_prior_rejected(self):
        H = np.eye(15)
        H[0, 0] = float('inf')

        with self.assertRaises(g.PriorAdmissionError):
            g.make_record(
                H, np.zeros(15), 0., 0
            )

    def test_timestamp_gap_disconnected(self):
        result = g.audit_case(
            gap.fixture('single_gap')
        )

        self.assertEqual(
            result['segments'], 2
        )
        self.assertEqual(
            result['cross_gap_prior_carry_count'], 0
        )

    def test_attack_count(self):
        result = g.audit_case(
            gap.fixture('continuous')
        )

        self.assertEqual(
            result['adversarial_rejections'], 6
        )

    def test_repeat_determinism(self):
        packets = gap.fixture('single_gap')

        self.assertEqual(
            g.audit_case(packets),
            g.audit_case(packets)
        )

    def test_recorded_imu_packet_rejected(self):
        packets = gap.fixture('continuous')
        packets[0]['source_id'] = '/camera/imu'

        with self.assertRaises(
            gap.InertialAdmissionError
        ):
            g.audit_case(packets)

    def test_confirmation_packet_rejected(self):
        packets = gap.fixture('continuous')
        packets[0]['confirmation_test_accessed'] = True

        with self.assertRaises(
            gap.InertialAdmissionError
        ):
            g.audit_case(packets)


if __name__ == '__main__':
    unittest.main(verbosity=2)
