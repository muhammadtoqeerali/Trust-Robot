"""Independent source relocation and exhaustive numerical verification."""

import hashlib
import json
import pathlib
import struct
import sys

import numpy as np
import r18_decode as reader
import r27_independent_verify as independent
import r29_multipair as engine


def need(ok, reason):
    if not ok:
        raise ValueError(
            'R29_INDEPENDENT_DENIED:' + reason
        )


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def load(path):
    return json.loads(
        pathlib.Path(path).read_text()
    )


def verify(
    bag, archive, r27, r28,
    report_path, destination
):
    report = load(report_path)
    engine.safety(report)

    r17p = archive / 'r17/r17_recorded_index.json'
    r18p = archive / 'r18/r18_bounded_recorded_samples.json'

    r17 = load(r17p)
    r18 = load(r18p)

    need(
        report['authenticated_bag_sha256'] ==
        r17['file_sha256'] ==
        r18['recording_sha256'],
        'SOURCE_CHAIN'
    )

    need(
        report['prior_reports_sha256'] == {
            'r17': sha(r17p.read_bytes()),
            'r18': sha(r18p.read_bytes()),
            'r27': sha(r27.read_bytes()),
            'r28': sha(r28.read_bytes()),
        },
        'REPORT_PINS'
    )

    # Independently rebuild the chunk-selection schedule.
    connections = {
        c['id']: c for c in r17['connections']
    }

    lidar_ids = [
        c['id']
        for c in r17['connections']
        if c['topic'] == '/velodyne_points'
    ]

    need(
        len(lidar_ids) == 1,
        'LIDAR_CONNECTION'
    )

    lidar = lidar_ids[0]
    available = []

    with bag.open('rb') as f:
        need(
            reader.read_exact(f, 13) ==
            b'#ROSBAG V2.0\n',
            'BAG_VERSION'
        )

        header, _ = reader.file_record(f, 8192)
        need(
            header.get(b'op') == b'\x03',
            'FILE_HEADER'
        )

        f.seek(
            struct.unpack(
                '<Q', header[b'index_pos']
            )[0]
        )

        for _ in range(r17['connection_count']):
            h, _ = reader.file_record(f)
            need(
                h.get(b'op') == b'\x07',
                'CONNECTION_RECORD'
            )

        for _ in range(r17['chunk_count']):
            h, data = reader.file_record(f)

            need(
                h.get(b'op') == b'\x06',
                'CHUNK_LEDGER'
            )

            offset = struct.unpack(
                '<Q', h[b'chunk_pos']
            )[0]

            n = reader.u32(h[b'count'])

            need(
                len(data) == 8 * n,
                'CHUNK_INFO_BYTES'
            )

            items = [
                struct.unpack_from(
                    '<II', data, 8 * j
                )
                for j in range(n)
            ]

            need(
                len({x[0] for x in items}) == n
                and all(
                    x[0] in connections
                    for x in items
                ),
                'LEDGER_KEYS'
            )

            counts = dict(items)

            if lidar in counts:
                need(
                    counts[lidar] == 1,
                    'LIDAR_MESSAGES_PER_CHUNK'
                )
                available.append(
                    (offset, counts)
                )

    need(
        len(available) == 752
        and len({
            x[0] for x in available
        }) == 752,
        'TOTAL_LIDAR_CHUNKS'
    )

    anchors = [
        (i * (len(available) - 2)) // 7
        for i in range(8)
    ]

    pairs = [
        (available[j], available[j + 1])
        for j in anchors
    ]

    need(
        report['eligible_lidar_chunk_count'] == 752
        and report['selected_unique_chunks'] == 16,
        'SCHEDULE_COUNTS'
    )

    with bag.open('rb') as f:
        for k, (previous, current) in enumerate(pairs):
            pair = report['pairs'][k]

            need(
                pair['pair_index'] == k
                and pair['observed_header_gap_ns'] > 0,
                'PAIR_SEQUENCE'
            )

            xyz_pair = []

            for j, (offset, expected_counts) in enumerate(
                (previous, current)
            ):
                bound = pair['scans'][j]

                need(
                    bound['chunk_offset'] == offset
                    and bound['connection_id'] == lidar,
                    'CHUNK_CHOICE'
                )

                raw, compression = reader.chunk_data(
                    f, offset
                )

                counts = {}
                found = []

                for cid, record_time, view in reader.messages(
                    raw, connections
                ):
                    counts[cid] = counts.get(cid, 0) + 1

                    if cid == lidar:
                        found.append((
                            record_time,
                            bytes(view)
                        ))

                need(
                    counts == expected_counts
                    and len(found) == 1,
                    'CHUNK_COUNTS'
                )

                bag_time, body = found[0]

                xyz, indices, meta = independent.read_scan(
                    body, reader
                )

                need(
                    bound['bag_record_time_ns'] == bag_time
                    and bound['serialized_message_sha256']
                    == sha(body)
                    and bound['serialized_message_bytes']
                    == len(body),
                    'SERIALIZED_SOURCE'
                )

                need(
                    meta['header_stamp_ns']
                    == bound['header_stamp_ns']
                    and meta['frame_id']
                    == bound['frame_id']
                    and meta['point_count_total']
                    == bound['point_count_total'],
                    'HEADER_OR_POINTS'
                )

                need(
                    bound['selected_indices_sha256']
                    == sha(
                        indices.astype('<i8').tobytes()
                    )
                    and bound['selected_xyz_float64_le_sha256']
                    == sha(
                        xyz.astype('<f8').tobytes()
                    ),
                    'POINT_SUBSET'
                )

                xyz_pair.append(xyz)

            need(
                pair['observed_header_gap_ns']
                == (
                    pair['scans'][1]['header_stamp_ns']
                    - pair['scans'][0]['header_stamp_ns']
                ),
                'STAMP_GAP'
            )

            (
                R, t, identity,
                final, median, maximum
            ) = independent.brute(
                *xyz_pair
            )

            diag = pair['registration']

            comparisons = [
                (
                    diag['rotation_previous_from_current'],
                    R
                ),
                (
                    diag['translation_previous_from_current_m'],
                    t
                ),
                (
                    diag['identity_nearest_neighbor_rmse_m'],
                    identity
                ),
                (
                    diag['candidate_nearest_neighbor_rmse_m'],
                    final
                ),
                (
                    diag['candidate_median_nn_distance_m'],
                    median
                ),
                (
                    diag['candidate_max_nn_distance_m'],
                    maximum
                ),
            ]

            need(
                all(
                    np.allclose(
                        x, y,
                        rtol=1e-6,
                        atol=1e-6
                    )
                    for x, y in comparisons
                ),
                'INDEPENDENT_NUMERIC_' + str(k)
            )

    summary = {
        'schema':
            'TRUST_ROBOT_R29_INDEPENDENT_RECORDED_LIDAR_MULTIPAIRS_V1',
        'source_report_sha256':
            sha(report_path.read_bytes()),
        'authenticated_lidar_messages_relocated': 16,
        'adjacent_pairs_verified': 8,
        'independently_reconstructed_schedule': True,
        'brute_force_registration_numeric_match': True,
        'physical_capture_semantics_verified': False,
        'real_pose_factors_authorized': False,
        'ground_truth_scoring_performed': False,
    }

    with destination.open('x', encoding='utf-8') as f:
        json.dump(
            summary, f,
            sort_keys=True,
            indent=2,
            allow_nan=False
        )
        f.write('\n')

    print('R29_INDEPENDENT_RECORDED_MESSAGE_HASHES=16_VERIFIED')
    print('R29_INDEPENDENT_ADJACENT_SCHEDULE=8_PAIRS_RECONSTRUCTED')
    print('R29_INDEPENDENT_BRUTE_FORCE_REGISTRATIONS=8_NUMERIC_MATCH')
    print('R29_INDEPENDENT_VALIDATION=PASS')


if __name__ == '__main__':
    verify(
        *(pathlib.Path(x) for x in sys.argv[1:7])
    )
