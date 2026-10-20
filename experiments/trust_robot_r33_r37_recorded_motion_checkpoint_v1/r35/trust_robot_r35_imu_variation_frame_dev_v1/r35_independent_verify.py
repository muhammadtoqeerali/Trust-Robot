"""Independent arithmetic from frozen R34 reports. No raw bag."""

import hashlib
import json
import math
import pathlib
import sys

def need(ok, reason):
    if not ok:
        raise ValueError('R35_INDEPENDENT_DENIED:' + reason)

def sha(path):
    return hashlib.sha256(
        pathlib.Path(path).read_bytes()
    ).hexdigest()

def load(path):
    return json.loads(pathlib.Path(path).read_text())

def eq(a, b):
    if type(a) is bool or type(b) is bool:
        return a is b

    if a is None or b is None:
        return a is None and b is None

    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(
            a, b,
            rel_tol=2e-11,
            abs_tol=2e-11
        )

    if isinstance(a, list) and isinstance(b, list):
        return (
            len(a) == len(b)
            and all(eq(x, y) for x, y in zip(a, b))
        )

    return a == b

def median(numbers):
    values = sorted(numbers)
    n = len(values)

    return (
        values[(n - 1) // 2]
        + values[n // 2]
    ) / 2

def verify(r34p, v34p, enginep, verifierp, reportp, outp):
    src = load(r34p)
    verified = load(v34p)
    report = load(reportp)

    need(
        src['schema'] ==
        'TRUST_ROBOT_R34_TRAIN_TWO_IMU_BOUNDED_INTERVALS_V1'
        and verified['schema'] ==
        'TRUST_ROBOT_R34_INDEPENDENT_TWO_IMU_INTERVALS_V1'
        and verified['source_report_sha256'] == sha(r34p)
        and verified['original_imu_messages_relocated'] == 32
        and verified['independent_trapezoid_intervals_recomputed'] == 16,
        'UPSTREAM_VALIDATION'
    )

    need(
        report['r34_source_report_sha256'] == sha(r34p)
        and report['r34_independent_validation_sha256'] == sha(v34p)
        and report['r34_engine_source_sha256'] == sha(enginep)
        and report['r34_independent_verifier_source_sha256']
        == sha(verifierp)
        and report['authenticated_bag_sha256']
        == src['authenticated_bag_sha256']
        and report['trajectory_id'] == src['trajectory_id']
        and report['split'] == src['split'] == 'train',
        'SOURCE_LINK'
    )

    need(
        report['stream_count'] == 2
        and report['interval_count'] == 16
        and report['previously_authenticated_messages_represented'] == 32
        and report['r35_reopened_raw_rosbag'] is False,
        'REPORT_SCOPE'
    )

    for field in (
        'physical_capture_time_verified',
        'cross_modal_alignment_performed',
        'full_extrinsics_verified',
        'imu_bias_calibrated',
        'gravity_compensation_performed',
        'imu_preintegration_executed',
        'metric_position_estimated',
        'metric_velocity_estimated',
        'independent_ground_truth_scored',
        'imu_orientation_pose_authorized',
        'orientation_covariance_calibrated',
        'health_model_training_authorized',
        'm2dgr_scoring_authorized',
        'real_sensor_factor_execution_authorized',
        'statistical_stability_established',
        'raw_recording_modified',
        'github_modified'
    ):
        need(
            report.get(field) is False,
            'SCIENCE_FLAG:' + field
        )

    for field in (
        'real_pose_factors_generated',
        'health_labels_generated',
        'new_sensor_acquisitions'
    ):
        need(
            type(report.get(field)) is int
            and report[field] == 0,
            'COUNT:' + field
        )

    expected_frame = {
        '/camera/imu': 'camera_imu_optical_frame',
        '/handsfree/imu': 'base_link'
    }

    need(
        set(report['streams'])
        == set(expected_frame)
        == set(src['streams']),
        'STREAM_SET'
    )

    checked = 0

    for topic, frame in expected_frame.items():
        output = report['streams'][topic]

        need(
            output['recorded_frame_id'] == frame
            and len(output['intervals']) == 8
            and output['physical_frame_extrinsics_verified'] is False
            and output['orientation_pose_measurement_authorized'] is False,
            'FRAME_ID'
        )

        sampled = {
            'observed_header_dt_ms': [],
            'gyro_sample_delta_norm_rad_s': [],
            'specific_force_sample_delta_norm_m_s2': [],
            'observed_gyro_integral_norm_rad': []
        }

        unknown = 0

        for k, source in enumerate(src['streams'][topic]):
            result = output['intervals'][k]

            need(
                result['pair_index'] == source['pair_index'] == k,
                'PAIR_INDEX'
            )

            first, second = source['samples']
            s0, s1 = source['messages']

            dt = (
                s1['header_stamp_ns']
                - s0['header_stamp_ns']
            ) / 1_000_000.0

            need(
                dt > 0
                and s0['frame_id'] == s1['frame_id'] == frame
                and s1['sequence'] == s0['sequence'] + 1,
                'SOURCE_FRAME'
            )

            gyro_diff = math.dist(
                first['gyro_rad_s'],
                second['gyro_rad_s']
            )

            accel_diff = math.dist(
                first['specific_force_m_s2'],
                second['specific_force_m_s2']
            )

            unknown_pair = sum(
                int(x['orientation_covariance_unknown_sentinel'])
                for x in (first, second)
            )

            checks = {
                'observed_header_dt_ms_not_capture_clock_proof': dt,
                'gyro_sample_delta_norm_rad_s': gyro_diff,
                'specific_force_sample_delta_norm_m_s2': accel_diff,
                'gyro_norm_samples_rad_s': [
                    first['gyro_norm_rad_s'],
                    second['gyro_norm_rad_s']
                ],
                'specific_force_norm_samples_m_s2': [
                    first['specific_force_norm_m_s2'],
                    second['specific_force_norm_m_s2']
                ],
                'orientation_norm_samples_as_recorded': [
                    first['orientation_norm_as_recorded'],
                    second['orientation_norm_as_recorded']
                ],
                'orientation_covariance_unknown_count': unknown_pair,
                'gyro_trapezoid_component_norm_rad':
                    source['diagnostic']['gyro_integral_vector_norm_rad'],
                'source_serialized_message_sha256': [
                    s0['serialized_message_sha256'],
                    s1['serialized_message_sha256']
                ],
                'velocity_from_acceleration_m_s': None,
                'relative_rotation_estimate_rad': None,
                'pose_factor': None
            }

            for key, value in checks.items():
                need(
                    eq(result.get(key), value),
                    'INDEPENDENT_INTERVAL:'
                    + topic + ':' + str(k) + ':' + key
                )

            sampled['observed_header_dt_ms'].append(dt)
            sampled['gyro_sample_delta_norm_rad_s'].append(
                gyro_diff
            )
            sampled['specific_force_sample_delta_norm_m_s2'].append(
                accel_diff
            )
            sampled['observed_gyro_integral_norm_rad'].append(
                source['diagnostic']['gyro_integral_vector_norm_rad']
            )

            unknown += unknown_pair
            checked += 1

        summary = output['summary']

        need(
            summary['orientation_covariance_unknown_samples']
            == unknown
            and summary['orientation_samples_inspected'] == 16,
            'ORIENTATION_COUNTS'
        )

        for key, measurements in sampled.items():
            triplet = summary[key]

            for stat, expected in (
                ('min', min(measurements)),
                ('median', median(measurements)),
                ('max', max(measurements))
            ):
                need(
                    eq(triplet[stat], expected),
                    'INDEPENDENT_SUMMARY:'
                    + topic + ':' + key + ':' + stat
                )

    need(checked == 16, 'INTERVAL_COUNT')

    outcome = {
        'schema':
            'TRUST_ROBOT_R35_INDEPENDENT_IMU_VARIATION_FRAME_V1',
        'r35_report_sha256': sha(reportp),
        'r34_source_report_sha256': sha(r34p),
        'r34_independent_validation_sha256': sha(v34p),
        'recorded_source_messages_reused_from_verified_r34': 32,
        'intervals_independently_recomputed': 16,
        'raw_bag_reopened': False,
        'physical_capture_clock_authorized': False,
        'inter_imu_alignment_authorized': False,
        'pose_factors_authorized': False
    }

    with outp.open('x', encoding='utf-8') as f:
        json.dump(
            outcome, f,
            indent=2,
            sort_keys=True,
            allow_nan=False
        )
        f.write('\n')

    print('R35_INDEPENDENT_INTERVAL_AND_FRAME_RECOMPUTATION=16_MATCHED')
    print('R35_INDEPENDENT_ORIENTATION_SENTINELS=32_CHECKED')
    print('R35_INDEPENDENT_VALIDATION=PASS')

if __name__ == '__main__':
    verify(
        *(pathlib.Path(x) for x in sys.argv[1:7])
    )
