"""A46-2: IMU propagation as a third manufactured pose comparison.

No trusted physical reference. All comparisons are descriptive, with no
health threshold, majority vote, source attribution, or runtime factor gate.
An optional common-mode IMU-pose shift is an algebraic proxy intervention,
not a measured IMU failure or changed solver input.
"""
from __future__ import annotations
import json
import math

SCHEMA = 'TRUST_ROBOT_R135_A46_2_TRI_MODAL_CONSISTENCY_LIMITS_V1'
ORIGIN = 'ANALYTIC_FIXTURE'
SEEDS = (13, 31)
EPS = 1e-9  # Equality tolerance for synthetic contrasts ONLY.

class BoundaryError(ValueError):
    pass

def canonical(x):
    return (
        json.dumps(
            x, sort_keys=True, separators=(',', ':'),
            allow_nan=False
        ) + '\n'
    ).encode()

def guard(origin):
    if type(origin) is not str or origin != ORIGIN:
        raise BoundaryError(
            'Real, recorded and unknown origins denied'
        )

    from trust_robot.synthetic_joint_fault_identifiability_v1 import (
        guard as prior_guard
    )
    prior_guard(origin)

def imu_edge_proxy(fixture, origin=ORIGIN):
    guard(origin)

    from trust_robot.analytic_inertial_15d import (
        initial_state, predict_imu, as_pose
    )

    if (
        type(fixture) is not dict
        or set(fixture) != {'scans', 'imu', 'available'}
        or len(fixture['imu']) != 8
        or len(fixture['available']) != 9
    ):
        raise BoundaryError(
            'Unexpected synthetic IMU fixture shape'
        )

    start = initial_state()
    state = start.copy()

    for index in range(2):
        m = fixture['imu'][index]

        if (
            type(m) is not dict
            or m.get('interval_index') != index
            or m.get('measurement_origin') != ORIGIN
            or m.get('physical_clock_verified') is not False
        ):
            raise BoundaryError(
                'Unqualified synthetic IMU sample'
            )

        state = predict_imu(state, m)

    return as_pose(start).inverse().compose(as_pose(state))

def triad(camera, lidar, imu):
    from trust_robot.synthetic_cross_modal_ambiguity_v1 import pose_gap
    from trust_robot.clean_backbone import PoseSE3

    if not all(
        isinstance(x, PoseSE3)
        for x in (camera, lidar, imu)
    ):
        raise BoundaryError(
            'Triad requires three manufactured PoseSE3 objects'
        )

    def describe(a, b):
        d = pose_gap(a, b)
        v = d['relative_translation_difference_m']

        if (
            type(v) is not float
            or not math.isfinite(v)
            or v < 0
        ):
            raise BoundaryError(
                'Invalid manufactured discrepancy'
            )

        return v

    return {
        'camera_vs_lidar_translation_m': describe(lidar, camera),
        'camera_vs_imu_translation_m': describe(imu, camera),
        'lidar_vs_imu_translation_m': describe(imu, lidar),
        'physical_threshold_selected': False,
        'physical_sensor_uncertainty_calibrated': False,
    }

def case(name, seed=13, origin=ORIGIN):
    guard(origin)

    from trust_robot.synthetic_joint_fault_identifiability_v1 import (
        construct, DESIGNS, EDGE
    )

    if (
        type(name) is not str
        or name not in DESIGNS
        or type(seed) is not int
        or seed not in SEEDS
    ):
        raise BoundaryError(
            'Unlisted manufactured intervention'
        )

    fixture, imu_factors, lidar, counts, packets, expected = (
        construct(name, seed, origin)
    )

    camera = {p.edge: p for p in packets}

    if (
        len(camera) != 2
        or EDGE not in camera
        or EDGE not in lidar
        or len(imu_factors) != 4
        or counts['imu_samples_reused'] is not False
    ):
        raise BoundaryError(
            'Factor/measurement ownership changed'
        )

    motion = imu_edge_proxy(fixture, origin)

    measurements = triad(
        camera[EDGE].measurement,
        lidar[EDGE],
        motion
    )

    return {
        'scenario': name,
        'seed': seed,
        'manufactured_relative_pose_edge': list(EDGE),
        'triad': measurements,
        'lidar_factor_count': len(lidar),
        'known_lidar_hold_windows':
            expected['required_shadow_holds'],
        'imu_proxy_derived_from_samples': [0, 1],
        'imu_proxy_is_independent_physical_reference': False,
        'known_scripted_fault_is_detected_source': False,
        'physical_responsible_modality': 'UNRESOLVED',
        'real_factor_admission': 'DENIED',
        'robot_actuation': 'DENIED',
    }

