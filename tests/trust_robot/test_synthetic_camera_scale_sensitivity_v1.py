import unittest
from unittest.mock import patch
from trust_robot import analytic_separated_modalities as sep
from trust_robot.clean_backbone import PoseSE3
from trust_robot import synthetic_camera_scale_sensitivity_v1 as a

class A47PrivateCameraScaleTests(unittest.TestCase):
    def test_01_frozen_matrix(self):
        self.assertEqual(len(a.CASES),10)
        self.assertEqual(a.MULTIPLIERS,(0.5,1.0,2.0))

    def test_02_guard_closed(self):
        a.guard('ANALYTIC_FIXTURE')

    def test_03_guard_refuses_physical_before_solver(self):
        for origin in ('NOVA_LIVE','NOVA_RECORDED','M2DGR',None,{},2):
            with self.subTest(origin=origin),patch.object(sep,'estimate_separated',side_effect=AssertionError('SOLVER_CALLED')):
                with self.assertRaises(a.SensitivityBoundary):
                    a.run_case('clean',1.0,True,origin)

    def test_04_unknown_condition(self):
        with self.assertRaises(a.SensitivityBoundary):a.run_case('real',1.0)

    def test_05_invalid_camera_switch(self):
        for x in (0,1,'yes',None):
            with self.subTest(x=x),self.assertRaises(a.SensitivityBoundary):a.run_case('clean',1.0,x)

    def test_06_invalid_multiplier(self):
        for x in (True,1,0,0.0,0.9,3.0,None,'1.0',float('nan')):
            with self.subTest(x=x),self.assertRaises(a.SensitivityBoundary):a.run_case('clean',x)

    def test_07_canonical_deterministic(self):
        self.assertEqual(a.canonical({'a':1,'b':2}),a.canonical({'b':2,'a':1}))

    def test_08_camera_residual_inverse_scale(self):
        from trust_robot.analytic_inertial_15d import initial_state
        x=initial_state();y=x.copy();y[0]+=0.015
        b=sep.camera_residual(x,y,PoseSE3.identity())[0]
        with patch.object(sep,'CAMERA_POSITION_SCALE_M',0.015):
            doubled=sep.camera_residual(x,y,PoseSE3.identity())[0]
        self.assertAlmostEqual(doubled,2*b)
        self.assertAlmostEqual(sep.CAMERA_POSITION_SCALE_M,0.03)

    def test_09_camera_on_clean_accounting(self):
        row=a.run_case('clean',1.0,True)
        self.assertEqual((row['camera_factor_count'],row['lidar_factor_count']),(2,7))
        self.assertEqual(row['missing_lidar_shadow_windows'],[])
        self.assertEqual(row['physical_sensor_health_classification'],'ABSTAIN')

    def test_10_camera_on_dropout_accounting(self):
        row=a.run_case('lidar_dropout',1.0,True)
        self.assertEqual((row['camera_factor_count'],row['lidar_factor_count']),(2,3))
        self.assertEqual(row['missing_lidar_shadow_windows'],[2,3])

    def test_11_camera_disabled_control(self):
        row=a.run_case('clean',2.0,False)
        self.assertEqual((row['camera_factor_count'],row['lidar_factor_count']),(0,7))

    def test_12_scale_restored_after_success(self):
        before=(sep.CAMERA_POSITION_SCALE_M,sep.CAMERA_ROTATION_SCALE_RAD)
        a.run_case('clean',0.5,True)
        self.assertEqual(before,(sep.CAMERA_POSITION_SCALE_M,sep.CAMERA_ROTATION_SCALE_RAD))

    def test_13_scale_restored_after_exception(self):
        before=(sep.CAMERA_POSITION_SCALE_M,sep.CAMERA_ROTATION_SCALE_RAD)
        with patch.object(sep,'estimate_separated',side_effect=RuntimeError('INJECTED')):
            with self.assertRaisesRegex(RuntimeError,'INJECTED'):
                a.run_case('clean',0.5,True)
        self.assertEqual(before,(sep.CAMERA_POSITION_SCALE_M,sep.CAMERA_ROTATION_SCALE_RAD))

    def test_14_no_operational_selection(self):
        row=a.run_case('lidar_dropout',2.0,True)
        self.assertFalse(row['factor_scale_execution_authorized'])
        self.assertFalse(row['numerical_scale_tuning_is_health_inference'])
        self.assertEqual(row['real_factor_admission'],'DENIED')
