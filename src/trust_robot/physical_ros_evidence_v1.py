"""Offline integrity and diagnostic review of Nova Carter ROS metadata.

Never qualifies hardware timing, ground truth, calibration, or real factors.
No ROS dependency, network access, or dataset access.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path, PurePosixPath

STREAMS = ('imu', 'left', 'right', 'left_info', 'right_info', 'lidar')
CORRELATION_FIELDS = ('phc_val', 'phc2_val', 'sys_val', 'tsc_val', 'phc_latency')


class EvidenceValidationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise EvidenceValidationError(message)


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def valid_digest(value):
    return isinstance(value, str) and len(value) == 64 and all(
        ch in '0123456789abcdef' for ch in value
    )


def read_json(path, limit=8_000_000):
    require(path.is_file() and not path.is_symlink(), 'Missing or linked evidence file')
    require(path.stat().st_size <= limit, 'Evidence JSON exceeds size limit')
    return json.loads(path.read_text(encoding='utf-8'))


def review_evidence(root, metadata_sha256, manifest_sha256):
    """Checks copy integrity and internal consistency; never attests sensor truth."""
    root = Path(root)
    require(root.is_dir() and not root.is_symlink(), 'Invalid evidence directory')
    require(valid_digest(metadata_sha256) and valid_digest(manifest_sha256),
            'Invalid expected digest')
    manifest_path = root / 'TRANSFER_MANIFEST.json'
    metadata_path = root / 'metadata.json'
    require(manifest_path.is_file() and not manifest_path.is_symlink(),
            'Missing manifest')
    require(metadata_path.is_file() and not metadata_path.is_symlink(),
            'Missing metadata')
    require(sha256(manifest_path) == manifest_sha256, 'Manifest digest mismatch')
    require(sha256(metadata_path) == metadata_sha256, 'Metadata digest mismatch')
    manifest = read_json(manifest_path, 2_000_000)
    metadata = read_json(metadata_path)
    require(isinstance(manifest, dict) and isinstance(metadata, dict),
            'Invalid JSON root')
    require(manifest.get('phase') == 'R135-A25F-1R', 'Wrong manifest phase')
    require(manifest.get('source_phase') == 'R135-A25E-3', 'Wrong source phase')
    require(metadata.get('phase') == 'R135-A25E-3', 'Wrong measurement phase')
    require(manifest.get('original_metadata_sha256') == metadata_sha256,
            'Manifest does not bind original metadata')
    require(manifest.get('real_factor_admission') == 'DENIED',
            'Real-factor denial missing')
    require(manifest.get('m2dgr_gates') == '11_CLOSED', 'Admission gates changed')
    require(manifest.get('raw_images_saved') is False and
            manifest.get('raw_pointclouds_saved') is False,
            'Unexpected raw recording declaration')
    require('no real factors admitted' in metadata.get('qualification', '').lower(),
            'Unqualified metadata language')
    require('11 m2dgr gates closed' in metadata.get('qualification', '').lower(),
            'Qualification boundary missing')

    expected = manifest.get('verified_files')
    require(isinstance(expected, dict) and len(expected) >= 3,
            'Invalid file inventory')
    require({'metadata.json', 'launch.log', 'three_sensors.launch.py'} <= set(expected),
            'Required source artifacts missing')
    actual = {}
    for path in root.rglob('*'):
        require(not path.is_symlink(), 'Symlink in evidence tree')
        require(path.is_dir() or path.is_file(), 'Unsupported evidence file type')
        if path.is_file():
            name = path.relative_to(root).as_posix()
            if name != 'TRANSFER_MANIFEST.json':
                actual[name] = path
    require(set(expected) == set(actual), 'File inventory differs from manifest')
    total = 0
    for name, item in expected.items():
        relative = PurePosixPath(name)
        require(not relative.is_absolute() and name == relative.as_posix() and
                all(p not in ('', '.', '..') for p in relative.parts) and
                '\\' not in name, 'Invalid inventory path')
        require(isinstance(item, dict), 'Invalid inventory record')
        path = actual[name]
        size = path.stat().st_size
        total += size
        require(total <= 250 * 1024 * 1024, 'Evidence copy too large')
        require(size == item.get('bytes') and sha256(path) == item.get('sha256'),
                'Copied file integrity failure: ' + name)
    require(sha256(root / 'launch.log') == manifest.get('original_launch_log_sha256'),
            'Original launch log mismatch')
    require(sha256(root / 'three_sensors.launch.py') ==
            metadata.get('launch_file_sha256'), 'Original launch source mismatch')

    shutdown = metadata.get('shutdown', {})
    require(isinstance(shutdown, dict) and
            shutdown.get('launch_group_gone') is True and
            shutdown.get('ros_graph_clear') is True and
            shutdown.get('remaining_driver_processes') == [],
            'Captured shutdown report indicates incomplete cleanup')
    require(len(metadata.get('correlation_node_names', [])) == 1,
            'Expected exactly one timestamp node')
    samples, summaries = metadata.get('samples'), metadata.get('summaries')
    require(isinstance(samples, dict) and isinstance(summaries, dict) and
            set(samples) == set(STREAMS) | {'correlation'} and
            set(summaries) == set(samples), 'Unexpected evidence stream schema')

    report = {}
    for stream in STREAMS:
        rows = samples[stream]
        info = summaries[stream]
        require(isinstance(rows, list) and 1 <= len(rows) <= 2200 and
                isinstance(info, dict) and info.get('count') == len(rows) and
                info.get('recorded') == len(rows), 'Stream count mismatch: ' + stream)
        require(all(isinstance(row, list) and len(row) == 3 and
                    all(type(x) is int and x > 0 for x in row) for row in rows),
                'Bad timestamp record: ' + stream)
        header = [row[0] for row in rows]
        arrival = [row[1] for row in rows]
        require(all(b > a for a, b in zip(header, header[1:])) and
                all(b > a for a, b in zip(arrival, arrival[1:])),
                'Nonmonotonic header/arrival: ' + stream)
        require(info.get('header_nonincreasing') == 0 and
                info.get('first_header_ns') == header[0] and
                info.get('last_header_ns') == header[-1],
                'Header summary mismatch: ' + stream)
        gaps = [(b - a) / 1_000_000 for a, b in zip(header, header[1:])]
        median = round(statistics.median(gaps), 5) if gaps else None
        require(info.get('header_p50_ms') == median,
                'Median summary mismatch: ' + stream)
        report[stream] = {'count': len(rows), 'median_header_interval_ms': median,
                          'maximum_header_gap_ms': round(max(gaps), 5) if gaps else None}

    corr = samples['correlation']
    require(isinstance(corr, list) and 1 <= len(corr) <= 30 and
            summaries['correlation'].get('count') == len(corr),
            'Correlation count mismatch')
    for row in corr:
        require(isinstance(row, dict) and type(row.get('arrival_monotonic_ns')) is int
                and row['arrival_monotonic_ns'] > 0 and
                isinstance(row.get('fields'), dict), 'Malformed correlation record')
        for field in CORRELATION_FIELDS:
            value = row['fields'].get(field)
            require(isinstance(value, str) and value.isascii() and
                    value.isdecimal(), 'Malformed correlation field: ' + field)

    left = {row[0] for row in samples['left']}
    right = {row[0] for row in samples['right']}
    pairs = len(left & right)
    require(metadata.get('image_exact_header_pairs') == pairs and
            metadata.get('image_distinct_left_stamps') == len(left) and
            metadata.get('image_distinct_right_stamps') == len(right),
            'Stereo timestamp accounting mismatch')
    require(len(left) == len(samples['left']) and len(right) == len(samples['right']),
            'Duplicate image timestamps')

    return {
        'status': 'INTEGRITY_AND_INTERNAL_CONSISTENCY_ONLY',
        'source_phase': 'R135-A25E-3',
        'metadata_sha256': metadata_sha256,
        'manifest_sha256': manifest_sha256,
        'verified_file_count': len(actual),
        'verified_source_bytes': total,
        'streams': report,
        'correlation_message_count': len(corr),
        'exact_stereo_timestamp_pairs': pairs,
        'real_factor_admission': 'DENIED',
        'm2dgr_gates': '11_CLOSED',
        'physical_clock_accuracy': 'UNVERIFIED',
        'sensor_calibration_validity': 'UNVERIFIED',
        'ground_truth_validity': 'UNVERIFIED',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir', required=True)
    parser.add_argument('--metadata-sha256', required=True)
    parser.add_argument('--manifest-sha256', required=True)
    args = parser.parse_args()
    print(json.dumps(review_evidence(args.evidence_dir, args.metadata_sha256,
                                     args.manifest_sha256), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
