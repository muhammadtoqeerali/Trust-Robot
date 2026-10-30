"""R135-A30-3: descriptive recorder-timestamp diagnostics and event requests.

Inter-arrival differences represent ROS bag recorder metadata, never
independently verified sensor event intervals, exposure timing, or clock
alignment. Physical time-offset fitting and factor construction are denied.
"""
from __future__ import annotations

from trust_robot.physical_ros_bag_envelope_v1 import (
    TOPICS, EnvelopeValidationError, review_envelopes,
)
from trust_robot.m2dgr_prospective_evidence_packet_v1 import validate_packet
from trust_robot.independent_acquisition_plan_v1 import build_work_orders

SCHEMA = 'TRUST_ROBOT_R135_A30_3_RECORDER_TIME_PROVENANCE_V1'
EVENT_REQUEST_IDS = ('B04', 'B05', 'B06', 'C01', 'C02')


def require(ok, message):
    if not ok:
        raise EnvelopeValidationError(message)


def _nearest_rank(values, numerator, denominator):
    require(len(values) > 0, 'No recorder interval samples')
    sorted_values = sorted(values)
    index = (numerator*len(sorted_values) + denominator - 1)//denominator - 1
    return sorted_values[index]


def summarize_recorder_intervals(rows):
    review_envelopes(rows)
    streams = {stream: [] for stream, _ in TOPICS.values()}
    last_stamp = {}
    gaps = {name: [] for name in streams}
    equal_global = 0
    previous = None
    for row in rows:
        stamp = row['recorder_stamp_ns']
        stream = row['stream']
        if previous is not None and stamp == previous:
            equal_global += 1
        previous = stamp
        if stream in last_stamp:
            gaps[stream].append(stamp-last_stamp[stream])
        last_stamp[stream] = stamp
        streams[stream].append(stamp)
    by_stream = {}
    for name in sorted(streams):
        stamps = streams[name]
        deltas = gaps[name]
        by_stream[name] = {
            'message_count': len(stamps),
            'interval_count': len(deltas),
            'recorder_span_ns': stamps[-1]-stamps[0] if stamps else None,
            'recorder_delta_min_ns': min(deltas) if deltas else None,
            'recorder_delta_p50_nearest_rank_ns': (
                _nearest_rank(deltas, 50, 100) if deltas else None),
            'recorder_delta_p95_nearest_rank_ns': (
                _nearest_rank(deltas, 95, 100) if deltas else None),
            'recorder_delta_max_ns': max(deltas) if deltas else None,
            'same_stream_equal_recorder_stamp_count': sum(d == 0 for d in deltas),
        }
    return {
        'schema': SCHEMA,
        'status': 'DESCRIPTIVE_ROSBAG_RECORDER_INTERVALS_ONLY',
        'total_messages': len(rows),
        'global_consecutive_equal_recorder_stamps': equal_global,
        'by_stream': by_stream,
        'timestamp_basis': 'SQLITE_ROSBAG_RECORDER_NS_NOT_SENSOR_EVENT_TIME',
        'no_physical_clock_map_computed': True,
        'header_stamps_extracted': False,
        'frame_ids_extracted': False,
        'physical_sample_periods_qualified': False,
        'cross_sensor_sync_qualified': False,
        'estimator_invoked': False,
        'real_factor_count': 0,
        'real_factor_admission': 'DENIED',
        'm2dgr_gates': '11_CLOSED',
    }


def event_time_acquisition_contract(packet):
    """Five exact A23 timing/reference requests; no filled physical values."""
    validate_packet(packet)
    planned = build_work_orders(packet)
    index = {item['request_id']: item for item in planned['work_orders']}
    require(all(ident in index for ident in EVENT_REQUEST_IDS),
            'Missing frozen independent timing request')
    orders = []
    for ident in EVENT_REQUEST_IDS:
        item = index[ident]
        require(item['received_receipt'] is None
                and item['measurement_value'] is None
                and item['uncertainty_value'] is None
                and item['scientific_gate_opened'] is False,
                'Unexpected evidence qualification')
        orders.append({
            'request_id': ident,
            'physical_fact_required': item['physical_fact_required'],
            'proposed_acquisition_method': item['proposed_acquisition_method'],
            'expected_independent_artifact': item['expected_independent_artifact'],
            'physical_event_name': None,
            'clock_domain_name': None,
            'measured_offset_ns': None,
            'uncertainty_bound_ns': None,
            'independently_accepted': False,
        })
    return {
        'schema': SCHEMA,
        'status': 'INDEPENDENT_EVENT_TIME_REQUESTS_ONLY',
        'request_ids': list(EVENT_REQUEST_IDS),
        'requests': orders,
        'qualified_receipt_count': 0,
        'time_offset_selected': False,
        'synchronization_tolerance_selected': False,
        'physical_clock_accuracy': 'UNVERIFIED',
        'real_factor_admission': 'DENIED',
        'm2dgr_gates': '11_CLOSED',
    }


def estimate_hardware_clock_offset(*args, **kwargs):
    raise EnvelopeValidationError('Recorder timestamps cannot qualify hardware clock offsets')


def associate_physical_exposures(*args, **kwargs):
    raise EnvelopeValidationError('Physical exposure/firing event relationships are unverified')
