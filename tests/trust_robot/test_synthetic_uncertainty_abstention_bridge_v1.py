import copy
import unittest
from trust_robot import synthetic_uncertainty_abstention_bridge_v1 as a
from trust_robot.synthetic_tri_modal_consistency_limits_v1 import execute as tri_execute
from trust_robot.synthetic_joint_fault_identifiability_v1 import execute as joint_execute

class AbstentionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tri=tri_execute()
        cls.joint=joint_execute()
        cls.out=a.evaluate(cls.tri,cls.joint)
    def test_count(self): self.assertEqual(self.out['synthetic_case_count'],8)
    def test_all_abstain(self): self.assertTrue(all(x['uncertainty_decision']=='ABSTAIN_UNCALIBRATED_REAL_HEALTH' for x in self.out['cases']))
    def test_no_weight(self): self.assertFalse(self.out['operational_factor_weight_updates'])
    def test_no_real_factor(self): self.assertEqual(self.out['real_factor_admission'],'DENIED')
    def test_source_unknown(self): self.assertEqual(self.out['physical_culprit'],'UNRESOLVED')
    def test_two_shared_examples(self): self.assertEqual(self.out['all_three_common_translation_gauge_examples'],2)
    def test_matched_seed_common_blind_pair(self):
        for x in self.out['cases']:
            if x['scenario']=='joint_common_mode':
                self.assertEqual(x['pairwise_contrast'][a.METRICS[0]],'UNCHANGED_SYNTHETIC_ONLY')
    def test_third_proxy_changes(self):
        for x in self.out['cases']:
            if x['scenario']=='joint_common_mode':
                self.assertEqual(x['pairwise_contrast'][a.METRICS[1]],'CHANGED_SYNTHETIC_ONLY')
    def test_dropout_holds(self):
        row=next(x for x in self.out['cases'] if x['scenario']=='dropout_and_camera')
        self.assertEqual(row['held_windows'],[2,3])
    def test_no_held_windows_other_cases(self):
        self.assertTrue(all(not x['held_windows'] for x in self.out['cases'] if x['scenario']!='dropout_and_camera'))
    def test_reproducible(self): self.assertEqual(a.canonical(self.out),a.canonical(a.evaluate(self.tri,self.joint)))
    def test_reject_bad_report_schema(self):
        bad=copy.deepcopy(self.tri);bad['schema']='BAD'
        with self.assertRaises(a.EvidenceDenied): a.evaluate(bad,self.joint)
    def test_reject_health_claim(self):
        bad=copy.deepcopy(self.tri);bad['calibrated_health_probabilities_available']=True
        with self.assertRaises(a.EvidenceDenied): a.evaluate(bad,self.joint)
    def test_reject_metric_tampering(self):
        bad=copy.deepcopy(self.tri);bad['eight_manufactured_factor_cases'][0]['triad'][a.METRICS[0]]=float('nan')
        with self.assertRaises(a.EvidenceDenied): a.evaluate(bad,self.joint)
    def test_reject_duplicate_case(self):
        bad=copy.deepcopy(self.tri);bad['eight_manufactured_factor_cases'][1]['scenario']='baseline'
        with self.assertRaises(a.EvidenceDenied): a.evaluate(bad,self.joint)
    def test_reject_mismatched_prior(self):
        bad=copy.deepcopy(self.joint);bad['cases'][0]['pair_translation_gap_m']=999.0
        with self.assertRaises(a.EvidenceDenied): a.evaluate(self.tri,bad)
