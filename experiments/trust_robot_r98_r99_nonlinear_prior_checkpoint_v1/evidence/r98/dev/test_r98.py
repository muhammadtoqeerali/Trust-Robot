import dataclasses
import inspect
import unittest

import numpy as np

import r98_nonlinear_audit as m

from trust_robot.analytic_inertial_15d import make_fixture
from trust_robot.analytic_preintegrated_fusion import make_factors
from trust_robot.analytic_three_modality_bridge import (
    manufactured_camera_packets,
)
from trust_robot.multimodal_factor_interface import (
    SyntheticPoseFactor,
)
from s6_joint_fusion import (
    JointFactor,assemble_joint,
    estimate_joint,
)

class R98Tests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.report=m.execute()

    def packets(self):
        fixture,truth=make_fixture('clean')
        _,lidar,_=make_factors(fixture)
        camera=manufactured_camera_packets(
            truth,seed=13
        )
        return lidar,camera

    def test_schema(self):
        self.assertEqual(
            self.report['schema'],m.SCHEMA
        )

    def test_status(self):
        self.assertEqual(
            self.report['status'],
            'PASS_SYNTHETIC_SOFTWARE_ONLY'
        )

    def test_three_nonlinear_cases(self):
        self.assertEqual(
            self.report['nonlinear_solver_cases'],3
        )

    def test_twelve_windows(self):
        self.assertEqual(
            self.report['nonlinear_windows_audited'],12
        )

    def test_nine_eliminations(self):
        self.assertEqual(
            self.report[
                'schur_marginalizations_reported'
            ],9
        )

    def test_clean_same_edge(self):
        a=self.report['cases']['clean_joint']
        self.assertEqual(
            a['same_edge_camera_lidar'],2
        )

    def test_camera_dropout_ablation(self):
        a=self.report['cases']['clean_camera_off']
        self.assertEqual(a['camera_factors'],0)

    def test_lidar_dropout_effect(self):
        a=self.report['cases']
        self.assertLess(
            a['lidar_dropout_joint']['lidar_factors'],
            a['clean_joint']['lidar_factors']
        )

    def test_no_duplicate_ownership(self):
        for case in self.report['cases'].values():
            self.assertEqual(
                case['distinct_measurement_ids'],
                case['consumed_factors']
                +case['remaining_factors']
            )

    def test_local_schur_information(self):
        a=self.report['local_nonlinear_schur_audit']
        self.assertLess(
            a['information_relative_error'],1e-6
        )

    def test_local_schur_gradient(self):
        a=self.report['local_nonlinear_schur_audit']
        self.assertLess(
            a['gradient_relative_error'],1e-6
        )

    def test_relative_quadratic_energy(self):
        a=self.report['local_nonlinear_schur_audit']
        self.assertLess(
            a['reduced_energy_difference_abs_error'],
            1e-5
        )

    def test_original_truth_excluded_from_solver_api(self):
        args=list(
            inspect.signature(
                estimate_joint
            ).parameters
        )
        self.assertEqual(
            args,['fixture','camera_packets']
        )

    def test_recorded_origin_rejected(self):
        _,camera=self.packets()

        with self.assertRaises(ValueError):
            dataclasses.replace(
                camera[0],origin='M2DGR'
            )

    def test_wrong_source_rejected(self):
        _,camera=self.packets()

        with self.assertRaises(ValueError):
            dataclasses.replace(
                camera[0],
                source_id='/camera/color/image_raw'
            )

    def test_duplicate_camera_denied(self):
        lidar,camera=self.packets()

        with self.assertRaises(ValueError):
            assemble_joint(
                lidar,(camera[0],camera[0])
            )

    def test_singular_covariance_denied(self):
        _,camera=self.packets()

        with self.assertRaises(ValueError):
            JointFactor(
                camera[0],np.zeros((6,6))
            )

    def test_untrusted_factor_type_denied(self):
        from s6_joint_fusion import validate_factors

        with self.assertRaises(ValueError):
            validate_factors(
                ({'source':'M2DGR'},)
            )

    def test_invalid_condition_denied(self):
        with self.assertRaises(m.R98Error):
            m.run_case('room_02')

    def test_invalid_seed_denied(self):
        with self.assertRaises(m.R98Error):
            m.run_case('clean',seed=-1)

    def test_no_health_or_groundtruth_scoring(self):
        self.assertFalse(
            self.report['health_training_authorized']
        )
        self.assertFalse(
            self.report['independent_ground_truth_scoring']
        )
        self.assertFalse(
            self.report['ate_rpe_authorized']
        )

    def test_r95_not_misrepresented_as_integrated(self):
        self.assertFalse(
            self.report[
                'r95_gaussian_prior_merged_into_s6'
            ]
        )

if __name__=='__main__':
    unittest.main(verbosity=2)
