"""Eight distributed adjacent LiDAR-pair diagnostics. No real factor admission."""

import hashlib
import json
import pathlib
import struct
import sys

import numpy as np
import r18_decode as reader
import r27_lidar_motion as prior

COUNT = 8
TOPIC = '/velodyne_points'


def need(ok, reason):
    if not ok:
        raise ValueError('R29_DENIED:' + reason)


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def read(path):
    return json.loads(pathlib.Path(path).read_text())


def schedule(bag, info):
    connections = {
        c['id']: c for c in info['connections']
    }

    ids = [
        c['id'] for c in info['connections']
        if c['topic'] == TOPIC
        and c['message_type'] == 'sensor_msgs/PointCloud2'
    ]

    need(
        len(ids) == 1
        and info['connection_count'] == 15
        and info['chunk_count'] == 5182,
        'INDEX_IDENTITY'
    )

    lidar = ids[0]
    eligible = []

    with pathlib.Path(bag).open('rb') as f:
        need(
            reader.read_exact(f, 13) == b'#ROSBAG V2.0\n',
            'BAG_MAGIC'
        )

        header, _ = reader.file_record(f, 8192)
        need(header.get(b'op') == b'\x03', 'BAG_HEADER')

        index_pos = struct.unpack(
            '<Q', header[b'index_pos']
        )[0]

        need(
            index_pos == info['index_position'],
            'INDEX_OFFSET'
        )

        f.seek(index_pos)

        for _ in range(info['connection_count']):
            connection_header, _ = reader.file_record(f)
            need(
                connection_header.get(b'op') == b'\x07',
                'INDEX_CONNECTION_OP'
            )

        for _ in range(info['chunk_count']):
            h, data = reader.file_record(f)

            need(
                h.get(b'op') == b'\x06',
                'CHUNK_INFO_OP'
            )

            offset = struct.unpack(
                '<Q', h[b'chunk_pos']
            )[0]

            n = reader.u32(h[b'count'])

            need(
                len(data) == 8 * n,
                'CHUNK_INFO_COUNTS'
            )

            counts = {}

            for i in range(n):
                cid, cnt = struct.unpack_from(
                    '<II', data, 8 * i
                )

                need(
                    cid in connections
                    and cid not in counts
                    and cnt > 0,
                    'CHUNK_CONNECTION_LEDGER'
                )

                counts[cid] = cnt

            if lidar in counts:
                need(
                    counts[lidar] == 1,
                    'MULTIPLE_LIDAR_MESSAGES_IN_CHUNK'
                )
                eligible.append((offset, counts))

    need(
        len(eligible) == 752
        and len({x[0] for x in eligible}) == 752,
        'LIDAR_CHUNK_COUNT'
    )

    indices = [
        (i * (len(eligible) - 2)) // (COUNT - 1)
        for i in range(COUNT)
    ]

    need(
        len(set(indices)) == COUNT,
        'DUPLICATE_ANCHORS'
    )

    pairs = [
        (eligible[i], eligible[i + 1])
        for i in indices
    ]

    need(
        len({
            off
            for pair in pairs
            for off, _ in pair
        }) == 2 * COUNT,
        'OVERLAPPING_PAIR_CHUNKS'
    )

    return pairs, connections, lidar


