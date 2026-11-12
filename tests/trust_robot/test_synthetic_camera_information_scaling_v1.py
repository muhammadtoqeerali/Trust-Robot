import unittest
from unittest.mock import patch
import numpy as np
from trust_robot import synthetic_camera_information_scaling_v1 as a
class CameraInformationScalingTests(unittest.TestCase):
    def test_origin_denied(self):
        for x in ('NOVA_LIVE','M2DGR','NOVA_RECORDED',None,1,{}):
            with self.subTest(x=x),self.assertRaises(a.Boundary):a.guard(x)
    def test_scientific_gates_closed(self):a.guard()
    def test_unexpectedly_open_gate_denied(self):
        with patch('trust_robot.factor_conditioning.assert_factor_scale_execution_authorized',return_value=None):
            with self.assertRaises(a.Boundary):a.guard()
    def test_wrong_condition_denied(self):
        with self.assertRaises(a.Boundary):a.evaluate('real',13,(0,1),1.0)
    def test_wrong_seed_denied(self):
        for s in (True,14,'13',13.0):
            with self.subTest(s=s),self.assertRaises(a.Boundary):a.evaluate('clean',s,(0,1),1.0)
    def test_wrong_edge_denied(self):
        with self.assertRaises(a.Boundary):a.evaluate('clean',13,(0,2),1.0)
    def test_wrong_scale_denied(self):
        for v in (1,0.75,1.5,True):
            with self.subTest(v=v),self.assertRaises(a.Boundary):a.evaluate('clean',13,(0,1),v)
    def test_canonical_determinism(self):
        self.assertEqual(a.canonical({'b':2,'a':1}),a.canonical({'a':1,'b':2}))
    def test_clean_identity_seed13(self):
        b=a.evaluate('clean',13,(0,1),1.0)
        h=a.evaluate('clean',13,(0,1),0.5)
        self.assertAlmostEqual(h['camera_translation_information_trace']/b['camera_translation_information_trace'],4.0,places=5)
        self.assertEqual(b['lidar_factors_unchanged'],7)
    def test_dropout_identity_seed31(self):
        b=a.evaluate('lidar_dropout',31,(2,3),1.0)
        h=a.evaluate('lidar_dropout',31,(2,3),2.0)
        self.assertAlmostEqual(h['camera_translation_information_trace']/b['camera_translation_information_trace'],0.25,places=5)
        self.assertEqual(h['lidar_shadow_holds_unchanged'],[2,3])
    def test_scientific_output_denied(self):
        x=a.evaluate('clean',13,(0,1),1.0)
        self.assertFalse(x['physical_calibration_established'])
        self.assertFalse(x['operational_factor_weighting_executed'])
        self.assertEqual(x['real_factor_admission'],'DENIED')
    def test_matrix_counts(self):
        r=a.execute()
        self.assertEqual(r['case_count'],24)
        self.assertEqual(r['comparison_count'],16)
        self.assertEqual(r['health_output'],'ABSTAIN')
