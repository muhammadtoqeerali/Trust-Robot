"""TRAIN-only variation of R34 verified IMU intervals. No pose."""

import hashlib
import json
import math
import pathlib
import statistics
import sys

TOPICS = ('/camera/imu', '/handsfree/imu')
FRAMES = {
    '/camera/imu': 'camera_imu_optical_frame',
    '/handsfree/imu': 'base_link'
}

BAG = 'ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1'
BASE = 'ebfd02b0ef8ad79b2e6a9810897fcb71efec2e87'

FLAGS = (
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
)

COUNTS = (
    'real_pose_factors_generated',
    'health_labels_generated',
    'new_sensor_acquisitions'
)

def need(ok, reason):
    if not ok:
        raise ValueError('R35_DENIED:' + reason)

def sha(path):
    return hashlib.sha256(
        pathlib.Path(path).read_bytes()
    ).hexdigest()

def load(path):
    return json.loads(pathlib.Path(path).read_text())

def norm(x):
    return math.sqrt(sum(v * v for v in x))

def stats(values):
    return {
        'min': float(min(values)),
        'median': float(statistics.median(values)),
        'max': float(max(values))
    }

def source_check(src, validated, source_sha):
    need(
        src.get('schema') ==
        'TRUST_ROBOT_R34_TRAIN_TWO_IMU_BOUNDED_INTERVALS_V1'
        and src.get('trajectory_id') == 'room_02'
        and src.get('split') == 'train'
        and src.get('authenticated_bag_sha256') == BAG
        and src.get('github_baseline') == BASE,
        'R34_IDENTITY'
    )

    need(
        src.get('stream_count') == 2
        and src.get('pairs_per_stream') == 8
        and src.get('serialized_imu_messages_inspected') == 32
        and set(src.get('streams', {})) == set(TOPICS),
        'R34_COUNTS'
    )

    need(
        validated.get('schema') ==
        'TRUST_ROBOT_R34_INDEPENDENT_TWO_IMU_INTERVALS_V1'
        and validated.get('source_report_sha256') == source_sha
        and validated.get('original_imu_messages_relocated') == 32
        and validated.get('independent_trapezoid_intervals_recomputed') == 16
        and validated.get('independent_chunk_schedule_rebuilt') is True
        and validated.get('physical_capture_time_verified') is False
        and validated.get('imu_preintegration_or_pose_factor_authorized') is False,
        'R34_INDEPENDENT_PROOF'
    )

    for key in (
        'physical_capture_time_verified',
        'imu_bias_calibrated',
        'gravity_compensation_performed',
        'imu_preintegration_executed',
        'metric_velocity_estimated',
        'metric_position_estimated',
        'real_sensor_factor_execution_authorized',
        'health_model_training_authorized'
    ):
        need(src.get(key) is False, 'R34_GATE:' + key)

    for key in COUNTS:
        need(
            type(src.get(key)) is int and src[key] == 0,
            'R34_COUNT:' + key
        )

    for topic in TOPICS:
        pairs = src['streams'][topic]

        need(
            len(pairs) == 8
            and [p['pair_index'] for p in pairs] == list(range(8)),
            'PAIR_SEQUENCE'
        )

        for p in pairs:
            x, y = p['messages']
            a, b = p['samples']
            d = p['diagnostic']
            dt = p['observed_header_gap_ns']

            need(
                x['frame_id'] == y['frame_id'] == FRAMES[topic]
                and y['sequence'] == x['sequence'] + 1
                and y['header_stamp_ns'] > x['header_stamp_ns']
                and dt == y['header_stamp_ns'] - x['header_stamp_ns'] > 0,
                'R34_PAIR_IDENTITY'
            )

            need(
                d['specific_force_is_gravity_compensated'] is False
                and all(
                    d[k] is None for k in (
                        'rotation_estimate',
                        'velocity_estimate',
                        'position_estimate',
                        'preintegration_factor'
                    )
                ),
                'R34_NONFACTOR'
            )

            for sample in (a, b):
                for key in (
                    'gyro_rad_s',
                    'specific_force_m_s2'
                ):
                    values = sample[key]
                    need(
                        len(values) == 3
                        and all(
                            type(v) in (int, float)
                            and math.isfinite(v)
                            for v in values
                        ),
                        'SAMPLE_VECTOR:' + key
                    )

                need(
                    type(
                        sample['orientation_covariance_unknown_sentinel']
                    ) is bool
                    and math.isfinite(
                        sample['orientation_norm_as_recorded']
                    ),
                    'ORIENTATION_VALIDITY'
                )

