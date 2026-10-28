"""Consistency checks for transcribed R134-A44 aggregate evidence.

Checks data integrity and descriptive arithmetic only.
Does not independently reproduce the UNIVER experiment.
"""
import hashlib
import json
import math
import statistics
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REPORT = ROOT / (
    'experiments/'
    'trust_robot_r134_a44_real_shadow_checkpoint_v1/'
    'aggregate_report_v1.json'
)

MODULE = ROOT / (
    'src/trust_robot/'
    'camera_imu_shadow_rotation_v1.py'
)

PIN = (
    '048abce9b63a13176dab1ccb36208195c40baa'
    'ee4ba61f91eb793bccd9a04462'
)

EXPECTED_FRAMES = (
    (660,661), (660,663),
    (680,681), (680,683),
    (1060,1061), (1060,1063),
    (1080,1081), (1080,1083)
)

class R134A44CheckpointTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(REPORT.read_text())
        cls.rows = cls.report['rows']

    def test_published_source_identity(self):
        self.assertEqual(
            hashlib.sha256(MODULE.read_bytes()).hexdigest(),
            PIN
        )
        self.assertEqual(
            self.report['source']['published_kernel_sha256'],
            PIN
        )

    def test_provenance_and_scope(self):
        d = self.report
        self.assertEqual(
            d['schema'],
            'TRUST_ROBOT_R134_A44_REAL_SHADOW_AGGREGATE_V1'
        )
        self.assertEqual(
            d['evidence_role'],
            'UNTRUSTED_DESCRIPTIVE_REPLAY'
        )
        self.assertEqual(d['camera_images_decoded'],12)
        self.assertEqual(d['imu_messages_decoded'],11003)
        self.assertEqual(len(self.rows),8)
        self.assertEqual(
            [tuple(r['frames']) for r in self.rows],
            list(EXPECTED_FRAMES)
        )

        for row in self.rows:
            self.assertTrue(5 <= row['rays'] <= 96)
            self.assertIn(row['steps'],(11,31))
            for key in (
                'zero','header_negative','header_positive',
                'kalibr_negative','kalibr_positive'
            ):
                self.assertTrue(
                    math.isfinite(row[key]) and row[key] >= 0
                )

    def test_aggregates_match_console(self):
        expected = {
            'zero':0.49050,
            'header_negative':0.20914,
            'header_positive':0.93475,
            'kalibr_negative':0.21244,
            'kalibr_positive':0.93195
        }
        for key,target in expected.items():
            actual = statistics.median(
                row[key] for row in self.rows
            )
            self.assertAlmostEqual(
                actual,target,delta=0.000011
            )

    def test_active_vs_stationary(self):
        for key in ('header_negative','kalibr_negative'):
            self.assertTrue(all(
                r[key] < r['zero']
                for r in self.rows[:4]
            ))
            self.assertTrue(all(
                r[key] > r['zero']
                for r in self.rows[4:]
            ))
        self.assertEqual(
            sum(r['zero'] == 0 for r in self.rows),4
        )

    def test_scientific_authority_closed(self):
        b = self.report['scientific_boundaries']
        self.assertEqual(
            b['m2dgr_scientific_gates_closed'],11
        )
        self.assertTrue(
            b['same_recording_and_windows_as_r134_a33']
        )
        self.assertFalse(
            b['independent_confirmation']
        )
        for key in (
            'real_factor_admission',
            'health_label_authority',
            'metric_pose_accuracy_claim',
            'camera_imu_frame_identity_verified',
            'm2dgr_confirmation_test_accessed'
        ):
            self.assertIs(b[key],False)

        self.assertFalse(
            self.report['source'][
                'source_log_cryptographically_attested'
            ]
        )
        self.assertFalse(
            self.report['source'][
                'physical_calibration_verified'
            ]
        )

if __name__ == '__main__':
    unittest.main(verbosity=2)
