"""TRAIN-only LiDAR geometry and directional consistency diagnostics."""

import hashlib
import json
import pathlib
import sys

import numpy as np
from scipy.spatial import cKDTree

import r29_multipair as source
import r27_lidar_motion as frontend


def need(condition, reason):
    if not condition:
        raise ValueError('R30_DENIED:' + reason)


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def load(path):
    return json.loads(pathlib.Path(path).read_text())


def geometry(xyz):
    need(
        xyz.shape == (512, 3)
        and bool(np.isfinite(xyz).all()),
        'XYZ_INPUT'
    )

    centered = xyz - xyz.mean(axis=0)
    covariance = (centered.T @ centered) / len(xyz)

    eigenvalues = np.maximum(
        np.linalg.eigvalsh(covariance), 0.0
    )

    need(
        float(eigenvalues[2]) > 0.0,
        'ZERO_GEOMETRY'
    )

    return {
        'centered_covariance_eigenvalues_m2':
            [float(v) for v in eigenvalues],
        'smallest_over_largest_eigenvalue':
            float(eigenvalues[0] / eigenvalues[2]),
        'middle_over_largest_eigenvalue':
            float(eigenvalues[1] / eigenvalues[2]),
    }


def correspondence(target, points, rotation, translation):
    transformed = points @ rotation.T + translation

    distances, indices = cKDTree(target).query(
        transformed, k=1, workers=1
    )

    need(
        bool(np.isfinite(distances).all()),
        'NONFINITE_NEIGHBORS'
    )

    return {
        'unique_target_fraction':
            float(len(np.unique(indices)) / len(indices)),
        'nearest_neighbor_median_m':
            float(np.median(distances)),
        'nearest_neighbor_p90_m':
            float(np.percentile(distances, 90)),
    }


def closure(forward, reverse):
    rf = np.asarray(
        forward['rotation_previous_from_current'],
        dtype=np.float64
    )
    tf = np.asarray(
        forward['translation_previous_from_current_m'],
        dtype=np.float64
    )
    rr = np.asarray(
        reverse['rotation_previous_from_current'],
        dtype=np.float64
    )
    tr = np.asarray(
        reverse['translation_previous_from_current_m'],
        dtype=np.float64
    )

    need(
        rf.shape == (3, 3)
        and rr.shape == (3, 3)
        and tf.shape == (3,)
        and tr.shape == (3,),
        'TRANSFORM_SHAPE'
    )

    rotation_roundtrip = rf @ rr

    cosine = float(np.clip(
        (np.trace(rotation_roundtrip) - 1.0) / 2.0,
        -1.0, 1.0
    ))

    return {
        'roundtrip_translation_m':
            float(np.linalg.norm(tf + rf @ tr)),
        'roundtrip_rotation_deg':
            float(np.degrees(np.arccos(cosine))),
    }


FLAGS = (
    'physical_capture_time_verified',
    'cross_modal_alignment_performed',
    'full_extrinsics_verified',
    'independent_ground_truth_scored',
    'health_model_training_authorized',
    'real_sensor_factor_execution_authorized',
    'm2dgr_scoring_authorized',
    'pose_accuracy_established',
    'statistical_stability_established',
    'confidence_threshold_frozen',
    'raw_recording_modified',
    'github_modified',
)

COUNTS = (
    'real_pose_factors_generated',
    'health_labels_generated',
    'new_sensor_acquisitions',
)


def safety(report):
    need(
        report.get('schema') ==
        'TRUST_ROBOT_R30_RECORDED_LIDAR_GEOMETRY_CONFIDENCE_LIMITS_V1'
        and report.get('trajectory_id') == 'room_02'
        and report.get('split') == 'train',
        'SCOPE'
    )

    need(
        report.get('pair_count') == 8
        and report.get('scans_considered') == 16
        and report.get('subset_size') == 512
        and len(report.get('pairs', [])) == 8,
        'PLAN'
    )

    need(
        all(report.get(k) is False for k in FLAGS),
        'FALSE_GATE'
    )

    need(
        all(
            type(report.get(k)) is int
            and report[k] == 0
            for k in COUNTS
        ),
        'ZERO_GATE'
    )

    need(
        [p.get('pair_index') for p in report['pairs']]
        == list(range(8)),
        'PAIR_SEQUENCE'
    )

    for pair in report['pairs']:
        need(
            pair.get('forward_factor_admitted') is False
            and pair.get('reverse_factor_admitted') is False,
            'PAIR_GATE'
        )

        geometries = pair.get('geometry')

        need(
            type(geometries) is list
            and len(geometries) == 2,
            'GEOMETRY_COUNT'
        )

        for item in geometries:
            eigenvalues = item.get(
                'centered_covariance_eigenvalues_m2'
            )

            need(
                type(eigenvalues) is list
                and len(eigenvalues) == 3
                and all(
                    type(v) is float
                    and np.isfinite(v)
                    and v >= 0
                    for v in eigenvalues
                )
                and eigenvalues == sorted(eigenvalues)
                and eigenvalues[-1] > 0.0,
                'EIGENVALUES'
            )

        for key in (
            'roundtrip_translation_m',
            'roundtrip_rotation_deg'
        ):
            value = pair.get(
                'inverse_consistency', {}
            ).get(key)

            need(
                type(value) is float
                and np.isfinite(value)
                and value >= 0.0,
                'INVERSE_METRIC'
            )


