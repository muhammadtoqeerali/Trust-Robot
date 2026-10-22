"""R84 synthetic-only inertial timestamp gap segmentation and preintegration.

Reuses the existing analytic bias-aware covariance preintegrator.

It never converts released IMU feature magnitudes into signed axes,
never infers an acquisition clock, and never constructs or adopts
executable real-data factors.
"""

from __future__ import annotations

import hashlib
import json
import math

from pathlib import Path

import numpy as np

from trust_robot.analytic_imu_preintegration import (
    preintegrate,
    bias_correct,
)

SCHEMA = 'TRUST_ROBOT_R84_SYNTHETIC_GAP_AWARE_INERTIAL_FRONTEND_V1'

ORIGIN = 'ANALYTIC_FIXTURE'
SOURCE = 'SYNTHETIC_R84_IMU_AXES'

MAX_GAP_NS = 120_000_000
MAX_WINDOW_STEPS = 4

FIELDS = frozenset((
    'timestamp_ns',
    'gyro_rad_s',
    'specific_force_m_s2',
    'source_id',
    'measurement_origin',
    'physical_clock_verified',
    'reference_data_used',
    'confirmation_test_accessed',
    'split_role',
))

BG = (0.002, -0.001, 0.0015)
BA = (0.02, -0.01, 0.015)


