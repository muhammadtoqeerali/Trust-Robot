"""A27-7 synthetic SE(3) checks; never a physical frame qualification."""
import copy
import math
import unittest

from trust_robot.nominal_frame_graph_v1 import FrameGraphError, relative_transform
from trust_robot.nominal_frame_consistency_v1 import (
    audit_nominal_consistency, check_nominal_claim, qualify_physical_extrinsic,
)


def toy():
    return {
        'links': ['root', 'imu_nominal', 'lidar_nominal'],
        'joints': [
            {'name': 'j1', 'type': 'fixed', 'parent': 'root',
             'child': 'imu_nominal', 'xyz': [1, 2, 3], 'rpy': [0, 0, math.pi/2]},
            {'name': 'j2', 'type': 'fixed', 'parent': 'imu_nominal',
             'child': 'lidar_nominal', 'xyz': [0, 1, 0], 'rpy': [0.1, 0.2, 0.3]},
        ],
    }


def claim():
    return {
        'source_frame': 'lidar_nominal', 'target_frame': 'root',
        'T_target_source': relative_transform(toy(), 'lidar_nominal', 'root'),
        'scope': 'NOMINAL_URDF_ONLY',
    }


class GeometryConsistencyTests(unittest.TestCase):
    def test_01_internal_consistency(self):
        r = audit_nominal_consistency(toy(), ['imu_nominal', 'lidar_nominal'])
        self.assertEqual(r['pair_checks'], 9)
        self.assertEqual(r['composition_checks'], 27)
        self.assertLess(r['max_composition_error'], 1e-9)
    def test_02_deterministic_digest(self):
        a = audit_nominal_consistency(toy(), ['lidar_nominal', 'imu_nominal'])
        b = audit_nominal_consistency(copy.deepcopy(toy()), ['imu_nominal', 'lidar_nominal'])
        self.assertEqual(a, b)
    def test_03_valid_nominal_claim(self):
        self.assertFalse(check_nominal_claim(toy(), claim())['physically_qualified'])
    def test_04_reverse_direction_rejected(self):
        c = claim()
        c['T_target_source'] = relative_transform(toy(), 'root', 'lidar_nominal')
        with self.assertRaises(FrameGraphError): check_nominal_claim(toy(), c)
    def test_05_translated_claim_rejected(self):
        c = claim(); c['T_target_source'][0][3] += 0.5
        with self.assertRaises(FrameGraphError): check_nominal_claim(toy(), c)
    def test_06_reflection_rejected(self):
        c = claim(); c['T_target_source'][0][0] *= -1
        with self.assertRaises(FrameGraphError): check_nominal_claim(toy(), c)
    def test_07_fake_physical_claim_rejected(self):
        c = claim(); c['scope'] = 'PHYSICAL_VERIFIED'
        with self.assertRaises(FrameGraphError): check_nominal_claim(toy(), c)
    def test_08_bmi088_alias_rejected(self):
        c = claim(); c['source_frame'] = 'bmi088_frame'
        with self.assertRaises(FrameGraphError): check_nominal_claim(toy(), c)
    def test_09_claim_extra_field_rejected(self):
        c = claim(); c['physical_accuracy'] = 0.001
        with self.assertRaises(FrameGraphError): check_nominal_claim(toy(), c)
    def test_10_nonfinite_matrix_rejected(self):
        c = claim(); c['T_target_source'][0][3] = float('nan')
        with self.assertRaises(FrameGraphError): check_nominal_claim(toy(), c)
    def test_11_boolean_matrix_rejected(self):
        c = claim(); c['T_target_source'][0][3] = True
        with self.assertRaises(FrameGraphError): check_nominal_claim(toy(), c)
    def test_12_corrupted_homogeneous_row(self):
        c = claim(); c['T_target_source'][3][0] = 1.0
        with self.assertRaises(FrameGraphError): check_nominal_claim(toy(), c)
    def test_13_dynamic_joint_refused(self):
        x = toy(); x['joints'][0]['type'] = 'revolute'
        with self.assertRaises(FrameGraphError): audit_nominal_consistency(x, ['imu_nominal', 'lidar_nominal'])
    def test_14_duplicate_selection_refused(self):
        with self.assertRaises(FrameGraphError): audit_nominal_consistency(toy(), ['imu_nominal', 'imu_nominal'])
    def test_15_factor_denied(self):
        with self.assertRaises(FrameGraphError): qualify_physical_extrinsic(toy())
    def test_16_scientific_denials(self):
        r = audit_nominal_consistency(toy(), ['imu_nominal', 'lidar_nominal'])
        self.assertIsNone(r['bmi088_frame_transform'])
        self.assertEqual(r['m2dgr_gates'], '11_CLOSED')