def fetch(bag, selected, connections, lidar):
    outputs = {}

    with pathlib.Path(bag).open('rb') as f:
        for off, expected_counts in selected:
            need(off not in outputs, 'REUSED_OFFSET')

            raw, compression = reader.chunk_data(f, off)
            observed = {}
            found = []

            for cid, record_time, blob in reader.messages(
                raw, connections
            ):
                observed[cid] = observed.get(cid, 0) + 1

                if cid != lidar:
                    continue

                body = bytes(blob)

                xyz, meta = prior.pointcloud(
                    body, reader
                )

                selected_xyz, idx = prior.select_points(
                    xyz
                )

                found.append((
                    selected_xyz,
                    {
                        'chunk_offset': off,
                        'connection_id': cid,
                        'bag_record_time_ns': record_time,
                        'serialized_message_sha256': sha(body),
                        'serialized_message_bytes': len(body),
                        'header_stamp_ns': meta['header_stamp_ns'],
                        'frame_id': meta['frame_id'],
                        'sequence': meta['sequence'],
                        'point_count_total': meta['points'],
                        'point_payload_sha256': meta['point_payload_sha256'],
                        'selected_indices_sha256': sha(
                            idx.astype('<i8').tobytes()
                        ),
                        'selected_xyz_float64_le_sha256': sha(
                            selected_xyz.astype('<f8').tobytes()
                        ),
                    }
                ))

            need(
                observed == expected_counts
                and len(found) == 1,
                'INDEX_VS_MESSAGE_COUNT'
            )

            outputs[off] = found[0]

    return outputs


def safety(d):
    need(
        d['schema'] ==
        'TRUST_ROBOT_R29_TRAIN_LIDAR_ADJACENT_PAIR_DIAGNOSTICS_V1'
        and d['trajectory_id'] == 'room_02'
        and d['split'] == 'train'
        and d['pair_count'] == COUNT,
        'SCOPE'
    )

    need(
        d['per_scan_selected_points'] == 512
        and d['fixed_registration_iterations'] == 10
        and d['sampling_rule'] ==
        'eight_evenly_spaced_index_anchors_each_with_next_lidar_scan',
        'PLAN'
    )

    need(
        len(d['pairs']) == COUNT
        and len({
            s['chunk_offset']
            for p in d['pairs']
            for s in p['scans']
        }) == 16,
        'UNIQUE_SOURCES'
    )

    for key in (
        'physical_capture_time_verified',
        'cross_modal_alignment_performed',
        'full_extrinsics_verified',
        'independent_ground_truth_scored',
        'health_model_training_authorized',
        'real_sensor_factor_execution_authorized',
        'm2dgr_scoring_authorized',
        'pose_accuracy_established',
        'statistical_stability_established',
        'raw_recording_modified',
        'github_modified',
    ):
        need(
            d.get(key) is False,
            'UNAUTHORIZED:' + key
        )

    for key in (
        'real_pose_factors_generated',
        'health_labels_generated',
        'new_sensor_acquisitions',
    ):
        need(
            type(d.get(key)) is int and d[key] == 0,
            'NONZERO:' + key
        )

    for p in d['pairs']:
        need(
            p['registration']['candidate_registered_as_factor']
            is False
            and p['registration']['independent_pose_accuracy_claimed']
            is False
            and p['scans'][1]['header_stamp_ns'] >
            p['scans'][0]['header_stamp_ns'],
            'PER_PAIR_GATES'
        )


