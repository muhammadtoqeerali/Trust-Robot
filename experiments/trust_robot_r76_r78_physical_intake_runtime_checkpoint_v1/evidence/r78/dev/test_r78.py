import copy
import pathlib
import sys
import unittest

import r78_runtime_boundary as m
import r77_bridge as bridge

REPO,P76,Q76,P77,Q77=map(pathlib.Path,sys.argv[1:])
sys.argv=[sys.argv[0]]

class RuntimeBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.args=(REPO,P76,Q76,P77,Q77)
        cls.gates,cls.snapshot=m.context(*cls.args)
        cls.claim=sorted(cls.gates)[0]

    def fixture(self,claim=None,filled=False,source='synthetic_fixture'):
        return bridge.synthetic_candidate(claim or self.claim,self.gates,source_class=source,filled=filled)

    def test_all_11_empty_candidates_are_format_only(self):
        for claim in self.gates:
            with self.subTest(claim=claim):
                v=m.inspect_format_only(self.fixture(claim),*self.args)
                self.assertFalse(v['recorded_factor_executable'])
                self.assertFalse(v['physical_source_admitted'])

    def test_all_11_filled_author_like_candidates_still_denied(self):
        for claim in self.gates:
            with self.subTest(claim=claim):
                v=m.inspect_format_only(self.fixture(claim,True,'author_source_candidate'),*self.args)
                self.assertEqual(v['status'],'FORMAT_ONLY_EXECUTION_DENIED')
                with self.assertRaises(m.RealExecutionDenied):
                    m.require_recorded_execution(self.fixture(claim,True,'author_source_candidate'),*self.args)

    def test_synthetic_looks_like_measurement_but_denied(self):
        x=self.fixture(filled=True,source='measurement_candidate')
        with self.assertRaises(m.RealExecutionDenied):
            m.require_recorded_execution(x,*self.args)

    def test_negative_authorization_injections(self):
        cases=(
            {'factor_execution_authorized':True},
            {'physical_validation_completed':True},
            {'confirmation_test_used':True},
            {'independent_validation_sha256':'b'*64},
            {'trajectory_id':'room_01'},
            {'split':'confirmation_test'},
            {'source_sha256':'NOT_SHA256'},
            {'claim_id':'unknown_r43_gate'},
        )
        for case in cases:
            with self.subTest(case=case):
                x=self.fixture()
                x.update(case)
                with self.assertRaises(m.RuntimeBoundaryError):
                    m.inspect_format_only(x,*self.args)

    def test_report_mutated_science_flags_rejected(self):
        r=m.json.loads((Q77/'r77_intake_sensor_factor_boundary_v1.json').read_text())
        i=m.json.loads((Q77/'r77_independent_validation_v1.json').read_text())
        for key,value in (
            ('scientific_gates_closed',10),
            ('real_pose_factors_authorized',True),
            ('physical_clock_qualified',True),
            ('historical_gates_checked',10),
            ('candidate_claim_names',[]),
        ):
            with self.subTest(key=key):
                bad=copy.deepcopy(r)
                bad[key]=value
                with self.assertRaises(m.RuntimeBoundaryError):
                    m.validate_receipts(bad,i)

    def test_independent_receipt_mutations_rejected(self):
        r=m.json.loads((Q77/'r77_intake_sensor_factor_boundary_v1.json').read_text())
        i=m.json.loads((Q77/'r77_independent_validation_v1.json').read_text())
        for key,value in (
            ('status','FAIL'),
            ('physical_sources_qualified',1),
            ('primary_result_sha256','0'*64),
            ('existing_sensor_factor_gates_remained_closed',False),
        ):
            with self.subTest(key=key):
                bad=copy.deepcopy(i)
                bad[key]=value
                with self.assertRaises(m.RuntimeBoundaryError):
                    m.validate_receipts(r,bad)

    def test_source_hash_tamper_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'r76_intake.py'
            p.write_bytes((P76/'r76_intake.py').read_bytes()+b' ')
            with self.assertRaises(m.RuntimeBoundaryError):
                m.require_pin(p,m.CODE_PINS['r76_intake.py'])

    def test_original_real_factor_gates_still_closed(self):
        self.assertTrue(bridge.assert_real_factor_gates_closed(self.snapshot))

    def test_no_boolean_approval_keyword_supported(self):
        x=self.fixture()
        x['authorization_override']=True
        with self.assertRaises(m.RuntimeBoundaryError):
            m.inspect_format_only(x,*self.args)

if __name__=='__main__':
    unittest.main(verbosity=2)
