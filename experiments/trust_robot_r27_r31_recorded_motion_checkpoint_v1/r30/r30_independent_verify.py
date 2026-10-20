"""Independent brute-force registration, geometry and provenance checks."""

import hashlib
import json
import pathlib
import sys

import numpy as np

import r18_decode as reader
import r27_independent_verify as reference
import r30_geometry as engine


def need(condition, reason):
    if not condition:
        raise ValueError(
            'R30_INDEPENDENT_DENIED:' + reason
        )


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def close(a, b):
    return bool(
        np.allclose(
            a, b,
            rtol=2e-6,
            atol=2e-6
        )
    )


def metrics(target, source, rotation, translation):
    moved = source @ rotation.T + translation

    squared = np.sum(
        (
            moved[:, None, :]
            - target[None, :, :]
        ) ** 2,
        axis=2
    )

    ids = np.argmin(squared, axis=1)
    distances = np.sqrt(
        squared[np.arange(len(source)), ids]
    )

    return [
        float(len(np.unique(ids)) / len(ids)),
        float(np.median(distances)),
        float(np.percentile(distances, 90)),
    ]


def shape(xyz):
    centered = xyz - xyz.mean(axis=0)

    singular = np.linalg.svd(
        centered,
        compute_uv=False
    )

    return np.sort(
        (singular * singular) / len(xyz)
    )