def run(bag, r17_path, r29_path, destination):
    info = load(r17_path)
    prior = load(r29_path)

    need(
        prior['schema'] ==
        'TRUST_ROBOT_R29_TRAIN_LIDAR_ADJACENT_PAIR_DIAGNOSTICS_V1'
        and prior['trajectory_id'] == 'room_02'
        and prior['split'] == 'train'
        and prior['authenticated_bag_sha256']
        == info['file_sha256'],
        'PRIOR_PROVENANCE'
    )

    need(
        all(
            prior[key] is False
            for key in (
                'pose_accuracy_established',
                'statistical_stability_established',
                'real_sensor_factor_execution_authorized',
                'm2dgr_scoring_authorized',
            )
        )
        and prior['real_pose_factors_generated'] == 0,
        'R29_GATES'
    )

    pairs, connections, lidar = source.schedule(
        bag, info
    )

    decoded = source.fetch(
        bag,
        [row for pair in pairs for row in pair],
        connections,
        lidar
    )

    rows = []

    for k, pair in enumerate(pairs):
        previous, current = (
            decoded[pair[j][0]] for j in (0, 1)
        )

        need(
            prior['pairs'][k]['pair_index'] == k
            and prior['pairs'][k]['scans'] ==
                [previous[1], current[1]],
            'EXACT_R29_SOURCE'
        )

        forward = frontend.candidate(
            previous[0], current[0]
        )

        for key in (
            'rotation_previous_from_current',
            'translation_previous_from_current_m',
            'identity_nearest_neighbor_rmse_m',
            'candidate_nearest_neighbor_rmse_m',
        ):
            need(
                np.allclose(
                    forward[key],
                    prior['pairs'][k]['registration'][key],
                    rtol=1e-9,
                    atol=1e-9
                ),
                'R29_FORWARD_REPLAY_' + key
            )

        reverse = frontend.candidate(
            current[0], previous[0]
        )

        rf = np.asarray(
            forward['rotation_previous_from_current']
        )
        tf = np.asarray(
            forward['translation_previous_from_current_m']
        )
        rr = np.asarray(
            reverse['rotation_previous_from_current']
        )
        tr = np.asarray(
            reverse['translation_previous_from_current_m']
        )

        result = {
            'pair_index': k,
            'source_message_sha256': [
                previous[1]['serialized_message_sha256'],
                current[1]['serialized_message_sha256'],
            ],
            'geometry': [
                geometry(previous[0]),
                geometry(current[0]),
            ],
            'forward': forward,
            'reverse': reverse,
            'forward_correspondence': correspondence(
                previous[0], current[0], rf, tf
            ),
            'reverse_correspondence': correspondence(
                current[0], previous[0], rr, tr
            ),
            'inverse_consistency': closure(
                forward, reverse
            ),
            'forward_factor_admitted': False,
            'reverse_factor_admitted': False,
        }

        rows.append(result)

        print(
            'R30_PAIR=%d ROUNDTRIP_TRANSLATION_M=%.6f '
            'ROUNDTRIP_ROTATION_DEG=%.6f'
            % (
                k,
                result['inverse_consistency'][
                    'roundtrip_translation_m'
                ],
                result['inverse_consistency'][
                    'roundtrip_rotation_deg'
                ],
            )
        )

    report = {
        'schema':
            'TRUST_ROBOT_R30_RECORDED_LIDAR_GEOMETRY_CONFIDENCE_LIMITS_V1',
        'trajectory_id': 'room_02',
        'split': 'train',
        'authenticated_bag_sha256':
            info['file_sha256'],
        'github_baseline':
            'd1c8aa7811619d096865f9b5f23a0ca7e940fa81',
        'r17_sha256':
            sha(r17_path.read_bytes()),
        'r29_sha256':
            sha(r29_path.read_bytes()),
        'pair_count': 8,
        'scans_considered': 16,
        'subset_size': 512,
        'method':
            '10_fixed_iterations_identity_initialized_both_directions_independent_subsets',
        'interpretation':
            'sensitivity_and_geometry_only_no_empirically_calibrated_confidence',
        'pairs': rows,
        'summary': {
            'max_roundtrip_translation_m': max(
                p['inverse_consistency'][
                    'roundtrip_translation_m'
                ] for p in rows
            ),
            'max_roundtrip_rotation_deg': max(
                p['inverse_consistency'][
                    'roundtrip_rotation_deg'
                ] for p in rows
            ),
            'min_geometry_smallest_largest_ratio': min(
                g['smallest_over_largest_eigenvalue']
                for p in rows
                for g in p['geometry']
            ),
            'min_nn_unique_target_fraction': min(
                p[d]['unique_target_fraction']
                for p in rows
                for d in (
                    'forward_correspondence',
                    'reverse_correspondence',
                )
            ),
        },
        **{key: False for key in FLAGS},
        **{key: 0 for key in COUNTS},
    }

    safety(report)

    with destination.open('x', encoding='utf-8') as f:
        json.dump(
            report, f,
            indent=2,
            sort_keys=True,
            allow_nan=False
        )
        f.write('\n')

    print('R30_DIRECTIONAL_PAIR_DIAGNOSTICS=8_COMPLETE')
    print('R30_RELATIVE_POSE_CONFIDENCE=NOT_CALIBRATED')


if __name__ == '__main__':
    run(
        *(pathlib.Path(x) for x in sys.argv[1:5])
    )
