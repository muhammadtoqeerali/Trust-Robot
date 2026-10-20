"""Independent no-bag IMU and SO3 numerical verification."""

import hashlib
import json
import math
import pathlib
import sys

def need(ok, reason):
    if not ok:
        raise ValueError('R37_INDEPENDENT_DENIED:' + reason)

def digest(path):
    return hashlib.sha256(
        pathlib.Path(path).read_bytes()
    ).hexdigest()

def load(path):
    return json.loads(pathlib.Path(path).read_text())

def close(a, b):
    if a is None or b is None:
        return a is b

    if type(a) is bool or type(b) is bool:
        return a is b

    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(
            a, b, rel_tol=1e-9, abs_tol=1e-11
        )

    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return (
            len(a) == len(b)
            and all(close(x, y) for x, y in zip(a, b))
        )

    return a == b

def qexp(vector):
    angle = math.sqrt(sum(x*x for x in vector))

    scale = (
        0.5 - angle*angle/48
        if angle < 1e-12
        else math.sin(angle/2)/angle
    )

    return (
        math.cos(angle/2),
        vector[0]*scale,
        vector[1]*scale,
        vector[2]*scale
    )

def qmul(a, b):
    w, x, y, z = a
    t, p, q, r = b

    return (
        w*t-x*p-y*q-z*r,
        w*p+x*t+y*r-z*q,
        w*q-x*r+y*t+z*p,
        w*r+x*q-y*p+z*t
    )

def qmatrix(q):
    w, x, y, z = q

    return [
        [
            1-2*(y*y+z*z),
            2*(x*y-w*z),
            2*(x*z+w*y)
        ],
        [
            2*(x*y+w*z),
            1-2*(x*x+z*z),
            2*(y*z-w*x)
        ],
        [
            2*(x*z-w*y),
            2*(y*z+w*x),
            1-2*(x*x+y*y)
        ]
    ]

