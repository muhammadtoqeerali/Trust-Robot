"""Transcription checks for R134-A48 publisher calibration comparison.

The user-supplied A48 values are not an independently
attested experiment log. No calibration coefficients are stored.
"""
import hashlib
import json
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REPORT = ROOT / (
    'experiments/'
    'trust_robot_r134_a48_source_consistency_v1/'
    'aggregate_v1.json'
)

MODULE = ROOT / (
    'src/trust_robot/camera_imu_shadow_rotation_v1.py'
)

PREV = ROOT / (
    'experiments/'
    'trust_robot_r134_a44_real_shadow_checkpoint_v1/'
    'aggregate_report_v1.json'
)

MODULE_SHA = (
    '048abce9b63a13176dab1ccb36208195c40baa'
    'ee4ba61f91eb793bccd9a04462'
)

PREV_SHA = (
    'cf612c945a3890e2f8313a7c22a001e0ff71'
    'c50f406dd6c146a2e2f27fdfadc6'
)

class SourceConsistencyTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(REPORT.read_text())

    def test_checkpoint_identity(self):
        self.assertEqual(
            self.data['schema'],
            'TRUST_ROBOT_R134_A48_PUBLISHER_CALIBRATION_CONSISTENCY_V1'
        )
        self.assertEqual(
            self.data['evidence_role'],
            'PUBLISHER_DERIVED_CALIBRATION_SOURCE_CONSISTENCY'
        )

    def test_publisher_source_pins(self):
        s = self.data['source']

        self.assertEqual(
            s['repository'],
            'Hilti-Research/phasma_description'
        )
        self.assertEqual(
            s['commit'],
            '79002026e9b229cf9b4e95a403eaec4f00acfd79'
        )
        self.assertEqual(
            s['calibration_git_blob'],
            '669905cffd11b51fda31ec529f777d5eb0b2663a'
        )
        self.assertEqual(
            s['phasma_xacro_git_blob'],
            '694316c6aaf858584991c459d749133c0bde5489'
        )
        self.assertEqual(
            s['camera_zero_identity'],
            'FRONT_RIGHT_CAMERA'
        )
        self.assertEqual(
            s['calibration_parent'],
            'ALPHASENSE_IMU'
        )
        self.assertIs(
            s['source_log_cryptographically_attested'],
            False
        )

    def test_transcribed_geometric_comparison(self):
        c = self.data['comparison']

        expected = {
            'inverse_rotation_difference_deg':0.00000171,
            'inverse_translation_difference_mm_displayed':0.0,
            'direct_rotation_difference_deg':120.95316063,
            'direct_translation_difference_mm':109.241498
        }

        for key,value in expected.items():
            self.assertIn(key,c)
            self.assertTrue(
                math.isfinite(c[key])
            )
            self.assertAlmostEqual(
                c[key],value,delta=1e-10
            )

        self.assertLess(
            c['inverse_rotation_difference_deg'],
            c['direct_rotation_difference_deg']
        )
        self.assertLess(
            c['inverse_translation_difference_mm_displayed'],
            c['direct_translation_difference_mm']
        )
        self.assertIs(
            c['inverse_rotation_closer'],True
        )
        self.assertIs(
            c['inverse_translation_closer'],True
        )
        self.assertIs(
            c['publisher_to_local_numerical_consistency_supported'],
            True
        )

    def test_unverified_authorities_remain_closed(self):
        b = self.data['boundaries']
        c = self.data['comparison']

        self.assertEqual(
            b['m2dgr_scientific_gates_closed'],11
        )
        self.assertIs(
            b['shared_calibration_origin_possible'],True
        )

        for key in (
            'official_archive_byte_identity_established',
            'independent_physical_measurement',
            'bag_camera_frame_alias_certified',
            'bag_imu_frame_alias_certified',
            'capture_clock_certified',
            'independent_ground_truth_accessed',
            'metric_pose_accuracy_established',
            'real_estimator_factor_authorized',
            'health_label_authorized',
            'm2dgr_confirmation_test_accessed'
        ):
            self.assertIs(b[key],False)

        self.assertIs(c['calibration_fitted'],False)
        self.assertIs(
            c['acceptance_threshold_selected'],False
        )

    def test_previous_published_evidence_unchanged(self):
        self.assertEqual(
            hashlib.sha256(MODULE.read_bytes()).hexdigest(),
            MODULE_SHA
        )
        self.assertEqual(
            hashlib.sha256(PREV.read_bytes()).hexdigest(),
            PREV_SHA
        )

if __name__ == '__main__':
    unittest.main(verbosity=2)
