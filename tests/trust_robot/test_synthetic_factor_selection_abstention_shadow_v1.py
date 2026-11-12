import copy
import hashlib
import unittest
from unittest.mock import patch
from trust_robot import synthetic_factor_selection_abstention_shadow_v1 as s

class ShadowOnlyTests(unittest.TestCase):
    def fixture(self):
        rows=[];sensitivity=[]
        for condition in s.CONDITIONS:
            for enabled,scales in ((True,s.SCALES),(False,(1.0,2.0))):
                for mul in scales:
                    ownership=s.factor_ownership(s.mask_for(condition))
                    pos=[0.005*mul if enabled else 0.001, 0.0, 0.0]
                    rows.append({
                        'condition':condition,'seed':13,'camera_enabled':enabled,
                        'hypothetical_camera_residual_scale_multiplier':mul,
                        'numerical_camera_residual_scales_m_rad':[0.03*mul,0.04*mul],
                        'estimated_trajectory_sha256':hashlib.sha256(
                            (condition+str(enabled)).encode()).hexdigest(),
                        'final_synthetic_position_m':pos,
                        'camera_factor_count':2 if enabled else 0,
                        'lidar_factor_count':ownership['lidar_factor_count'],
                        'missing_lidar_shadow_windows':ownership['known_endpoint_shadow_holds'],
                        'numerical_solver_accepted_windows':4,
                        'numerical_scale_tuning_is_health_inference':False,
                        'factor_scale_execution_authorized':False,
                        'physical_factor_scale_calibrated':False,
                        'physical_sensor_health_classification':'ABSTAIN',
                        'physical_responsible_modality':'UNRESOLVED',
                        'real_factor_admission':'DENIED','robot_actuation':'DENIED',
                    })
            for mul in s.SCALES:
                sensitivity.append({
                    'condition':condition,'multiplier':mul,
                    'synthetic_final_position_gap_to_one_x_m':round(abs(0.005*mul-0.005),12),
                    'trajectory_quality_or_health_inferred':False,
                })
        return {'schema':s.PRIOR_SCHEMA,'case_count':10,'cases':rows,
                'numerical_scale_sensitivity':sensitivity,
                'camera_disabled_controls_invariant':True,
                'uncertainty_decision':'ABSTAIN_UNCALIBRATED_REAL_HEALTH',
                'operational_factor_selection_executed':False,
                'operational_factor_weighting_executed':False,
                'physical_calibration_established':False,
                'real_factor_admission':'DENIED','robot_actuation':'DENIED'}

    def test_frozen_gates_closed(self):
        s.guard()

    def test_unknown_origin_rejected_before_model(self):
        report=self.fixture()
        for val in ('NOVA_LIVE','NOVA_RECORDED','M2DGR','',None,0,{}):
            with self.subTest(origin=val), patch(
                'trust_robot.factor_ownership_availability_bridge_v1.model',
                side_effect=AssertionError('MODEL_CALLED')):
                with self.assertRaises(s.ShadowBoundary):s.evaluate(report,val)

    def test_frozen_mask_topology_clean(self):
        x=s.factor_ownership(s.mask_for('clean'))
        self.assertEqual(x['lidar_factor_count'],7)
        self.assertEqual(x['known_endpoint_shadow_holds'],[])
        self.assertEqual(len(x['lidar_edge_keys_absent_due_to_known_scan_mask']),0)

    def test_middle_scan_dropout(self):
        x=s.factor_ownership(s.mask_for('lidar_dropout'))
        self.assertEqual(x['lidar_factor_count'],3)
        self.assertEqual(x['known_endpoint_shadow_holds'],[2,3])
        self.assertEqual(len(x['lidar_edge_keys_absent_due_to_known_scan_mask']),4)

    def test_all_missing_scan_mask(self):
        x=s.factor_ownership([False]*9)
        self.assertEqual(x['lidar_factor_count'],0)
        self.assertEqual(x['known_endpoint_shadow_holds'],[1,2,3,4])

    def test_invalid_mask_rejected(self):
        for mask in ([],[True]*8,[True]*8+[1],None):
            with self.subTest(mask=mask),self.assertRaises(ValueError):s.factor_ownership(mask)

    def test_all_32_masks_unique(self):
        self.assertEqual(len(s.all_32_masks()),32)

    def test_example_report_passes(self):
        r=s.evaluate(self.fixture())
        self.assertEqual(r['case_count'],10)
        self.assertEqual(r['real_health_inference'],'ABSTAIN')
        self.assertFalse(r['operational_factor_selection_executed'])

    def test_repeat_determinism(self):
        r=self.fixture()
        self.assertEqual(s.canonical(s.execute(r)),s.canonical(s.execute(r)))

    def test_duplicate_case_rejected(self):
        r=self.fixture();r['cases'][1]=copy.deepcopy(r['cases'][0])
        with self.assertRaises(s.ShadowBoundary):s.evaluate(r)

    def test_fabricated_health_rejected(self):
        r=self.fixture();r['cases'][0]['physical_sensor_health_classification']='HEALTHY'
        with self.assertRaises(s.ShadowBoundary):s.evaluate(r)

    def test_calibrated_scale_claim_rejected(self):
        r=self.fixture();r['cases'][0]['physical_factor_scale_calibrated']=True
        with self.assertRaises(s.ShadowBoundary):s.evaluate(r)

    def test_weight_execution_rejected(self):
        r=self.fixture();r['operational_factor_weighting_executed']=True
        with self.assertRaises(s.ShadowBoundary):s.evaluate(r)

    def test_missing_hold_is_not_health_label(self):
        r=s.evaluate(self.fixture())
        row=next(x for x in r['cases'] if x['condition']=='lidar_dropout')
        self.assertEqual(row['known_scan_availability_factor_ownership']['known_endpoint_shadow_holds'],[2,3])
        self.assertEqual(row['real_sensor_health'],'ABSTAIN_UNCALIBRATED')

    def test_camera_disabled_invariance_enforced(self):
        r=self.fixture();off=[x for x in r['cases'] if not x['camera_enabled']]
        off[0]['estimated_trajectory_sha256']='a'*64
        with self.assertRaises(s.ShadowBoundary):s.evaluate(r)

    def test_scale_contrast_consistency_enforced(self):
        r=self.fixture();r['numerical_scale_sensitivity'][0]['synthetic_final_position_gap_to_one_x_m']=0.1
        with self.assertRaises(s.ShadowBoundary):s.evaluate(r)

    def test_wrong_schema_rejected(self):
        r=self.fixture();r['schema']='REAL'
        with self.assertRaises(s.ShadowBoundary):s.evaluate(r)

    def test_case_count_rejected(self):
        r=self.fixture();r['cases']=r['cases'][:-1]
        with self.assertRaises(s.ShadowBoundary):s.evaluate(r)

    def test_digest_canonical_sort(self):
        self.assertEqual(s.canonical({'b':2,'a':1}),s.canonical({'a':1,'b':2}))