def verify(root, report_path, destination):
    ready = load(report_path)

    expected_counts = {
        'r33': 7,
        'r34': 4,
        'r35': 5,
        'r36': 5
    }

    need(
        ready['schema'] ==
        'TRUST_ROBOT_R37_R33_R36_NONFACTOR_CHECKPOINT_READINESS_V1'
        and ready['phase_counts'] == expected_counts
        and ready['off_git_artifact_count'] == 21
        and ready['readiness_decision'] ==
        'READY_FOR_SHA_PINNED_R33_R37_NONFACTOR_GITHUB_CHECKPOINT',
        'READINESS_SCOPE'
    )

    need(
        ready['trajectory_id'] == 'room_02'
        and ready['split'] == 'train'
        and ready['raw_bag_archived'] is False
        and ready['scientific_pose_factors'] == 0
        and ready['health_labels'] == 0
        and ready['pose_accuracy_scores'] == 0,
        'SCIENCE_SCOPE'
    )

    for key in (
        'real_sensor_factor_execution_authorized',
        'health_model_training_authorized',
        'm2dgr_scoring_authorized',
        'physical_capture_time_verified',
        'cross_modal_alignment_performed',
        'full_extrinsics_verified',
        'statistical_stability_established',
        'raw_recording_modified',
        'github_modified'
    ):
        need(ready.get(key) is False, 'SCIENCE_GATE:' + key)

    files = ready['source_sha256']

    need(
        len(files) == 21
        and {
            k: sum(
                p.startswith(k + '/')
                for p in files
            )
            for k in expected_counts
        } == expected_counts,
        'SOURCE_INVENTORY'
    )

    def item(name):
        matches = [
            key for key in files
            if key.endswith('/' + name)
        ]

        need(len(matches) == 1, 'ITEM:' + name)

        key = matches[0]
        path = root / key.split('/', 1)[1]

        need(
            path.is_file()
            and not path.is_symlink()
            and path.stat().st_nlink == 1
            and digest(path) == files[key],
            'SHA:' + name
        )

        return path

    for key, desired in files.items():
        path = root / key.split('/', 1)[1]

        need(
            path.is_file()
            and not path.is_symlink()
            and digest(path) == desired,
            'SOURCE_SHA:' + key
        )

    r33 = load(item('r33_camera_multipair_pixel_diagnostics_v1.json'))
    v33 = load(item('r33_independent_validation_v1.json'))

    r34 = load(item('r34_imu_short_interval_diagnostics_v1.json'))
    v34 = load(item('r34_independent_validation_v1.json'))

    r35 = load(item('r35_imu_variation_frame_v1.json'))
    v35 = load(item('r35_independent_validation_v1.json'))

    r36 = load(item('r36_gyro_window_candidates_v1.json'))
    v36 = load(item('r36_independent_validation_v1.json'))

    provenance = load(
        item('r33_failed_baseline_repair_provenance_v1.json')
    )

    for name in (
        'r33_camera_multipair.py',
        'r33_independent_verify.py'
    ):
        failed = name.replace(
            '.py', '_initial_failed_v1.py.saved'
        )

        row = provenance['readers'][name]

        need(
            row['failed_sha256'] == digest(item(failed))
            and row['repaired_sha256'] == digest(item(name))
            and row['failed_backup'] == failed,
            'R33_FAILURE_AND_REPAIR'
        )

    proof_rows = (
        (
            'r33_camera_multipair_pixel_diagnostics_v1.json',
            v33, 'source_report_sha256'
        ),
        (
            'r34_imu_short_interval_diagnostics_v1.json',
            v34, 'source_report_sha256'
        ),
        (
            'r35_imu_variation_frame_v1.json',
            v35, 'r35_report_sha256'
        ),
        (
            'r36_gyro_window_candidates_v1.json',
            v36, 'source_report_sha256'
        )
    )

    for filename, validation, key in proof_rows:
        need(
            validation[key] == digest(item(filename)),
            'VERIFICATION_LINK:' + filename
        )

    need(
        v33['recorded_camera_messages_verified'] == 16
        and v33['independently_recomputed_pair_tracks'] == 8
        and v33['r31_baseline_identical'] is True,
        'R33_INDEPENDENT'
    )

    need(
        v34['independent_trapezoid_intervals_recomputed'] == 16
        and v35['intervals_independently_recomputed'] == 16
        and v36['independently_recomputed_three_sample_windows'] == 16,
        'IMU_INDEPENDENT'
    )

    need(
        r34['source_report_sha256']['r33'] ==
        digest(item('r33_camera_multipair_pixel_diagnostics_v1.json'))
        and r35['r34_source_report_sha256'] ==
        digest(item('r34_imu_short_interval_diagnostics_v1.json'))
        and r36['source_report_sha256']['r35'] ==
        digest(item('r35_imu_variation_frame_v1.json')),
        'CROSS_PHASE_CHAIN'
    )

    checked_camera = 0
    checked_intervals = 0
    checked_windows = 0
    source_ids = set()

    need(len(r33['pairs']) == 8, 'CAMERA_COUNT')

    for k, pair in enumerate(r33['pairs']):
        motion = pair['pixel_motion']

        need(
            pair['pair_index'] == k
            and len(pair['frames']) == 2
            and pair['metric_pose_qualified'] is False,
            'CAMERA_PAIR'
        )

        need(
            motion['camera_pose_factor'] is None
            and motion['metric_translation_m'] is None
            and 0 <= motion['forward_backward_consistent_count']
            <= motion['initial_corner_count'] <= 400,
            'CAMERA_NONFACTOR'
        )

        checked_camera += 1

    for topic, frame, expected_unknown in (
        ('/camera/imu', 'camera_imu_optical_frame', 16),
        ('/handsfree/imu', 'base_link', 0)
    ):
        short = r34['streams'][topic]
        variations = r35['streams'][topic]['intervals']
        windows = r36['streams'][topic]

        need(
            len(short) == len(variations) == len(windows) == 8
            and r35['streams'][topic]['recorded_frame_id'] == frame,
            'STREAM_FRAMES'
        )

        unknown_count = 0

        for k, (pair, variation) in enumerate(
            zip(short, variations)
        ):
            s0, s1 = pair['samples']
            m0, m1 = pair['messages']
            diagnostic = pair['diagnostic']

            need(
                pair['pair_index'] == variation['pair_index'] == k
                and m0['frame_id'] == m1['frame_id'] == frame
                and m1['sequence'] == m0['sequence'] + 1,
                'SHORT_SEQUENCE'
            )

            dt = (
                m1['header_stamp_ns']
                - m0['header_stamp_ns']
            ) * 1e-9

            need(
                dt > 0
                and close(
                    diagnostic[
                        'observed_header_dt_s_not_verified_capture_time'
                    ],
                    dt
                ),
                'SHORT_DT'
            )

            gyro_integral = [
                (
                    s0['gyro_rad_s'][j]
                    + s1['gyro_rad_s'][j]
                ) * dt / 2
                for j in range(3)
            ]

            force_integral = [
                (
                    s0['specific_force_m_s2'][j]
                    + s1['specific_force_m_s2'][j]
                ) * dt / 2
                for j in range(3)
            ]

            need(
                close(
                    diagnostic[
                        'gyro_trapezoid_component_integrals_rad'
                    ],
                    gyro_integral
                )
                and close(
                    diagnostic[
                        'raw_specific_force_component_integrals_m_s'
                    ],
                    force_integral
                )
                and close(
                    diagnostic['gyro_integral_vector_norm_rad'],
                    math.sqrt(
                        sum(x*x for x in gyro_integral)
                    )
                ),
                'INDEPENDENT_IMU_TRAPEZOID'
            )

            need(
                close(
                    variation['gyro_sample_delta_norm_rad_s'],
                    math.dist(
                        s0['gyro_rad_s'],
                        s1['gyro_rad_s']
                    )
                )
                and close(
                    variation['specific_force_sample_delta_norm_m_s2'],
                    math.dist(
                        s0['specific_force_m_s2'],
                        s1['specific_force_m_s2']
                    )
                )
                and close(
                    variation[
                        'observed_header_dt_ms_not_capture_clock_proof'
                    ],
                    dt*1e3
                ),
                'INDEPENDENT_IMU_VARIATION'
            )

            unknown = sum(
                int(s['orientation_covariance_unknown_sentinel'])
                for s in (s0, s1)
            )

            need(
                variation['orientation_covariance_unknown_count']
                == unknown,
                'ORIENTATION_SENTINEL'
            )

            unknown_count += unknown
            checked_intervals += 1

        need(
            unknown_count == expected_unknown
            == r35['streams'][topic]['summary'][
                'orientation_covariance_unknown_samples'
            ],
            'ORIENTATION_TOTAL'
        )

        for k, window in enumerate(windows):
            messages = window['messages']
            samples = window['samples']
            numerical = window['gyro_numerics']

            need(
                window['window_index'] == k
                and window['physically_qualified_rotation'] is False
                and len(messages) == len(samples) == 3,
                'GYRO_WINDOW'
            )

            for source in messages:
                identity = (
                    topic,
                    source['chunk_offset'],
                    source['serialized_message_sha256']
                )

                need(
                    identity not in source_ids,
                    'REPEATED_GYRO_MESSAGE'
                )
                source_ids.add(identity)

            gaps = [
                messages[i+1]['header_stamp_ns']
                - messages[i]['header_stamp_ns']
                for i in (0, 1)
            ]

            need(
                numerical['header_gaps_ns'] == gaps
                and all(x > 0 for x in gaps),
                'GYRO_WINDOW_TIMES'
            )

            increments = []

            for i, dt_ns in enumerate(gaps):
                first = samples[i]['gyro_rad_s']
                second = samples[i+1]['gyro_rad_s']

                increments.append([
                    (first[j] + second[j])*0.5*dt_ns/1e9
                    for j in range(3)
                ])

            quat = qmul(
                qexp(increments[1]),
                qexp(increments[0])
            )

            angle = 2 * math.atan2(
                math.sqrt(sum(x*x for x in quat[1:])),
                abs(quat[0])
            )

            need(
                close(
                    numerical[
                        'midpoint_gyro_component_increments_rad'
                    ],
                    increments
                ),
                'GYRO_INCREMENT_REPLAY'
            )

            need(
                close(
                    numerical[
                        'two_step_composed_rotation_matrix_diagnostic'
                    ],
                    qmatrix(quat)
                )
                and close(
                    numerical[
                        'two_step_composed_rotation_angle_rad_diagnostic'
                    ],
                    angle
                ),
                'INDEPENDENT_SO3'
            )

            need(
                numerical['factor'] is None
                and numerical['translation_m'] is None
                and numerical['velocity_m_s'] is None
                and numerical['rotation_is_calibrated_robot_pose'] is False,
                'GYRO_NONFACTOR'
            )

            checked_windows += 1

    need(
        (
            checked_camera,
            checked_intervals,
            checked_windows,
            len(source_ids)
        ) == (8, 16, 16, 48),
        'RECOMPUTATION_COUNTS'
    )

    result = {
        'schema':
            'TRUST_ROBOT_R37_INDEPENDENT_READINESS_V1',
        'source_readiness_report_sha256': digest(report_path),
        'source_artifacts_independently_hashed': 21,
        'camera_pairs_source_bound': 8,
        'imu_trapezoid_intervals_recomputed': 16,
        'imu_interval_variations_recomputed': 16,
        'gyro_windows_recomputed_using_pure_python_quaternion': 16,
        'r33_original_failed_readers_preserved': True,
        'science_gates_closed': True,
        'raw_rosbag_read': False,
        'github_modified': False,
        'factor_admission': False
    }

    with destination.open('x', encoding='utf-8') as f:
        json.dump(
            result,
            f,
            sort_keys=True,
            indent=2,
            allow_nan=False
        )
        f.write('\n')

    print('R37_INDEPENDENT_SOURCE_FILES=21_HASH_MATCH')
    print('R37_INDEPENDENT_CAMERA_PAIRS=8_PROVENANCE_VERIFIED')
    print('R37_INDEPENDENT_R34_R35_IMU_INTERVALS=16_RECOMPUTED')
    print('R37_INDEPENDENT_R36_QUATERNION_WINDOWS=16_MATCHED')
    print('R37_INDEPENDENT_VALIDATION=PASS')

if __name__ == '__main__':
    verify(
        *(pathlib.Path(x) for x in sys.argv[1:4])
    )