def analyze(src, validated, source_sha,
            validation_sha, engine_sha, checker_sha):

    source_check(src, validated, source_sha)

    streams = {}

    for topic in TOPICS:
        intervals = []

        for p in src['streams'][topic]:
            a, b = p['samples']
            x, y = p['messages']

            dt = p['observed_header_gap_ns'] * 1e-6

            gyro_delta = norm([
                q - z for q, z in zip(
                    b['gyro_rad_s'], a['gyro_rad_s']
                )
            ])

            force_delta = norm([
                q - z for q, z in zip(
                    b['specific_force_m_s2'],
                    a['specific_force_m_s2']
                )
            ])

            intervals.append({
                'pair_index': p['pair_index'],
                'observed_header_dt_ms_not_capture_clock_proof':
                    float(dt),
                'gyro_sample_delta_norm_rad_s':
                    float(gyro_delta),
                'specific_force_sample_delta_norm_m_s2':
                    float(force_delta),
                'gyro_norm_samples_rad_s': [
                    float(a['gyro_norm_rad_s']),
                    float(b['gyro_norm_rad_s'])
                ],
                'specific_force_norm_samples_m_s2': [
                    float(a['specific_force_norm_m_s2']),
                    float(b['specific_force_norm_m_s2'])
                ],
                'orientation_norm_samples_as_recorded': [
                    float(a['orientation_norm_as_recorded']),
                    float(b['orientation_norm_as_recorded'])
                ],
                'orientation_covariance_unknown_count':
                    int(a['orientation_covariance_unknown_sentinel'])
                    + int(b['orientation_covariance_unknown_sentinel']),
                'gyro_trapezoid_component_norm_rad':
                    float(
                        p['diagnostic']['gyro_integral_vector_norm_rad']
                    ),
                'source_serialized_message_sha256': [
                    x['serialized_message_sha256'],
                    y['serialized_message_sha256']
                ],
                'velocity_from_acceleration_m_s': None,
                'relative_rotation_estimate_rad': None,
                'pose_factor': None
            })

        streams[topic] = {
            'recorded_frame_id': FRAMES[topic],
            'orientation_semantics':
                'recorded_covariance_sentinel_counted_no_orientation_pose_admission',
            'intervals': intervals,
            'summary': {
                'observed_header_dt_ms': stats([
                    i['observed_header_dt_ms_not_capture_clock_proof']
                    for i in intervals
                ]),
                'gyro_sample_delta_norm_rad_s': stats([
                    i['gyro_sample_delta_norm_rad_s']
                    for i in intervals
                ]),
                'specific_force_sample_delta_norm_m_s2': stats([
                    i['specific_force_sample_delta_norm_m_s2']
                    for i in intervals
                ]),
                'observed_gyro_integral_norm_rad': stats([
                    i['gyro_trapezoid_component_norm_rad']
                    for i in intervals
                ]),
                'orientation_covariance_unknown_samples':
                    sum(
                        i['orientation_covariance_unknown_count']
                        for i in intervals
                    ),
                'orientation_samples_inspected': 16
            },
            'physical_frame_extrinsics_verified': False,
            'orientation_pose_measurement_authorized': False
        }

    output = {
        'schema':
            'TRUST_ROBOT_R35_TRAIN_IMU_VARIATION_FRAME_SEMANTICS_V1',
        'trajectory_id': 'room_02',
        'split': 'train',
        'github_baseline': BASE,
        'authenticated_bag_sha256': BAG,
        'r34_source_report_sha256': source_sha,
        'r34_independent_validation_sha256': validation_sha,
        'r34_engine_source_sha256': engine_sha,
        'r34_independent_verifier_source_sha256': checker_sha,
        'stream_count': 2,
        'interval_count': 16,
        'previously_authenticated_messages_represented': 32,
        'streams': streams,
        'interpretation':
            'descriptive_within_stream_sample_variation_only_no_cross_stream_alignment_or_pose',
        'r35_reopened_raw_rosbag': False,
        **{k: False for k in FLAGS},
        **{k: 0 for k in COUNTS}
    }

    safety(output)
    return output

