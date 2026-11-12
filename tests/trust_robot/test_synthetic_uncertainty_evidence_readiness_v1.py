import unittest
from unittest.mock import patch
from trust_robot import synthetic_uncertainty_evidence_readiness_v1 as a

class ReadinessTests(unittest.TestCase):
    def test_guard_closed(self): a.guard()
    def test_reject_physical(self):
        for x in ('NOVA_LIVE','M2DGR',None,7,{},'ANALYTIC_FIXTURE'):
            with self.subTest(x=x),self.assertRaises(a.Boundary):a.guard(x)
    def test_unexpected_phase5_open_refused(self):
        with patch('trust_robot.multimodal_health_model.assert_training_authorized',return_value=None):
            with self.assertRaises(a.Boundary):a.guard()
    def test_unexpected_phase6_open_refused(self):
        with patch('trust_robot.probabilistic_calibration.assert_calibration_execution_authorized',return_value=None):
            with self.assertRaises(a.Boundary):a.guard()
    def test_unexpected_phase8_open_refused(self):
        with patch('trust_robot.factor_conditioning.assert_factor_scale_execution_authorized',return_value=None):
            with self.assertRaises(a.Boundary):a.guard()
    def test_canonical_stable(self):self.assertEqual(a.canonical({'b':2,'a':1}),a.canonical({'a':1,'b':2}))
    def test_contract_refuses_invalid_root(self):
        with self.assertRaises(a.Boundary):a.documents('/nonexistent/private/contract/root')
    def test_contract_refuses_nonpath(self):
        with self.assertRaises(a.Boundary):a.documents({})
    def test_no_synthetic_calibration_as_empirical(self):
        with patch.object(a,'documents',return_value={'fake':{'sha256':'0'*64}}):
            x=a.assess('/tmp')
        self.assertFalse(x['synthetic_information_scaling_is_empirical_covariance'])
    def test_health_abstains(self):
        with patch.object(a,'documents',return_value={}):x=a.assess('/tmp')
        self.assertEqual(x['physical_health_classification'],'ABSTAIN')
    def test_gate_crosswalk_preserves_counts(self):
        with patch.object(a,'documents',return_value={}):x=a.assess('/tmp')
        self.assertEqual((x['existing_evidence_request_count_per_published_a23'],x['existing_m2dgr_gates_closed_per_published_evidence']),(13,11))
    def test_never_operational(self):
        with patch.object(a,'documents',return_value={}):x=a.assess('/tmp')
        self.assertEqual((x['real_factor_admission'],x['operational_factor_weighting'],x['robot_actuation']),('DENIED','DENIED','DENIED'))
