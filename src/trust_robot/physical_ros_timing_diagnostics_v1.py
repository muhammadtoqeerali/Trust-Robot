"""R135-A26: offline descriptive diagnostics of already integrity-reviewed ROS metadata.

No clock calibration, sensor sync, factor admission, robot I/O, or dataset access.
All numbers are descriptions of recorded fields, not physical timing accuracy.
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from trust_robot.physical_ros_evidence_v1 import (
    STREAMS, EvidenceValidationError, read_json, require, review_evidence,
)

SCHEMA = "TRUST_ROBOT_R135_A26_OFFLINE_TIMING_DIAGNOSTICS_V1"
CLOCK_FIELDS = ("phc_val", "phc2_val", "sys_val", "tsc_val")


def _median(values, digits=5):
    return round(statistics.median(values), digits) if values else None


def _intervals(values):
    return [b - a for a, b in zip(values, values[1:])]


def stream_diagnostics(rows):
    """Describe ordered capture rows: [header_ns, monotonic_arrival_ns, wall_arrival_ns]."""
    require(isinstance(rows, list) and len(rows) >= 2, 'Insufficient stream samples')
    require(all(isinstance(r, list) and len(r) == 3 and
                all(type(x) is int and x > 0 for x in r) for r in rows),
            'Malformed stream sample')
    headers, monotonic, wall = [[r[i] for r in rows] for i in range(3)]
    hdiff = _intervals(headers)
    mdiff = _intervals(monotonic)
    require(all(x > 0 for x in hdiff) and all(x > 0 for x in mdiff),
            'Nonincreasing header or monotonic arrival')
    header_ms = [x / 1e6 for x in hdiff]
    arrival_ms = [x / 1e6 for x in mdiff]
    med = statistics.median(header_ms)
    return {
        'message_count': len(rows),
        'header_span_s': round((headers[-1] - headers[0]) / 1e9, 5),
        'arrival_span_s': round((monotonic[-1] - monotonic[0]) / 1e9, 5),
        'header_interval_median_ms': _median(header_ms),
        'arrival_interval_median_ms': _median(arrival_ms),
        'maximum_header_gap_ms': round(max(header_ms), 5),
        'header_gap_over_1_5x_median_count': sum(v > 1.5 * med for v in header_ms),
        'header_span_derived_hz': round((len(rows)-1) * 1e9 / (headers[-1]-headers[0]), 5),
        'wall_arrival_minus_header_median_ms': _median(
            [(w-h)/1e6 for h,w in zip(headers,wall)]),
        'arrival_minus_header_is_physical_latency': False,
    }


def stereo_diagnostics(left, right):
    """Compare recorded numeric ROS headers; NOT physical exposure synchronization."""
    def maps(rows):
        require(isinstance(rows, list) and all(isinstance(r,list) and len(r)==3 and
                all(type(x) is int for x in r) for r in rows), 'Malformed image rows')
        result = {r[0]: r[1] for r in rows}
        require(len(result) == len(rows), 'Duplicate image header')
        return result
    lm, rm = maps(left), maps(right)
    common = set(lm) & set(rm)
    gaps = [abs(lm[h]-rm[h])/1e6 for h in common]
    return {
        'left_image_count': len(left), 'right_image_count': len(right),
        'exact_shared_header_count': len(common),
        'unmatched_left_header_count': len(set(lm)-set(rm)),
        'unmatched_right_header_count': len(set(rm)-set(lm)),
        'matched_callback_arrival_abs_gap_median_ms': _median(gaps),
        'matched_callback_arrival_abs_gap_max_ms': round(max(gaps),5) if gaps else None,
        'matched_headers_prove_stereo_hardware_sync': False,
        'callback_arrival_gap_proves_exposure_offset': False,
    }


def correlation_diagnostics(rows):
    """Clock-field integer differences in UNVERIFIED raw units only."""
    require(isinstance(rows,list) and len(rows) >= 1, 'No correlation records')
    cols = {key: [] for key in CLOCK_FIELDS + ('phc_latency',)}
    arrivals = []
    for row in rows:
        require(isinstance(row,dict) and
                type(row.get('arrival_monotonic_ns')) is int, 'Bad correlation row')
        arrivals.append(row['arrival_monotonic_ns'])
        raw = row.get('fields')
        require(isinstance(raw,dict), 'Bad clock fields')
        for key in cols:
            value = raw.get(key)
            require(isinstance(value,str) and value.isascii() and value.isdecimal(),
                    'Unparseable clock field: ' + key)
            cols[key].append(int(value))
    require(all(x > 0 for x in arrivals), 'Bad correlation arrival')
    return {
        'message_count': len(rows),
        'clock_fields_strictly_increasing': {
            k: all(b>a for a,b in zip(cols[k],cols[k][1:])) for k in CLOCK_FIELDS
        },
        'sys_minus_phc2_median_raw_integer_units': _median([
            a-b for a,b in zip(cols['sys_val'],cols['phc2_val'])]),
        'phc2_minus_phc_median_raw_integer_units': _median([
            a-b for a,b in zip(cols['phc2_val'],cols['phc_val'])]),
        'phc_latency_median_raw_integer_units': _median(cols['phc_latency']),
        'clock_field_units_verified': False,
        'clock_accuracy_verified': False,
        'cross_sensor_time_sync_verified': False,
    }


def build_diagnostics(evidence_dir, metadata_sha256, manifest_sha256):
    """Require A25 integrity check first; never upgrade its admission decision."""
    root = Path(evidence_dir)
    verified = review_evidence(root, metadata_sha256, manifest_sha256)
    metadata = read_json(root / 'metadata.json')
    rows = metadata['samples']
    streams = {name: stream_diagnostics(rows[name]) for name in STREAMS}
    for name, item in streams.items():
        require(item['message_count'] == verified['streams'][name]['count'],
                'Mismatch against validated source: ' + name)
    stereo = stereo_diagnostics(rows['left'], rows['right'])
    corr = correlation_diagnostics(rows['correlation'])
    require(stereo['exact_shared_header_count'] == verified['exact_stereo_timestamp_pairs'],
            'Changed stereo header accounting')
    require(corr['message_count'] == verified['correlation_message_count'],
            'Changed correlation record count')
    return {
        'schema': SCHEMA,
        'status': 'UNQUALIFIED_OFFLINE_DIAGNOSTICS_ONLY',
        'source_phase': 'R135-A25E-3',
        'source_metadata_sha256': metadata_sha256,
        'source_transfer_manifest_sha256': manifest_sha256,
        'source_integrity_check': 'PASS',
        'streams': streams,
        'stereo': stereo,
        'correlation': corr,
        'calibration': {
            'calibration_document_hash_is_physical_calibration_proof': False,
            'camera_intrinsics_physically_validated': False,
            'camera_imu_extrinsics_physically_validated': False,
            'camera_lidar_extrinsics_physically_validated': False,
            'lidar_point_timestamp_semantics_verified': False,
        },
        'independent_reference_present': False,
        'full_raw_image_or_pointcloud_recording_present': False,
        'physical_clock_accuracy': 'UNVERIFIED',
        'sensor_calibration_validity': 'UNVERIFIED',
        'ground_truth_validity': 'UNVERIFIED',
        'real_factor_admission': 'DENIED',
        'm2dgr_gates': '11_CLOSED',
        'a23_independent_evidence_requests_qualified': 0,
        'scientific_boundary': 'DESCRIPTIVE_METADATA_ONLY',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir', required=True)
    parser.add_argument('--metadata-sha256', required=True)
    parser.add_argument('--manifest-sha256', required=True)
    args = parser.parse_args()
    print(json.dumps(build_diagnostics(args.evidence_dir,
                                       args.metadata_sha256,
                                       args.manifest_sha256),
                     indent=2, sort_keys=True, allow_nan=False))


if __name__ == '__main__':
    main()