def contrast(before, after):
    if type(before) is not dict or type(after) is not dict:
        raise BoundaryError(
            'Missing paired synthetic diagnostics'
        )

    keys = (
        'camera_vs_lidar_translation_m',
        'camera_vs_imu_translation_m',
        'lidar_vs_imu_translation_m'
    )

    if any(
        type(before.get(k)) is not float
        or type(after.get(k)) is not float
        or not math.isfinite(before[k])
        or not math.isfinite(after[k])
        or before[k] < 0
        or after[k] < 0
        for k in keys
    ):
        raise BoundaryError(
            'Invalid paired synthetic diagnostic'
        )

    return {
        key: round(after[key] - before[key], 12)
        for key in keys
    }

def shifted_imu_proxy(seed):
    """Shared translation leaves all three pairwise gaps unchanged.

    Alters only a derived IMU pose proxy, not IMU samples or solver.
    """
    if type(seed) is not int or seed not in SEEDS:
        raise BoundaryError('Unlisted seed')

    from trust_robot.synthetic_joint_fault_identifiability_v1 import (
        construct, shift_x, DELTA_M, EDGE
    )

    base = construct('baseline', seed)
    common = construct('joint_common_mode', seed)

    bfixture, _, blidar, _, bpackets, _ = base
    cfixture, _, clidar, _, cpackets, _ = common

    bcam = {
        p.edge: p for p in bpackets
    }[EDGE].measurement

    ccam = {
        p.edge: p for p in cpackets
    }[EDGE].measurement

    bimu = imu_edge_proxy(bfixture)
    cimu = imu_edge_proxy(cfixture)

    before = triad(bcam, blidar[EDGE], bimu)
    after = triad(
        ccam, clidar[EDGE],
        shift_x(cimu, DELTA_M)
    )

    delta = contrast(before, after)

    if any(abs(x) > EPS for x in delta.values()):
        raise BoundaryError(
            'Synthetic all-three common-mode invariance failed'
        )

    return {
        'seed': seed,
        'synthetic_three_way_common_shift_m': DELTA_M,
        'translation_pairwise_metrics_unchanged': True,
        'delta_translation_metrics_m': delta,
        'imu_proxy_shift_is_raw_imu_corruption': False,
        'physical_failure_attribution': 'UNRESOLVED',
    }

def execute():
    guard(ORIGIN)

    names = (
        'baseline',
        'camera_only',
        'lidar_only',
        'joint_common_mode',
        'joint_opposing',
        'dropout_and_camera'
    )

    results = [
        case(n, 13)
        for n in names
    ]

    results += [
        case(n, 31)
        for n in ('baseline', 'joint_common_mode')
    ]

    lookup = {
        (r['scenario'], r['seed']): r
        for r in results
    }

    if len(lookup) != 8:
        raise BoundaryError(
            'Not eight unique manufactured conditions'
        )

    paired = []

    for seed in SEEDS:
        baseline = lookup['baseline', seed]['triad']
        common = lookup['joint_common_mode', seed]['triad']
        d = contrast(baseline, common)

        if (
            abs(d['camera_vs_lidar_translation_m']) > EPS
            or d['camera_vs_imu_translation_m'] < 0.08
            or d['lidar_vs_imu_translation_m'] < 0.08
        ):
            raise BoundaryError(
                'Third-synthetic-modality contrast not reproduced'
            )

        paired.append({
            'seed': seed,
            'common_mode_contrast_m': d
        })

    for name, invariant in (
        ('camera_only', 'lidar_vs_imu_translation_m'),
        ('lidar_only', 'camera_vs_imu_translation_m')
    ):
        d = contrast(
            lookup['baseline', 13]['triad'],
            lookup[name, 13]['triad']
        )

        if abs(d[invariant]) > EPS:
            raise BoundaryError(
                'Unperturbed synthetic source diagnostic drifted'
            )

    if (
        lookup['dropout_and_camera', 13][
            'known_lidar_hold_windows'
        ] != [2, 3]
    ):
        raise BoundaryError('Dropout hold lost')

    three = [
        shifted_imu_proxy(s)
        for s in SEEDS
    ]

    return {
        'schema': SCHEMA,
        'eight_manufactured_factor_cases': results,
        'common_camera_lidar_shift_vs_unchanged_imu': paired,
        'all_three_shared_shift_diagnostic_counterexamples':
            three,
        'pairwise_reliability_limits_exposed': True,
        'third_modality_is_not_trusted_physical_reference': True,
        'faulty_source_identified': False,
        'calibrated_health_probabilities_available': False,
        'real_factor_admission': 'DENIED',
        'robot_actuation': 'DENIED',
        'real_sensor_data_accessed': False,
    }