def verify(
    bag, r17_path, r29_path,
    report_path, output
):
    info = json.loads(r17_path.read_text())
    older = json.loads(r29_path.read_text())
    report = json.loads(report_path.read_text())

    engine.safety(report)

    need(
        report['r17_sha256'] == sha(r17_path.read_bytes())
        and report['r29_sha256'] == sha(r29_path.read_bytes())
        and report['authenticated_bag_sha256']
        == info['file_sha256']
        == older['authenticated_bag_sha256'],
        'SOURCE_BINDING'
    )

    connections = {
        c['id']: c for c in info['connections']
    }

    lidar_ids = [
        c['id']
        for c in info['connections']
        if c['topic'] == '/velodyne_points'
    ]

    need(
        len(lidar_ids) == 1,
        'LIDAR_ID'
    )

    observed_offsets = set()
    verified_pairs = []

    with bag.open('rb') as handle:
        for k, pair in enumerate(older['pairs']):
            scans = []

            for source in pair['scans']:
                offset = source['chunk_offset']

                need(
                    offset not in observed_offsets,
                    'DUPLICATE_LIDAR_CHUNK'
                )
                observed_offsets.add(offset)

                raw, compression = reader.chunk_data(
                    handle, offset
                )

                found = []

                for cid, timestamp, body in reader.messages(
                    raw, connections
                ):
                    if cid == lidar_ids[0]:
                        found.append(
                            (timestamp, bytes(body))
                        )

                need(
                    len(found) == 1,
                    'LIDAR_MESSAGE_COUNT'
                )

                stamp, blob = found[0]

                need(
                    stamp == source['bag_record_time_ns']
                    and sha(blob) ==
                        source['serialized_message_sha256']
                    and len(blob) ==
                        source['serialized_message_bytes'],
                    'RECORDED_BYTE_PROVENANCE'
                )

                xyz, indices, meta = reference.read_scan(
                    blob, reader
                )

                need(
                    meta['header_stamp_ns'] ==
                        source['header_stamp_ns']
                    and meta['frame_id'] ==
                        source['frame_id']
                    and meta['point_count_total'] ==
                        source['point_count_total'],
                    'SOURCE_HEADER'
                )

                need(
                    sha(indices.astype('<i8').tobytes())
                        == source['selected_indices_sha256']
                    and sha(xyz.astype('<f8').tobytes())
                        == source['selected_xyz_float64_le_sha256'],
                    'SOURCE_POINT_SELECTION'
                )

                scans.append(xyz)

            previous, current = scans
            row = report['pairs'][k]

            need(
                row['source_message_sha256'] == [
                    s['serialized_message_sha256']
                    for s in pair['scans']
                ],
                'REPORT_SCAN_IDENTITY'
            )

            for j, xyz in enumerate(scans):
                eigenvalues = shape(xyz)
                recorded = row['geometry'][j]

                need(
                    close(
                        recorded[
                            'centered_covariance_eigenvalues_m2'
                        ],
                        eigenvalues
                    )
                    and close(
                        recorded[
                            'smallest_over_largest_eigenvalue'
                        ],
                        eigenvalues[0] / eigenvalues[2]
                    )
                    and close(
                        recorded[
                            'middle_over_largest_eigenvalue'
                        ],
                        eigenvalues[1] / eigenvalues[2]
                    ),
                    'COVARIANCE_SPECTRUM'
                )

            forward = reference.brute(
                previous, current
            )
            backward = reference.brute(
                current, previous
            )

            for diagnostic, values in (
                (row['forward'], forward),
                (row['reverse'], backward),
            ):
                rotation, translation, identity, final, median, maximum = values

                checks = (
                    ('rotation_previous_from_current', rotation),
                    ('translation_previous_from_current_m', translation),
                    ('identity_nearest_neighbor_rmse_m', identity),
                    ('candidate_nearest_neighbor_rmse_m', final),
                    ('candidate_median_nn_distance_m', median),
                    ('candidate_max_nn_distance_m', maximum),
                )

                for key, expected in checks:
                    need(
                        close(diagnostic[key], expected),
                        'INDEPENDENT_REGISTRATION_' + key
                    )

            rf, tf = forward[:2]
            rr, tr = backward[:2]

            rotation_roundtrip = rf @ rr

            angle = float(np.degrees(np.arccos(
                np.clip(
                    (np.trace(rotation_roundtrip) - 1.0) / 2.0,
                    -1.0, 1.0
                )
            )))

            translation_roundtrip = float(
                np.linalg.norm(tf + rf @ tr)
            )

            need(
                close(
                    row['inverse_consistency'][
                        'roundtrip_rotation_deg'
                    ],
                    angle
                )
                and close(
                    row['inverse_consistency'][
                        'roundtrip_translation_m'
                    ],
                    translation_roundtrip
                ),
                'INVERSE_CLOSURE'
            )

            directional = (
                (
                    row['forward_correspondence'],
                    metrics(previous, current, rf, tf),
                ),
                (
                    row['reverse_correspondence'],
                    metrics(current, previous, rr, tr),
                ),
            )

            for recorded, expected in directional:
                actual = [
                    recorded['unique_target_fraction'],
                    recorded['nearest_neighbor_median_m'],
                    recorded['nearest_neighbor_p90_m'],
                ]

                need(
                    close(actual, expected),
                    'INDEPENDENT_NN_UNIQUENESS'
                )

            verified_pairs.append(row)

    need(
        len(observed_offsets) == 16,
        'SCAN_COUNT'
    )

    summary = {
        'max_roundtrip_translation_m': max(
            p['inverse_consistency'][
                'roundtrip_translation_m'
            ] for p in verified_pairs
        ),
        'max_roundtrip_rotation_deg': max(
            p['inverse_consistency'][
                'roundtrip_rotation_deg'
            ] for p in verified_pairs
        ),
        'min_geometry_smallest_largest_ratio': min(
            g['smallest_over_largest_eigenvalue']
            for p in verified_pairs
            for g in p['geometry']
        ),
        'min_nn_unique_target_fraction': min(
            p[d]['unique_target_fraction']
            for p in verified_pairs
            for d in (
                'forward_correspondence',
                'reverse_correspondence'
            )
        ),
    }

    need(
        all(
            close(summary[key], report['summary'][key])
            for key in summary
        ),
        'SUMMARY'
    )

    result = {
        'schema':
            'TRUST_ROBOT_R30_INDEPENDENT_GEOMETRY_AND_INVERSE_CONSISTENCY_V1',
        'source_report_sha256':
            sha(report_path.read_bytes()),
        'original_lidar_messages_verified': 16,
        'independent_brute_force_registrations': 16,
        'geometry_spectra_verified': 16,
        'bidirectional_roundtrips_verified': 8,
        'science_factor_admission': False,
        'independent_reference_accuracy_scored': False,
    }

    with output.open('x', encoding='utf-8') as f:
        json.dump(
            result, f,
            indent=2,
            sort_keys=True,
            allow_nan=False
        )
        f.write('\n')

    print('R30_INDEPENDENT_SOURCE_SCANS=16_VERIFIED')
    print('R30_INDEPENDENT_BRUTE_FORCE_REGISTRATIONS=16_NUMERIC_MATCH')
    print('R30_INVERSE_AND_GEOMETRY_DIAGNOSTICS=8_PAIRS_VERIFIED')
    print('R30_INDEPENDENT_VALIDATION=PASS')


if __name__ == '__main__':
    verify(
        *(pathlib.Path(x) for x in sys.argv[1:6])
    )
