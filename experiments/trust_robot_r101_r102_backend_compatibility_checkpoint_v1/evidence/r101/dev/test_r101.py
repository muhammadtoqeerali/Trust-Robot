import copy
import unittest
import numpy as np

import r101_prior_adapter as m
import r90_prior_guard as guard

from trust_robot.analytic_schur_marginalization import (
    SquareRootInformationPrior,
)

class Tests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.report=m.execute()

    def record(self):
        H=np.diag(
            np.linspace(10.,30.,15)
        )
        g=np.linspace(-0.5,0.5,15)
        return guard.make_record(
            H,g,0.25,0
        )

    def convert(self,record=None,**overrides):
        args={
            'segment_id':0,
            'expected_token':guard.token(0),
            'source_space':m.LOCAL_SPACE,
            'target_space':m.LOCAL_SPACE,
            'node_id':100,
            'reference':np.zeros(15),
        }
        args.update(overrides)
        return m.bridge(
            self.record() if record is None else record,
            **args
        )

    def test_schema(self):
        self.assertEqual(
            self.report['schema'],m.SCHEMA
        )

    def test_four_scenarios(self):
        self.assertEqual(
            self.report['scenarios'],4
        )

    def test_sixteen_prior_conversions(self):
        self.assertEqual(
            self.report[
                'converted_gaussian_prior_prefixes'
            ],16
        )

    def test_five_segments(self):
        self.assertEqual(
            self.report['independent_synthetic_segments'],
            5
        )

    def test_timestamp_gap(self):
        self.assertEqual(
            self.report['timestamp_gaps'],1
        )

    def test_square_root_type(self):
        result=self.convert()
        self.assertIsInstance(
            result['prior'],
            SquareRootInformationPrior
        )

    def test_normal_equation_reconstruction(self):
        r=self.convert()
        self.assertLess(
            r['information_relative_error'],1e-9
        )
        self.assertLess(
            r['gradient_relative_error'],1e-9
        )

    def test_quadratic_energy(self):
        self.assertLess(
            self.convert()['max_energy_relative_error'],
            1e-7
        )

    def test_nonzero_reference(self):
        ref=np.linspace(-0.002,0.002,15)
        r=self.convert(reference=ref)
        np.testing.assert_allclose(
            r['prior'].reference,
            ref
        )

    def test_source_copy_not_aliased(self):
        record=self.record()
        result=self.convert(record)
        previous=result['prior'].square_root_information.copy()
        record['H'][0,0]=1000.
        np.testing.assert_array_equal(
            result['prior'].square_root_information,
            previous
        )

    def test_no_live_s6_binding(self):
        self.assertFalse(
            self.report[
                's6_nonlinear_node_binding_authorized'
            ]
        )

    def test_direct_binding_denied(self):
        with self.assertRaises(m.BridgeError):
            m.bind_to_s6_nonlinear_solver(
                self.convert()
            )

    def test_wrong_target_frame_denied(self):
        with self.assertRaises(m.BridgeError):
            self.convert(
                target_space=m.S6_SPACE
            )

    def test_wrong_source_frame_denied(self):
        with self.assertRaises(m.BridgeError):
            self.convert(
                source_space='M2DGR_BODY'
            )

    def test_live_node_denied(self):
        with self.assertRaises(m.BridgeError):
            self.convert(node_id=1)

    def test_stale_token_denied(self):
        with self.assertRaises(m.BridgeError):
            self.convert(expected_token='STALE')

    def test_cross_gap_segment_denied(self):
        with self.assertRaises(m.BridgeError):
            self.convert(segment_id=1,node_id=101)

    def test_invalid_reference_denied(self):
        with self.assertRaises(m.BridgeError):
            self.convert(reference=np.zeros(14))

    def test_nonfinite_reference_denied(self):
        ref=np.zeros(15)
        ref[0]=float('nan')
        with self.assertRaises(m.BridgeError):
            self.convert(reference=ref)

    def test_fingerprint_tamper_denied(self):
        record=self.record()
        record['g'][0]=7.
        with self.assertRaises(
            guard.PriorAdmissionError
        ):
            self.convert(record)

    def test_physical_claim_denied(self):
        record=self.record()
        record['physical_clock_verified']=True
        with self.assertRaises(
            guard.PriorAdmissionError
        ):
            self.convert(record)

    def test_real_factor_claim_denied(self):
        record=self.record()
        record['real_factor_executable']=True
        with self.assertRaises(
            guard.PriorAdmissionError
        ):
            self.convert(record)

    def test_recorded_source_denied(self):
        record=self.record()
        record['source']='RECORDED_M2DGR'
        with self.assertRaises(
            guard.PriorAdmissionError
        ):
            self.convert(record)

    def test_singular_prior_denied(self):
        record=self.record()
        record['H'][0,0]=0.
        with self.assertRaises(
            guard.PriorAdmissionError
        ):
            self.convert(record)

    def test_missing_field_denied(self):
        record=self.record()
        del record['anchor']
        with self.assertRaises(
            guard.PriorAdmissionError
        ):
            self.convert(record)

    def test_confirmation_not_accessed(self):
        self.assertFalse(
            self.report['confirmation_test_accessed']
        )

    def test_r95_not_merged(self):
        self.assertFalse(
            self.report[
                'r95_gaussian_backend_merged_into_s6'
            ]
        )

    def test_repeat_determinism(self):
        self.assertEqual(
            m.canonical(self.report),
            m.canonical(m.execute())
        )

if __name__=='__main__':
    unittest.main(verbosity=2)
