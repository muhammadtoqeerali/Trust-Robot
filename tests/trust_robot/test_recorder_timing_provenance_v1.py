"""Synthetic recorder-time diagnostics only: no physical timing claims."""
import copy
import unittest
from trust_robot.physical_ros_bag_envelope_v1 import EnvelopeValidationError
from trust_robot.m2dgr_prospective_evidence_packet_v1 import build_packet
from trust_robot.recorder_timing_provenance_v1 import (
    summarize_recorder_intervals, event_time_acquisition_contract,
    estimate_hardware_clock_offset, associate_physical_exposures,
)


def row(stream, seq, stamp):
    return {
        'stream': stream, 'sequence': seq, 'recorder_stamp_ns': stamp,
        'serialized_bytes': 128, 'source_kind': 'PHYSICAL_UNQUALIFIED',
        'header_stamp_ns': None, 'frame_id': None,
    }


def fixture():
    return [row('imu', 0, 100), row('lidar', 0, 100),
            row('imu', 1, 200), row('lidar', 1, 250),
            row('imu', 2, 200+100)]


class RecorderTimingTests(unittest.TestCase):
    def test_01_basic_stats(self):
        r = summarize_recorder_intervals(fixture())
        self.assertEqual(r['total_messages'], 5)
        self.assertEqual(r['by_stream']['imu']['interval_count'], 2)
        self.assertEqual(r['by_stream']['imu']['recorder_delta_p95_nearest_rank_ns'], 100)
    def test_02_ties_counted(self):
        self.assertEqual(summarize_recorder_intervals(fixture())['global_consecutive_equal_recorder_stamps'], 1)
    def test_03_nonphysical_semantics(self):
        r = summarize_recorder_intervals(fixture())
        self.assertFalse(r['cross_sensor_sync_qualified'])
        self.assertFalse(r['physical_sample_periods_qualified'])
        self.assertFalse(r['header_stamps_extracted'])
    def test_04_deterministic(self):
        self.assertEqual(summarize_recorder_intervals(fixture()),
                         summarize_recorder_intervals(copy.deepcopy(fixture())))
    def test_05_unordered_rejected(self):
        x = fixture(); x[3]['recorder_stamp_ns'] = 50
        with self.assertRaises(EnvelopeValidationError): summarize_recorder_intervals(x)
    def test_06_bad_header_rejected(self):
        x = fixture(); x[0]['header_stamp_ns'] = 100
        with self.assertRaises(EnvelopeValidationError): summarize_recorder_intervals(x)
    def test_07_bad_frame_rejected(self):
        x = fixture(); x[0]['frame_id'] = 'bmi088_frame'
        with self.assertRaises(EnvelopeValidationError): summarize_recorder_intervals(x)
    def test_08_source_mutation_rejected(self):
        x = fixture(); x[0]['source_kind'] = 'PHYSICAL_QUALIFIED'
        with self.assertRaises(EnvelopeValidationError): summarize_recorder_intervals(x)
    def test_09_sequence_gap_rejected(self):
        x = fixture(); x[2]['sequence'] = 9
        with self.assertRaises(EnvelopeValidationError): summarize_recorder_intervals(x)
    def test_10_empty_rejected(self):
        with self.assertRaises(EnvelopeValidationError): summarize_recorder_intervals([])
    def test_11_exact_event_requests(self):
        r = event_time_acquisition_contract(build_packet())
        self.assertEqual(r['request_ids'], ['B04', 'B05', 'B06', 'C01', 'C02'])
        self.assertEqual(r['qualified_receipt_count'], 0)
    def test_12_all_event_values_unfilled(self):
        r = event_time_acquisition_contract(build_packet())
        self.assertTrue(all(x['measured_offset_ns'] is None
                            and x['uncertainty_bound_ns'] is None
                            for x in r['requests']))
    def test_13_reject_fabricated_A23(self):
        p = build_packet(); p['requests'][0]['qualifying_receipt_received'] = True
        with self.assertRaises(Exception): event_time_acquisition_contract(p)
    def test_14_denied_clock_fit(self):
        with self.assertRaises(EnvelopeValidationError): estimate_hardware_clock_offset(fixture())
    def test_15_denied_exposure_association(self):
        with self.assertRaises(EnvelopeValidationError): associate_physical_exposures(fixture())
    def test_16_empty_single_stream_stats(self):
        r = summarize_recorder_intervals([row('imu', 0, 100)])
        self.assertEqual(r['by_stream']['imu']['interval_count'], 0)
        self.assertIsNone(r['by_stream']['lidar']['recorder_span_ns'])
    def test_17_duplicate_stream_recorder_stamp(self):
        r = summarize_recorder_intervals([row('imu', 0, 100), row('imu', 1, 100)])
        self.assertEqual(r['by_stream']['imu']['same_stream_equal_recorder_stamp_count'], 1)
    def test_18_no_factor_permission(self):
        r = summarize_recorder_intervals(fixture())
        self.assertEqual(r['real_factor_count'], 0)
        self.assertEqual(r['m2dgr_gates'], '11_CLOSED')