class InertialAdmissionError(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise InertialAdmissionError(reason)


def vec3(value, name):
    need(
        type(value) is list and len(value) == 3,
        'VECTOR_SHAPE:' + name
    )

    need(
        all(
            type(x) in (int, float)
            and math.isfinite(x)
            for x in value
        ),
        'VECTOR_FINITE:' + name
    )

    return tuple(float(x) for x in value)


def check(sample):
    need(
        type(sample) is dict and set(sample) == FIELDS,
        'PACKET_FIELDS'
    )

    need(
        sample['source_id'] == SOURCE
        and sample['measurement_origin'] == ORIGIN,
        'ANALYTIC_ONLY'
    )

    need(
        sample['split_role'] == 'synthetic',
        'SYNTHETIC_ONLY'
    )

    for key in (
        'physical_clock_verified',
        'reference_data_used',
        'confirmation_test_accessed'
    ):
        need(
            sample[key] is False,
            'SCIENCE:' + key
        )

    stamp = sample['timestamp_ns']

    need(
        type(stamp) is int and stamp >= 0,
        'TIMESTAMP_INTEGER'
    )

    gyro = vec3(sample['gyro_rad_s'], 'gyro')
    accel = vec3(sample['specific_force_m_s2'], 'accel')

    return stamp, gyro, accel


def partition(
    packets,
    max_gap_ns=MAX_GAP_NS,
    max_steps=MAX_WINDOW_STEPS
):
    need(
        type(packets) in (tuple, list)
        and len(packets) >= 2,
        'PACKET_COUNT'
    )

    need(
        type(max_gap_ns) is int
        and 0 < max_gap_ns <= 200_000_000,
        'MAX_GAP'
    )

    need(
        type(max_steps) is int
        and 1 <= max_steps <= 32,
        'MAX_WINDOW'
    )

    values = [check(x) for x in packets]

    windows = []
    gap_count = 0
    readings = []
    start = None
    previous = values[0]

    for current in values[1:]:
        dt = current[0] - previous[0]

        need(
            dt > 0,
            'OUT_OF_ORDER_OR_DUPLICATE_TIMESTAMP'
        )

        if dt > max_gap_ns:
            if readings:
                windows.append((
                    start,
                    previous[0],
                    tuple(readings)
                ))

                readings = []

            start = None
            gap_count += 1
            previous = current
            continue

        if not readings:
            start = previous[0]

        readings.append({
            'dt_s': dt / 1e9,
            'gyro_rad_s': list(previous[1]),
            'specific_force_m_s2': list(previous[2]),
            'measurement_origin': ORIGIN,
            'physical_clock_verified': False,
        })

        if len(readings) == max_steps:
            windows.append((
                start,
                current[0],
                tuple(readings)
            ))

            readings = []
            start = None

        previous = current

    if readings:
        windows.append((
            start,
            previous[0],
            tuple(readings)
        ))

    need(
        bool(windows),
        'NO_SAFE_INERTIAL_INTERVALS'
    )

    need(
        all(
            a < b and len(r) > 0
            for a, b, r in windows
        ),
        'EMPTY_OR_REVERSED_WINDOW'
    )

    return windows, gap_count


def integrate_window(a, b, readings, index):
    pre = preintegrate(list(readings))

    P = pre['covariance']
    J = pre['jacobian_bias']

    need(
        P.shape == (15, 15)
        and J.shape == (9, 6),
        'PROPAGATION_SHAPE'
    )

    need(
        bool(np.isfinite(P).all())
        and bool(np.isfinite(J).all()),
        'PROPAGATION_NONFINITE'
    )

    sym_err = float(
        np.max(np.abs(P - P.T))
    )

    min_eig = float(
        np.linalg.eigvalsh(P).min()
    )

    covtrace = float(
        np.trace(P)
    )

    need(
        sym_err <= 1e-10
        and min_eig >= -1e-12
        and covtrace > 0,
        'COVARIANCE_PSD'
    )

    need(
        abs(pre['total_dt'] - (b-a)/1e9) < 1e-10,
        'PREINTEGRATION_DURATION'
    )

    corrected = bias_correct(pre, BG, BA)
    exact = preintegrate(list(readings), BG, BA)

    discrepancies = (
        float(np.linalg.norm(
            corrected['delta_p'] - exact['delta_p']
        )),
        float(np.linalg.norm(
            corrected['delta_v'] - exact['delta_v']
        )),
        float(
            (
                corrected['delta_R'].inv()
                * exact['delta_R']
            ).magnitude()
        ),
    )

    need(
        max(discrepancies) < 1e-3,
        'BIAS_LINEARIZATION_DIVERGENCE'
    )

    return {
        'window_index': index,
        'synthetic_start_ns': a,
        'synthetic_end_ns': b,
        'samples_integrated': len(readings),
        'integration_duration_s': pre['total_dt'],

        'delta_position_m':
            pre['delta_p'].tolist(),

        'delta_velocity_m_s':
            pre['delta_v'].tolist(),

        'delta_rotation_quaternion_xyzw':
            pre['delta_R'].as_quat().tolist(),

        'covariance_15d_trace':
            covtrace,

        'covariance_15d_min_eigenvalue':
            min_eig,

        'covariance_symmetry_max_error':
            sym_err,

        'jacobian_bias_frobenius_norm':
            float(np.linalg.norm(J)),

        'bias_first_order_vs_exact_errors':
            list(discrepancies),

        'synthetic_only': True,
        'real_pose_factor_executable': False,
    }


def analyze(packets):
    groups, gaps = partition(packets)

    rows = [
        integrate_window(a, b, rr, i)
        for i, (a, b, rr) in enumerate(groups)
    ]

    return {
        'source_provenance': ORIGIN,

        'stream_scope':
            'ONE_SYNTHETIC_IMU_NOT_CROSS_MODAL',

        'input_packet_count': len(packets),
        'safe_window_count': len(rows),
        'gap_count': gaps,

        'integrated_pair_count':
            sum(x['samples_integrated'] for x in rows),

        'windows': rows,

        'gaps_bridged_or_interpolated': False,
        'physical_clock_verified': False,
        'real_sensor_factor_execution_authorized': False,
    }


def fixture(case):
    need(
        case in (
            'continuous',
            'single_gap',
            'accel_injection',
            'gyro_injection'
        ),
        'CASE'
    )

    out = []

    for i in range(9):
        t = 1_000_000_000 + 50_000_000*i

        if case == 'single_gap' and i >= 5:
            t += 700_000_000

        gyro = [0.018, -0.011, 0.024]
        accel = [0.1, 0.2, 9.81]

        if case == 'gyro_injection' and i >= 3:
            gyro = [0.028, -0.009, 0.02]

        if case == 'accel_injection' and i >= 3:
            accel = [0.15, 0.24, 9.77]

        out.append({
            'timestamp_ns': t,
            'gyro_rad_s': gyro,
            'specific_force_m_s2': accel,
            'source_id': SOURCE,
            'measurement_origin': ORIGIN,
            'physical_clock_verified': False,
            'reference_data_used': False,
            'confirmation_test_accessed': False,
            'split_role': 'synthetic',
        })

    return out


def execute(r81sha, r82sha):
    cases = {
        name: analyze(fixture(name))
        for name in (
            'continuous',
            'single_gap',
            'accel_injection',
            'gyro_injection'
        )
    }

    need(
        cases['continuous']['safe_window_count'] == 2,
        'CLEAN_WINDOWS'
    )

    need(
        cases['single_gap']['safe_window_count'] == 2,
        'GAP_WINDOWS'
    )

    need(
        cases['single_gap']['gap_count'] == 1,
        'GAP_DETECTED'
    )

    need(
        cases['continuous']['integrated_pair_count'] == 8,
        'CLEAN_STEPS'
    )

    need(
        cases['single_gap']['integrated_pair_count'] == 7,
        'GAP_STEPS'
    )

    need(
        cases['single_gap']['windows'][0]['synthetic_end_ns']
        < cases['single_gap']['windows'][1]['synthetic_start_ns'],
        'GAP_NOT_BRIDGED'
    )

    return {
        'schema': SCHEMA,
        'status': 'PASS_SOFTWARE_ONLY',

        'parent_R83_r81_result_sha256':
            r81sha,

        'parent_R83_r82_result_sha256':
            r82sha,

        'algorithm':
            'SYNTHETIC_IRREGULAR_TIMESTAMP_SEGMENTER_PLUS_EXISTING_ANALYTIC_PREINTEGRATOR',

        'max_safe_sample_interval_ns':
            MAX_GAP_NS,

        'max_consecutive_steps_per_window':
            MAX_WINDOW_STEPS,

        'scenarios': cases,
        'synthetic_cases_executed': 4,

        'original_imu_axes_in_se3_feature_vectors_available': False,

        'recorded_imu_preintegration_performed': False,
        'raw_rosbags_or_gt_opened': False,
        'confirmation_test_accessed': False,
        'cross_sensor_synchronization_verified': False,
        'real_pose_factors_authorized': False,
        'health_training_authorized': False,
        'ate_rpe_authorized': False,
        'scientific_gates_closed': 11,
    }


def canonical(obj):
    return (
        json.dumps(
            obj,
            indent=2,
            sort_keys=True,
            allow_nan=False
        ) + '\n'
    ).encode('utf-8')


if __name__ == '__main__':
    import sys

    root, out = map(Path, sys.argv[1:])

    base = (
        root /
        'experiments/trust_robot_r80_r82_recorded_multimodal_checkpoint_v1/evidence'
    )

    r81 = (
        base /
        'r81/result/r81_full_train_increment_adapter_v1.json'
    )

    r82 = (
        base /
        'r82/result/r82_temporal_window_manifest_v1.json'
    )

    report = execute(
        hashlib.sha256(r81.read_bytes()).hexdigest(),
        hashlib.sha256(r82.read_bytes()).hexdigest()
    )

    path = out / 'r84_synthetic_inertial_gap_frontend_v1.json'

    with path.open('xb') as f:
        f.write(canonical(report))

    print('R84_SYNTHETIC_GAP_AWARE_INERTIAL_FRONTEND=PASS')