def safety(d):
    need(
        d.get('schema') ==
        'TRUST_ROBOT_R35_TRAIN_IMU_VARIATION_FRAME_SEMANTICS_V1'
        and d.get('trajectory_id') == 'room_02'
        and d.get('split') == 'train'
        and d.get('authenticated_bag_sha256') == BAG
        and d.get('github_baseline') == BASE,
        'REPORT_SCOPE'
    )

    need(
        d.get('stream_count') == 2
        and d.get('interval_count') == 16
        and d.get('previously_authenticated_messages_represented') == 32
        and d.get('r35_reopened_raw_rosbag') is False,
        'COUNT_SCOPE'
    )

    need(
        all(d.get(k) is False for k in FLAGS),
        'SCIENTIFIC_GATE'
    )

    need(
        all(
            type(d.get(k)) is int and d[k] == 0
            for k in COUNTS
        ),
        'SCIENTIFIC_COUNT'
    )

    need(
        set(d.get('streams', {})) == set(TOPICS),
        'STREAMS'
    )

    seen = set()

    for topic in TOPICS:
        row = d['streams'][topic]
        intervals = row['intervals']
        summary = row['summary']

        need(
            row['recorded_frame_id'] == FRAMES[topic]
            and row['physical_frame_extrinsics_verified'] is False
            and row['orientation_pose_measurement_authorized'] is False
            and len(intervals) == 8
            and [x['pair_index'] for x in intervals] == list(range(8)),
            'FRAME_GATE'
        )

        need(
            summary['orientation_samples_inspected'] == 16
            and type(
                summary['orientation_covariance_unknown_samples']
            ) is int
            and 0 <= summary[
                'orientation_covariance_unknown_samples'
            ] <= 16,
            'ORIENTATION_COUNT'
        )

        total = 0

        for p in intervals:
            hashes = p['source_serialized_message_sha256']

            need(
                len(hashes) == 2
                and all(
                    type(h) is str
                    and len(h) == 64
                    and all(
                        c in '0123456789abcdef'
                        for c in h
                    )
                    for h in hashes
                ),
                'SOURCE_SHA'
            )

            for h in hashes:
                need(
                    (topic, h) not in seen,
                    'DUPLICATE_SOURCE'
                )
                seen.add((topic, h))

            for key in (
                'observed_header_dt_ms_not_capture_clock_proof',
                'gyro_sample_delta_norm_rad_s',
                'specific_force_sample_delta_norm_m_s2',
                'gyro_trapezoid_component_norm_rad'
            ):
                value = p[key]

                need(
                    type(value) is float
                    and math.isfinite(value)
                    and (
                        value > 0
                        if key.startswith('observed_header_dt')
                        else value >= 0
                    ),
                    'FINITE_METRIC:' + key
                )

            for key in (
                'gyro_norm_samples_rad_s',
                'specific_force_norm_samples_m_s2',
                'orientation_norm_samples_as_recorded'
            ):
                values = p[key]

                need(
                    len(values) == 2
                    and all(
                        type(v) is float
                        and math.isfinite(v)
                        and v >= 0
                        for v in values
                    ),
                    'SAMPLE_NORMS:' + key
                )

            k = p['orientation_covariance_unknown_count']

            need(
                type(k) is int and 0 <= k <= 2,
                'ORIENTATION_SENTINEL'
            )

            total += k

            need(
                all(
                    p[x] is None for x in (
                        'velocity_from_acceleration_m_s',
                        'relative_rotation_estimate_rad',
                        'pose_factor'
                    )
                ),
                'NO_POSE'
            )

        need(
            total ==
            summary['orientation_covariance_unknown_samples'],
            'SENTINEL_SUMMARY'
        )

        for metric in (
            'observed_header_dt_ms',
            'gyro_sample_delta_norm_rad_s',
            'specific_force_sample_delta_norm_m_s2',
            'observed_gyro_integral_norm_rad'
        ):
            vals = summary[metric]

            need(
                all(
                    type(vals[k]) is float
                    and math.isfinite(vals[k])
                    for k in ('min', 'median', 'max')
                )
                and 0 <= vals['min']
                <= vals['median']
                <= vals['max'],
                'SUMMARY_METRIC:' + metric
            )

    need(len(seen) == 32, 'SOURCE_COUNT')

def run(reportp, validationp, enginep, verifierp, outp):
    src = load(reportp)
    validated = load(validationp)

    output = analyze(
        src, validated,
        sha(reportp), sha(validationp),
        sha(enginep), sha(verifierp)
    )

    with outp.open('x', encoding='utf-8') as f:
        json.dump(
            output, f,
            indent=2,
            sort_keys=True,
            allow_nan=False
        )
        f.write('\n')

    for topic in TOPICS:
        s = output['streams'][topic]['summary']
        times = s['observed_header_dt_ms']

        print(
            'R35_STREAM=%s FRAME=%s '
            'HEADER_DT_MS_MIN_MED_MAX=%.6f,%.6f,%.6f '
            'ORIENTATION_UNKNOWN=%d/16'
            % (
                topic, FRAMES[topic],
                times['min'],
                times['median'],
                times['max'],
                s['orientation_covariance_unknown_samples']
            )
        )

    print('R35_RECORDED_IMU_INTERVAL_VARIATION=16_DERIVED')
    print(
        'R35_EXTERNAL_FRAME_AND_CAPTURE_CLOCK_QUALIFICATION=NOT_ESTABLISHED'
    )

if __name__ == '__main__':
    run(
        *(pathlib.Path(x) for x in sys.argv[1:6])
    )
