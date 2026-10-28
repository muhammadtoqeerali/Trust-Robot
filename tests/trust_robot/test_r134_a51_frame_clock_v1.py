"""R134-A51 aggregate metadata transcription tests.

These tests do not independently repeat UNIVER's
bag inspection or authenticate its terminal output.
"""
import hashlib
import json
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REPORT = ROOT / (
    'experiments/'
    'trust_robot_r134_a51_frame_clock_v1/'
    'aggregate_v1.json'
)

PINS = {
    'src/trust_robot/camera_imu_shadow_rotation_v1.py':
        '048abce9b63a13176dab1ccb36208195c40baaee4ba61f91eb793bccd9a04462',
    'experiments/trust_robot_r134_a44_real_shadow_checkpoint_v1/aggregate_report_v1.json':
        'cf612c945a3890e2f8313a7c22a001e0ff71c50f406dd6c146a2e2f27fdfadc6',
    'experiments/trust_robot_r134_a48_source_consistency_v1/aggregate_v1.json':
        '7e15631cc25f0171270264fd11b0f27ff8ea58f71110607ae6d08f4622a36bd4'
}

class FrameClockAuditTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(REPORT.read_text())

    def test_schema_and_evidence_role(self):
        d=self.data
        self.assertEqual(
            d['schema'],
            'TRUST_ROBOT_R134_A51_FRAME_CLOCK_AUDIT_V1'
        )
        self.assertEqual(
            d['evidence_role'],
            'UNTRUSTED_RECORDED_METADATA_AND_DOCUMENTARY_CONTEXT'
        )
        self.assertIs(
            d['recording']['source_log_cryptographically_attested'],
            False
        )

    def test_frame_counts_and_absent_ros_support(self):
        f=self.data['frames']
        self.assertEqual(f['camera_headers_inspected'],76)
        self.assertEqual(f['imu_headers_inspected'],11003)
        self.assertEqual(f['camera_header_mismatch_count'],0)
        self.assertEqual(f['imu_frame_mismatch_count'],0)
        self.assertEqual(f['imu_header_nonmonotonic_count'],0)
        self.assertEqual(f['tf_topic_count'],0)
        self.assertEqual(f['cam0_camera_info_connections'],0)
        self.assertEqual(
            f['camera_header_frame_id'],
            'cam0_sensor_frame'
        )
        self.assertEqual(
            f['imu_header_frame_id'],
            'imu_sensor_frame'
        )
        self.assertIs(
            f['publisher_to_recorded_ros_alias_certified'],
            False
        )

    def test_record_and_header_delay_descriptive_only(self):
        t=self.data['timestamps']
        self.assertEqual(len(t['groups']),4)
        self.assertEqual(
            [g['count'] for g in t['groups']],
            [64,12,128,45]
        )
        for group in t['groups']:
            for key in ('min_ms','median_ms','max_ms'):
                self.assertEqual(group[key],0.0)

        self.assertEqual(
            t['record_minus_header_print_precision_decimal_places'],
            4
        )
        self.assertIs(
            t['integer_nanosecond_equality_independently_audited'],
            False
        )
        self.assertIs(
            t['bag_record_timestamp_independent_capture_clock_reference'],
            False
        )

    def test_measured_intervals_and_declared_shift(self):
        t=self.data['timestamps']
        self.assertAlmostEqual(
            t['kalibr_declared_shift_ms'],1.90712
        )

        cam=t['camera_first_64_intervals_ms']
        imu=t['imu_first_128_intervals_ms']

        self.assertAlmostEqual(cam['min'],24.9972)
        self.assertAlmostEqual(cam['median'],24.9973)
        self.assertAlmostEqual(cam['max'],24.99946)

        self.assertAlmostEqual(imu['min'],2.4835)
        self.assertAlmostEqual(imu['median'],2.505)
        self.assertAlmostEqual(imu['max'],2.5251)

        for values in (cam,imu):
            self.assertTrue(all(
                math.isfinite(values[k]) and values[k]>0
                for k in ('min','median','max')
            ))
            self.assertLessEqual(
                values['min'],values['median']
            )
            self.assertLessEqual(
                values['median'],values['max']
            )

    def test_manufacturer_documentation_not_bag_proof(self):
        m=self.data['manufacturer_context']

        self.assertEqual(
            m['pinned_revision'],
            '6280dd64b7271b8a26a21c1703f38086d636a2b2'
        )
        self.assertEqual(
            m['time_synchronization_git_blob'],
            'b6115e8a4c8cd6ac567d5fd53c0ab20c3e082f2f'
        )
        self.assertEqual(
            m['sensor_settings_git_blob'],
            'd048ee893aa3a90dcdf852d0413594632477dc9a'
        )
        self.assertEqual(
            m['documented_time_modes'],
            ['RAW_DEVICE','TRANSLATED_HOST','PTP_SYNCHRONIZED']
        )

        for key in (
            'recording_specific_mode_verified',
            'recording_specific_driver_configuration_available',
            'manual_version_matches_recording_proven'
        ):
            self.assertIs(m[key],False)

        self.assertIs(
            self.data['timestamps']['clock_mode_identified'],
            False
        )
        self.assertIs(
            self.data['timestamps']['ptp_lock_certified'],
            False
        )

    def test_scientific_authority_closed(self):
        b=self.data['scientific_boundaries']
        self.assertEqual(
            b['m2dgr_scientific_gates_closed'],11
        )

        for key in (
            'physical_frame_alias_certified',
            'physical_clock_certified',
            'independent_calibration_measurement',
            'ground_truth_accessed',
            'pose_or_covariance_generated',
            'real_factor_authorized',
            'health_labels_authorized',
            'm2dgr_confirmation_test_accessed'
        ):
            self.assertIs(b[key],False)

    def test_previously_published_files_unchanged(self):
        for name,expected in PINS.items():
            actual=hashlib.sha256(
                (ROOT/name).read_bytes()
            ).hexdigest()
            self.assertEqual(actual,expected)

if __name__=='__main__':
    unittest.main(verbosity=2)
