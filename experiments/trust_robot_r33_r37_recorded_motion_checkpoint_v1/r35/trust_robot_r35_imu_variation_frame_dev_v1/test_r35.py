"""Manufactured IMU fixture and science-gate controls."""

import copy
import json
import pathlib
import tempfile

import r35_analysis as m
import r35_independent_verify as v

def sample(i, topic):
    gyro = [0.01 + i * 0.001, 0.02, 0.03]
    accel = [0.1, 9.7 + i * 0.02, -0.2]

    return {
        'gyro_rad_s': gyro,
        'specific_force_m_s2': accel,
        'gyro_norm_rad_s': m.norm(gyro),
        'specific_force_norm_m_s2': m.norm(accel),
        'orientation_norm_as_recorded':
            0.0 if topic == m.TOPICS[0] else 1.0,
        'orientation_covariance_unknown_sentinel':
            topic == m.TOPICS[0]
    }

def fixture():
    r = {
        'schema':
            'TRUST_ROBOT_R34_TRAIN_TWO_IMU_BOUNDED_INTERVALS_V1',
        'trajectory_id': 'room_02',
        'split': 'train',
        'authenticated_bag_sha256': m.BAG,
        'github_baseline': m.BASE,
        'stream_count': 2,
        'pairs_per_stream': 8,
        'serialized_imu_messages_inspected': 32,
        'streams': {},
        **{
            k: False for k in (
                'physical_capture_time_verified',
                'imu_bias_calibrated',
                'gravity_compensation_performed',
                'imu_preintegration_executed',
                'metric_velocity_estimated',
                'metric_position_estimated',
                'real_sensor_factor_execution_authorized',
                'health_model_training_authorized'
            )
        },
        **{k: 0 for k in m.COUNTS}
    }

    for j, topic in enumerate(m.TOPICS):
        records = []

        for i in range(8):
            a = sample(i, topic)
            b = sample(i + 1, topic)
            start = 10_000_000 * i
            gap = 5_000_000 + i * 200_000 + j * 30_000

            messages = [
                {
                    'sequence': i * 2 + t,
                    'header_stamp_ns':
                        start if t == 0 else start + gap,
                    'frame_id': m.FRAMES[topic],
                    'serialized_message_sha256':
                        '%064x' % (1 + i * 2 + t + j * 100)
                }
                for t in range(2)
            ]

            records.append({
                'pair_index': i,
                'messages': messages,
                'samples': [a, b],
                'observed_header_gap_ns': gap,
                'diagnostic': {
                    'gyro_integral_vector_norm_rad':
                        0.0001 + i * 0.00001,
                    'specific_force_is_gravity_compensated': False,
                    'rotation_estimate': None,
                    'velocity_estimate': None,
                    'position_estimate': None,
                    'preintegration_factor': None
                }
            })

        r['streams'][topic] = records

    return r

with tempfile.TemporaryDirectory() as folder:
    d = pathlib.Path(folder)

    r34 = d / 'r34.json'
    v34 = d / 'v34.json'
    engine = d / 'engine.py'
    checker = d / 'checker.py'

    r34.write_text(json.dumps(fixture(), sort_keys=True))
    engine.write_text('pass\n')
    checker.write_text('pass\n')

    verified = {
        'schema':
            'TRUST_ROBOT_R34_INDEPENDENT_TWO_IMU_INTERVALS_V1',
        'source_report_sha256': m.sha(r34),
        'original_imu_messages_relocated': 32,
        'independent_trapezoid_intervals_recomputed': 16,
        'independent_chunk_schedule_rebuilt': True,
        'physical_capture_time_verified': False,
        'imu_preintegration_or_pose_factor_authorized': False
    }

    v34.write_text(json.dumps(verified))

    result = m.analyze(
        m.load(r34),
        m.load(v34),
        m.sha(r34),
        m.sha(v34),
        m.sha(engine),
        m.sha(checker)
    )

    report = d / 'report.json'
    report.write_text(json.dumps(result))

    v.verify(
        r34, v34, engine, checker,
        report, d / 'independent.json'
    )

    rejected = 0

    for key in (*m.FLAGS, *m.COUNTS):
        invalid = copy.deepcopy(result)
        invalid[key] = True if key in m.FLAGS else 1

        try:
            m.safety(invalid)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError('FAILED_SCIENCE_GATE:' + key)

    for kind in (
        'wrong_split',
        'fake_pose',
        'repeated_source',
        'changed_sentinel_summary',
        'bad_frame'
    ):
        bad = copy.deepcopy(result)

        if kind == 'wrong_split':
            bad['split'] = 'confirmation_test'

        elif kind == 'fake_pose':
            bad['streams'][m.TOPICS[0]][
                'intervals'
            ][0]['pose_factor'] = [1, 2, 3]

        elif kind == 'repeated_source':
            bad['streams'][m.TOPICS[0]]['intervals'][1][
                'source_serialized_message_sha256'
            ][0] = bad['streams'][m.TOPICS[0]]['intervals'][0][
                'source_serialized_message_sha256'
            ][0]

        elif kind == 'changed_sentinel_summary':
            bad['streams'][m.TOPICS[0]]['summary'][
                'orientation_covariance_unknown_samples'
            ] = 0

        else:
            bad['streams'][m.TOPICS[0]][
                'recorded_frame_id'
            ] = 'base_link'

        try:
            m.safety(bad)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError('FAILED_MUTATION:' + kind)

    assert rejected == 25

print('R35_MANUFACTURED_TWO_IMU_FRAME_AND_VARIATION=PASS')
print('R35_NEGATIVE_SCIENCE_AND_SOURCE_CONTROLS=25_REJECTED')
