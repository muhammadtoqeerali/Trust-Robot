"""No real evidence, ROS, robot, or dataset I/O: synthetic A26 diagnostics tests."""
import unittest
from unittest.mock import patch

from trust_robot.physical_ros_timing_diagnostics_v1 import (
    SCHEMA, stream_diagnostics, stereo_diagnostics, correlation_diagnostics,
    build_diagnostics, EvidenceValidationError,
)


def rows(headers, arrivals=None):
    if arrivals is None:
        arrivals = [x+1_000_000 for x in headers]
    return [[h,a,h+5_000_000] for h,a in zip(headers,arrivals)]


def corr():
    return [{'arrival_monotonic_ns': 100,
             'fields': {'phc_val':'1000','phc2_val':'1010','sys_val':'1008',
                        'tsc_val':'8000','phc_latency':'25'}},
            {'arrival_monotonic_ns': 200,
             'fields': {'phc_val':'2000','phc2_val':'2010','sys_val':'2011',
                        'tsc_val':'9000','phc_latency':'30'}}]


class OfflineTimingDiagnosticTests(unittest.TestCase):
    def test_01_header_and_arrival_descriptions_distinct(self):
        r = rows([1_000_000_000,1_010_000_000,1_040_000_000],
                 [2_000_000_000,2_012_000_000,2_027_000_000])
        result = stream_diagnostics(r)
        self.assertEqual(result['message_count'],3)
        self.assertEqual(result['header_interval_median_ms'],20.0)
        self.assertEqual(result['arrival_interval_median_ms'],13.5)
        self.assertEqual(result['maximum_header_gap_ms'],30.0)
        self.assertFalse(result['arrival_minus_header_is_physical_latency'])

    def test_02_single_large_gap_reported_without_fault_label(self):
        r = rows([1_000_000_000,1_010_000_000,1_020_000_000,1_060_000_000])
        result = stream_diagnostics(r)
        self.assertEqual(result['header_gap_over_1_5x_median_count'],1)
        self.assertEqual(result['maximum_header_gap_ms'],40.0)

    def test_03_rejects_nonmonotonic_header(self):
        with self.assertRaises(EvidenceValidationError):
            stream_diagnostics(rows([100,100]))

    def test_04_rejects_nonmonotonic_arrival(self):
        with self.assertRaises(EvidenceValidationError):
            stream_diagnostics(rows([100,200], [1000,999]))

    def test_05_rejects_invalid_record(self):
        with self.assertRaises(EvidenceValidationError):
            stream_diagnostics([[1,2,3],[4,'5',6]])

    def test_06_stereo_exact_pairs_but_no_hardware_sync_claim(self):
        left = rows([100,200,300], [1000,2000,3000])
        right = rows([100,300,400], [1900,3500,4000])
        result = stereo_diagnostics(left,right)
        self.assertEqual(result['exact_shared_header_count'],2)
        self.assertEqual(result['unmatched_left_header_count'],1)
        self.assertEqual(result['unmatched_right_header_count'],1)
        self.assertFalse(result['matched_headers_prove_stereo_hardware_sync'])
        self.assertFalse(result['callback_arrival_gap_proves_exposure_offset'])

    def test_07_rejects_duplicate_stereo_header(self):
        with self.assertRaises(EvidenceValidationError):
            stereo_diagnostics(rows([100,100]),rows([100,200]))

    def test_08_correlated_raw_numbers_not_clock_accuracy(self):
        result = correlation_diagnostics(corr())
        self.assertEqual(result['message_count'],2)
        self.assertEqual(result['sys_minus_phc2_median_raw_integer_units'],-0.5)
        self.assertFalse(result['clock_field_units_verified'])
        self.assertFalse(result['clock_accuracy_verified'])
        self.assertFalse(result['cross_sensor_time_sync_verified'])

    def test_09_rejects_non_numeric_clock_field(self):
        samples = corr()
        samples[0]['fields']['phc_val'] = 'not-a-number'
        with self.assertRaises(EvidenceValidationError):
            correlation_diagnostics(samples)

    def test_10_empty_correlation_rejected(self):
        with self.assertRaises(EvidenceValidationError):
            correlation_diagnostics([])

    def test_11_integration_calls_existing_integrity_gate(self):
        with patch('trust_robot.physical_ros_timing_diagnostics_v1.review_evidence',
                   side_effect=EvidenceValidationError('bad digest')):
            with self.assertRaises(EvidenceValidationError):
                build_diagnostics('/some/private/path', 'x'*64, 'y'*64)

    def test_12_schema_is_descriptive_not_qualification(self):
        self.assertEqual(SCHEMA, 'TRUST_ROBOT_R135_A26_OFFLINE_TIMING_DIAGNOSTICS_V1')


if __name__ == '__main__':
    unittest.main()
