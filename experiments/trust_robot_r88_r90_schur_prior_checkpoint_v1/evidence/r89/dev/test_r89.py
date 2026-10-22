import unittest
import numpy as np
import r84_gap_frontend as gap
import r89_prior as r

class PriorTests(unittest.TestCase):

    def simple(self):
        H = 3*np.eye(15)
        g = np.arange(15, dtype=float)/20.
        return H, g, 0.25

    def test_recenter_identity(self):
        H,g,c = self.simple()
        A,b,d = r.recenter(H,g,c,np.zeros(15))
        np.testing.assert_array_equal(A,H)
        np.testing.assert_array_equal(b,g)
        self.assertEqual(d,c)

    def test_recenter_minimizer(self):
        H,g,c = self.simple()
        x = np.linalg.solve(H,g)
        delta = np.ones(15)*.04
        A,b,d = r.recenter(H,g,c,delta)
        np.testing.assert_allclose(
            np.linalg.solve(A,b),
            x-delta,
            atol=1e-12
        )

    def test_recenter_energy(self):
        H,g,c = self.simple()
        d = np.ones(15)*.02
        A,b,e = r.recenter(H,g,c,d)
        x = np.arange(15)*.003
        self.assertAlmostEqual(
            r.quadratic(H,g,c,x),
            r.quadratic(A,b,e,x-d),
            places=11
        )

    def test_recenter_covariance(self):
        H,g,c = self.simple()
        A,_,_ = r.recenter(
            H,g,c,np.ones(15)*.02
        )
        np.testing.assert_allclose(
            np.linalg.inv(A),
            np.linalg.inv(H)
        )

    def test_nonzero_recenter_information(self):
        H,g,c = self.simple()
        _,b,_ = r.recenter(
            H,g,c,np.ones(15)*.02
        )
        self.assertFalse(np.array_equal(b,g))

    def test_relinearization_denied(self):
        H,g,c = self.simple()
        with self.assertRaises(r.PriorConsistencyError):
            r.recenter(
                H,g,c,np.zeros(15),
                operation='NONLINEAR_RELINEARIZE'
            )

    def test_reconstruct_deleted_factors_denied(self):
        with self.assertRaises(r.PriorConsistencyError):
            r.authorize_prior_operation(
                'RECONSTRUCT_ELIMINATED_FACTORS'
            )

    def test_indefinite_prior_denied(self):
        H,g,c = self.simple()
        with self.assertRaises(
            (r.PriorConsistencyError,ValueError)
        ):
            r.recenter(-H,g,c,np.zeros(15))

    def test_bad_shift_denied(self):
        H,g,c = self.simple()
        with self.assertRaises(r.PriorConsistencyError):
            r.recenter(H,g,c,np.zeros(14))

    def test_nonfinite_shift_denied(self):
        H,g,c = self.simple()
        d = np.zeros(15)
        d[0] = float('nan')
        with self.assertRaises(r.PriorConsistencyError):
            r.recenter(H,g,c,d)

    def test_bad_information_vector_denied(self):
        H,g,c = self.simple()
        with self.assertRaises(r.PriorConsistencyError):
            r.recenter(H,np.zeros(14),c,np.zeros(15))

    def test_nonfinite_constant_denied(self):
        H,g,_ = self.simple()
        with self.assertRaises(r.PriorConsistencyError):
            r.recenter(H,g,float('inf'),np.zeros(15))

    def test_clean_segment(self):
        x = r.run_case(
            gap.fixture('continuous')
        )
        self.assertEqual(
            (
                x['segments'],
                x['timestamp_gaps_rejected'],
                x['prior_recentered_segment_count']
            ),
            (1,0,1)
        )

    def test_gap_independent_priors(self):
        x = r.run_case(
            gap.fixture('single_gap')
        )
        self.assertEqual(
            (
                x['segments'],
                x['cross_gap_prior_carry_count']
            ),
            (2,0)
        )

    def test_full_batch_lineage(self):
        x = r.run_case(
            gap.fixture('continuous')
        )
        self.assertLess(
            x['segment_results'][0][
                'schur_vs_prior_full_batch_cost_abs_error'
            ],
            1e-5
        )

    def test_nonlinear_jacobian_changes(self):
        x = r.run_case(
            gap.fixture('continuous')
        )
        self.assertGreater(
            x['nonlinear_audits'][0][
                'relinearized_jacobian_relative_change'
            ],
            1e-10
        )

    def test_recenter_determinism(self):
        packets = gap.fixture('single_gap')
        self.assertEqual(
            r.run_case(packets),
            r.run_case(packets)
        )

    def test_real_source_denied(self):
        packets = gap.fixture('continuous')
        packets[0]['source_id'] = '/camera/imu'
        with self.assertRaises((
            gap.InertialAdmissionError,
            r.PriorConsistencyError
        )):
            r.run_case(packets)

    def test_confirmation_denied(self):
        packets = gap.fixture('continuous')
        packets[0]['confirmation_test_accessed'] = True
        with self.assertRaises((
            gap.InertialAdmissionError,
            r.PriorConsistencyError
        )):
            r.run_case(packets)

    def test_wrong_split_denied(self):
        packets = gap.fixture('continuous')
        packets[0]['split_role'] = 'train'
        with self.assertRaises((
            gap.InertialAdmissionError,
            r.PriorConsistencyError
        )):
            r.run_case(packets)

    def test_reversed_stamp_denied(self):
        packets = gap.fixture('continuous')
        packets[1]['timestamp_ns'] = (
            packets[0]['timestamp_ns'] - 1
        )
        with self.assertRaises((
            gap.InertialAdmissionError,
            r.PriorConsistencyError
        )):
            r.run_case(packets)


if __name__ == '__main__':
    unittest.main(verbosity=2)
