"""A40-3 manufactured-fixture observability negative controls; no real inputs."""
from __future__ import annotations
import copy
import json
import unittest

from trust_robot.synthetic_observability_falsification_v1 import (
    CASES, EXCLUDED_NOT_REPRESENTABLE, _aggregate_characterization,
    _canonical, paired_fixture, run_falsification,
)
from trust_robot import synthetic_diagnostic_stress_v1 as stress


class ObservabilityFalsificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = run_falsification()
        cls.rows = {x['case_id']: x for x in cls.out['rows']}

    def test_01_cardinality_and_unique_cases(self):
        self.assertEqual(len(CASES), 19)
        self.assertEqual(len(self.rows), 19)
        self.assertEqual(self.out['case_count'], 19)

    def test_02_expected_visibility_distribution(self):
        self.assertEqual(self.out['visibility_counts'], {
            'DETAIL_ONLY_CHANGE': 6, 'NO_DIAGNOSTIC_CHANGE': 8,
            'PUBLIC_SUMMARY_CHANGE': 5})

    def test_03_every_case_matches_frozen_expected(self):
        for case_id, _, _, expect in CASES:
            with self.subTest(case_id=case_id):
                self.assertEqual(self.rows[case_id]['visibility'], expect)

    def test_04_public_change_needs_detail_change(self):
        for row in self.rows.values():
            with self.subTest(case_id=row['case_id']):
                if row['changed_public_fields']:
                    self.assertTrue(row['changed_detail_fields'])

    def test_05_no_diagnostic_change_invariance(self):
        for name in ('both_header_common_shift', 'both_recorder_common_shift',
                     'camera_zero_location_swap', 'imu_sign_inversion',
                     'imu_axis_permutation', 'imu_sample_reverse',
                     'lidar_slot_redistribution', 'lidar_message_reverse'):
            with self.subTest(name=name):
                r = self.rows[name]
                self.assertEqual(r['visibility'], 'NO_DIAGNOSTIC_CHANGE')
                self.assertEqual(r['changed_detail_fields'], [])
                self.assertEqual(r['changed_public_fields'], [])

    def test_06_camera_ordinal_swap_detail_only(self):
        r = self.rows['camera_ordinal_swap']
        self.assertEqual(r['visibility'], 'DETAIL_ONLY_CHANGE')
        self.assertTrue(any(x.startswith('left.header_intervals_ms') for x in r['changed_detail_fields']))

    def test_07_recorder_jitter_detail_only(self):
        self.assertEqual(self.rows['camera_recorder_small_jitter']['visibility'], 'DETAIL_ONLY_CHANGE')
        self.assertFalse(self.rows['camera_recorder_small_jitter']['changed_public_fields'])

    def test_08_recorder_offset_not_physical_clock(self):
        self.assertEqual(self.rows['right_recorder_small_offset']['visibility'], 'DETAIL_ONLY_CHANGE')
        self.assertEqual(self.out['physical_clock_sync'], 'NOT_QUALIFIED')

    def test_09_imu_bias_visible_only_in_detail(self):
        r = self.rows['imu_bias']
        self.assertEqual(r['visibility'], 'DETAIL_ONLY_CHANGE')
        self.assertTrue(any(k.startswith('imu.acceleration_norm_m_s2') for k in r['changed_detail_fields']))

    def test_10_imu_noise_visible_only_in_detail(self):
        r = self.rows['imu_noise']
        self.assertEqual(r['visibility'], 'DETAIL_ONLY_CHANGE')
        self.assertTrue(any(k.startswith('imu.angular_speed_norm_rad_s') for k in r['changed_detail_fields']))

    def test_11_lidar_layout_hidden_in_public_summary(self):
        r = self.rows['lidar_field_layout_change']
        self.assertEqual(r['visibility'], 'DETAIL_ONLY_CHANGE')
        self.assertEqual(r['changed_public_fields'], [])

    def test_12_lidar_slot_delta_visible(self):
        r = self.rows['lidar_slots_removed']
        self.assertIn('lidar_reported_point_slots', r['changed_public_fields'])

    def test_13_camera_zero_flag_visible(self):
        r = self.rows['camera_zero_flags_added']
        self.assertIn('camera.left_zero_payload_count', r['changed_public_fields'])

    def test_14_camera_header_overlap_not_sync(self):
        r = self.rows['right_header_offset']
        self.assertIn('camera.numeric_equal_header_count', r['changed_public_fields'])
        self.assertEqual(self.out['physical_clock_sync'], 'NOT_QUALIFIED')

    def test_15_camera_message_removal_not_dropped_frame_proof(self):
        r = self.rows['right_message_removed']
        self.assertIn('camera.right_count', r['changed_public_fields'])
        self.assertEqual(self.out['source_role'], 'MANUFACTURED_FIXTURES_ONLY_NO_REAL_SENSOR_OR_DATASET')

    def test_16_delivery_burst_still_diagnostic_only(self):
        self.assertEqual(self.rows['right_delivery_burst']['visibility'], 'PUBLIC_SUMMARY_CHANGE')
        self.assertEqual(self.out['real_factors'], 'DENIED')

    def test_17_distinct_control_treatment_and_no_mutation(self):
        baseline = stress.manufactured_baseline()
        baseline_bytes = _canonical(baseline)
        for case_id, *_ in CASES:
            ctrl, treatment = paired_fixture(case_id)
            self.assertNotEqual(ctrl, treatment)
            _aggregate_characterization(ctrl)
            _aggregate_characterization(treatment)
        self.assertEqual(_canonical(baseline), baseline_bytes)

    def test_18_unknown_synthetic_case_rejected(self):
        with self.assertRaises(ValueError):
            paired_fixture('request_motor_stop')

    def test_19_byte_exact_repeatability(self):
        self.assertEqual(_canonical(run_falsification()), _canonical(run_falsification()))

    def test_20_aggregate_export_no_input_traces(self):
        exported = json.dumps(self.out, sort_keys=True, allow_nan=False)
        for forbidden in ('header_ns', 'recorder_ns', 'accel_xyz', 'gyro_xyz',
                          'point_step_bytes', 'raw_payload', 'image_data'):
            self.assertNotIn(forbidden, exported)

    def test_21_unmodelled_signals_explicitly_excluded(self):
        self.assertEqual(len(EXCLUDED_NOT_REPRESENTABLE), 5)
        self.assertIn('camera_pixel_blur', self.out['excluded_unrepresented_not_simulated'])
        self.assertIn('lidar_return_geometry', self.out['excluded_unrepresented_not_simulated'])

    def test_22_causal_attack_inference_denied(self):
        self.assertEqual(self.out['attack_attribution'], 'DENIED')
        self.assertEqual(self.out['physical_health_labels_accepted'], 0)

    def test_23_physical_and_dataset_gates_frozen(self):
        self.assertEqual(self.out['train_validation_confirmation_datasets'], 'NOT_ACCESSED')
        self.assertEqual(self.out['robot_control'], 'DENIED')
        self.assertEqual(self.out['trained_health_model'], 'NOT_QUALIFIED')

    def test_24_modalities_and_count_partition(self):
        per = self.out['visibility_by_modality']
        self.assertEqual(set(per), {'camera', 'imu', 'lidar'})
        self.assertEqual(sum(sum(v.values()) for v in per.values()), 19)


if __name__ == '__main__':
    unittest.main()
