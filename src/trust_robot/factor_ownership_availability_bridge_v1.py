"""Purely synthetic factor-ownership and scan-availability cross-check.

Uses original frozen 15D LiDAR frontend and observation-aware shadow. Does not
train health, weight factors, infer fault source or enable physical operations.
"""
from __future__ import annotations
from itertools import combinations
import json

SCHEMA = 'TRUST_ROBOT_R135_A44_5_SYNTHETIC_FACTOR_OWNERSHIP_V1'
FRAMES = (0, 2, 4, 6, 8)

class BridgeViolation(ValueError):
    pass

def canonical(data):
    return (
        json.dumps(data, sort_keys=True, separators=(',', ':'), allow_nan=False)
        + '\n'
    ).encode()

def guard(origin):
    if type(origin) is not str or origin != 'ANALYTIC_FIXTURE':
        raise BridgeViolation('Physical/recorded/unspecified input not allowed')
    from trust_robot.observation_aware_support_shadow_v1 import frozen_gates
    frozen_gates()

def validate_mask(mask):
    if (
        type(mask) not in (tuple, list)
        or len(mask) != 9
        or any(type(x) is not bool for x in mask)
    ):
        raise BridgeViolation('Nine synthetic boolean scan flags required')
    return tuple(mask)

def model(mask):
    mask = validate_mask(mask)
    edges = [
        (i, j)
        for j in range(1, 5)
        for i in range(max(0, j-2), j)
        if mask[FRAMES[i]] and mask[FRAMES[j]]
    ]
    holds = [
        j for j in range(1, 5)
        if not (mask[FRAMES[j-1]] and mask[FRAMES[j]])
    ]
    return {
        'lidar_edge_keys': [list(k) for k in edges],
        'lidar_factor_count': len(edges),
        'missing_node_frames': [k for k in FRAMES if not mask[k]],
        'required_shadow_holds': holds
    }

def mutate_fixture(missing):
    if (
        type(missing) is not tuple
        or len(set(missing)) != len(missing)
        or any(type(k) is not int or k not in FRAMES for k in missing)
    ):
        raise BridgeViolation('Only known synthetic node-frame dropouts permitted')

    from trust_robot.analytic_marginalized_fusion import make_fixture
    fixture, _ = make_fixture('clean')

    validate_mask(fixture['available'])
    if not all(fixture['available']):
        raise BridgeViolation('Clean fixture baseline changed')

    for frame in missing:
        fixture['available'][frame] = False

    return fixture

def verify_frontend(fixture):
    from trust_robot.analytic_preintegrated_fusion import (
        make_factors, NODE_FRAMES
    )

    if tuple(NODE_FRAMES) != FRAMES:
        raise BridgeViolation('Frozen estimator chronology changed')

    mask = validate_mask(fixture['available'])
    expected = model(mask)
    imu, lidar, counts = make_factors(fixture)

    if (
        set(imu) != {(0,1), (1,2), (2,3), (3,4)}
        or counts.get('imu_intervals') != 4
        or counts.get('unique_imu_sample_count') != 8
        or counts.get('imu_samples_reused') is not False
        or sorted(lidar) != [
            tuple(k) for k in expected['lidar_edge_keys']
        ]
        or counts.get('lidar_factor_count') != len(lidar)
    ):
        raise BridgeViolation(
            'Actual LiDAR/IMU factor ownership differs from synthetic model'
        )

    return expected

def run_case(missing, origin='ANALYTIC_FIXTURE'):
    guard(origin)
    fixture = mutate_fixture(missing)
    expected = verify_frontend(fixture)

    from trust_robot import analytic_marginalized_fusion as solver
    from trust_robot.observation_aware_support_shadow_v1 import assess

    try:
        states, audit = solver.estimate_marginalized_with_support(
            fixture, support_policy='report'
        )
    except ValueError as exc:
        if not str(exc).startswith('Marginalized window solve failed at '):
            raise
        return {
            'missing_frames': list(missing),
            'expected': expected,
            'estimator': 'NUMERICALLY_REJECTED_SYNTHETIC',
            'optimizer_exception_type': type(exc).__name__,
            'shadow': 'HOLD_SYNTHETIC_SHADOW',
            'actual_hold_windows': [],
            'estimator_state_count': 0,
            'real_factor_admission': 'DENIED'
        }

    if not (
        len(states) == 5
        and audit.get('accepted_window_count') == 4
        and audit.get('schur_elimination_count') == 3
        and audit.get('unaccounted_factor_count') == 0
        and audit.get('factor_reuse_after_marginalization') is False
    ):
        raise BridgeViolation('Marginalized factor accounting changed')

    decision = assess(
        fixture['available'], FRAMES, audit['windows']
    )
    actual_holds = [
        item['end_node']
        for item in decision['window_decisions']
        if item['shadow_decision'].startswith('HOLD')
    ]

    if not set(expected['required_shadow_holds']).issubset(actual_holds):
        raise BridgeViolation('Known missing scan escaped the shadow hold')

    if not missing and actual_holds:
        raise BridgeViolation('Clean fixture unexpectedly shadow-held')

    return {
        'missing_frames': list(missing),
        'expected': expected,
        'estimator': 'SOLVED_SYNTHETIC',
        'optimizer_exception_type': None,
        'shadow': decision['global_shadow_decision'],
        'actual_hold_windows': actual_holds,
        'estimator_state_count': len(states),
        'real_factor_admission': 'DENIED'
    }

def all_patterns():
    records = []
    for n in range(6):
        for missing in combinations(FRAMES, n):
            mask = [True] * 9
            for frame in missing:
                mask[frame] = False
            records.append({
                'missing_frames': list(missing),
                **model(mask)
            })

    if (
        len(records) != 32
        or len({
            tuple(x['missing_frames']) for x in records
        }) != 32
    ):
        raise BridgeViolation('Exhaustive manufactured mask matrix incomplete')

    return records

def execute():
    guard('ANALYTIC_FIXTURE')
    patterns = all_patterns()
    selected = (
        (), (4,), (0,), (8,), (2,6), (0,2,4,6,8)
    )
    solved = [run_case(m) for m in selected]

    from trust_robot.observation_aware_support_shadow_v1 import (
        run_case as frozen_case
    )
    reference = frozen_case('lidar_dropout')

    if (
        reference['shadow']['missing_node_frames'] != [4]
        or [
            x['end_node']
            for x in reference['shadow']['window_decisions']
            if x['shadow_decision'].startswith('HOLD')
        ] != [2, 3]
    ):
        raise BridgeViolation('Published A44-4 dropout reference changed')

    for x in solved:
        if (
            x['missing_frames'] == [4]
            and x['estimator'] == 'SOLVED_SYNTHETIC'
            and x['actual_hold_windows'] != [2, 3]
        ):
            raise BridgeViolation('Single-dropout hold chronology changed')

    return {
        'schema': SCHEMA,
        'pattern_count': len(patterns),
        'exhaustive_pure_mask_patterns': patterns,
        'frozen_frontend_solver_cases': solved,
        'published_a44_4_dropout_reference': 'FRAME_4_HOLD_WINDOWS_2_3',
        'actual_source_attribution': 'NOT_INFERRED',
        'real_health_labels_created': False,
        'physical_clock_calibrated': False,
        'real_factors_executed': False,
        'real_factor_admission': 'DENIED',
        'robot_actuation': 'DENIED'
    }