def run(repo, bag, archive, r27_path, r28_path, output):
    r17p = archive / 'r17/r17_recorded_index.json'
    r18p = archive / 'r18/r18_bounded_recorded_samples.json'

    r17, r18, r27, r28 = map(
        read, (r17p, r18p, r27_path, r28_path)
    )

    need(
        r17['trajectory_id'] ==
        r18['trajectory_id'] ==
        r27['trajectory_id'] ==
        r28['trajectory_id'] == 'room_02',
        'TRAIN_IDS'
    )

    need(
        r17['file_sha256'] ==
        r18['recording_sha256'] ==
        r27['bag_sha256'] ==
        r28['authenticated_bag_sha256'],
        'BAG_CHAIN'
    )

    need(
        r28['candidate_factors_admitted'] == 0
        and r28['relative_pose_accuracy_established'] is False,
        'PRIOR_R28_GATE'
    )

    pairs, connections, lidar = schedule(bag, r17)

    selected = [
        row
        for pair in pairs
        for row in pair
    ]

    decoded = fetch(
        bag, selected, connections, lidar
    )

    baseline = r18['samples'][TOPIC]

    need(
        [pairs[0][i][0] for i in (0, 1)] ==
        [s['chunk_offset'] for s in baseline],
        'R27_PAIR_INDEX_MATCH'
    )

    results = []

    for k, (first, second) in enumerate(pairs):
        previous = decoded[first[0]]
        current = decoded[second[0]]

        need(
            current[1]['header_stamp_ns'] >
            previous[1]['header_stamp_ns'],
            'NONINCREASING_SCAN_HEADER'
        )

        diagnostic = prior.candidate(
            previous[0], current[0]
        )

        if k == 0:
            reference = r27['registration_diagnostic']

            for field in (
                'rotation_previous_from_current',
                'translation_previous_from_current_m',
                'identity_nearest_neighbor_rmse_m',
                'candidate_nearest_neighbor_rmse_m',
            ):
                need(
                    np.allclose(
                        diagnostic[field],
                        reference[field],
                        rtol=1e-9,
                        atol=1e-9
                    ),
                    'R27_REPLAY_' + field
                )

        results.append({
            'pair_index': k,
            'scans': [
                previous[1],
                current[1]
            ],
            'observed_header_gap_ns':
                current[1]['header_stamp_ns']
                - previous[1]['header_stamp_ns'],
            'registration': diagnostic,
            'relative_motion_ground_truth_available': False,
        })

        print(
            'R29_PAIR=%d INITIAL_RMSE_M=%.6f CANDIDATE_RMSE_M=%.6f'
            % (
                k,
                diagnostic['identity_nearest_neighbor_rmse_m'],
                diagnostic['candidate_nearest_neighbor_rmse_m'],
            )
        )

    report = {
        'schema':
            'TRUST_ROBOT_R29_TRAIN_LIDAR_ADJACENT_PAIR_DIAGNOSTICS_V1',
        'trajectory_id': 'room_02',
        'split': 'train',
        'github_baseline':
            'd1c8aa7811619d096865f9b5f23a0ca7e940fa81',
        'authenticated_bag_sha256':
            r17['file_sha256'],
        'prior_reports_sha256': {
            'r17': sha(r17p.read_bytes()),
            'r18': sha(r18p.read_bytes()),
            'r27': sha(r27_path.read_bytes()),
            'r28': sha(r28_path.read_bytes()),
        },
        'sampling_rule':
            'eight_evenly_spaced_index_anchors_each_with_next_lidar_scan',
        'eligible_lidar_chunk_count': 752,
        'selected_unique_chunks': 16,
        'pair_count': COUNT,
        'per_scan_selected_points': 512,
        'fixed_registration_iterations': 10,
        'pair_order':
            'previous_lidar_T_current_lidar_diagnostic_only',
        'pairs': results,
        'interpretation':
            'fixed_iteration_point_to_point_registration_descriptive_only_no_stability_threshold',
        'physical_capture_time_verified': False,
        'cross_modal_alignment_performed': False,
        'full_extrinsics_verified': False,
        'independent_ground_truth_scored': False,
        'health_model_training_authorized': False,
        'real_sensor_factor_execution_authorized': False,
        'm2dgr_scoring_authorized': False,
        'pose_accuracy_established': False,
        'statistical_stability_established': False,
        'real_pose_factors_generated': 0,
        'health_labels_generated': 0,
        'new_sensor_acquisitions': 0,
        'raw_recording_modified': False,
        'github_modified': False,
    }

    safety(report)

    with output.open('x', encoding='utf-8') as f:
        json.dump(
            report, f,
            sort_keys=True,
            indent=2,
            allow_nan=False
        )
        f.write('\n')

    print(
        'R29_FIRST_PAIR_R27_BASELINE=RECOMPUTED_AND_MATCHED'
    )
    print('R29_REAL_RECORDED_SCAN_PAIRS=8')
    print('R29_SOURCE_LIDAR_SCANS=16')
    print('R29_CANDIDATES=DIAGNOSTIC_ONLY')


if __name__ == '__main__':
    run(
        *(pathlib.Path(x) for x in sys.argv[1:7])
    )
