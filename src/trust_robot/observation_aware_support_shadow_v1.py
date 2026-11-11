"""Development-only availability-aware shadow over the frozen 15D solver.

Numerical support is not physical observability. Synthetic scan availability
is a known fixture input, NOT a device health or fault-attribution label.
No real measurements, factor weighting, control or health classification.
"""
from __future__ import annotations
import json

SCHEMA = 'TRUST_ROBOT_R135_A44_3_OBSERVATION_AWARE_SHADOW_V1'
CASES = ('clean', 'accel_bias', 'lidar_dropout')

class ShadowDenied(ValueError):
    pass

def canonical(x):
    return (
        json.dumps(
            x, sort_keys=True, separators=(',', ':'), allow_nan=False
        ) + '\n'
    ).encode()

def reject_origin(origin):
    if type(origin) is not str or origin != 'ANALYTIC_FIXTURE':
        raise ShadowDenied(
            'Real, recorded and unknown sources are forbidden'
        )

def frozen_gates():
    from trust_robot.factor_conditioning import (
        assert_factor_scale_execution_authorized,
        FactorConditioningContractError
    )
    from trust_robot.auxiliary_consistency import (
        assert_consistency_execution_authorized,
        AuxiliaryConsistencyContractError
    )

    for action, expected in (
        (
            assert_factor_scale_execution_authorized,
            FactorConditioningContractError
        ),
        (
            assert_consistency_execution_authorized,
            AuxiliaryConsistencyContractError
        ),
    ):
        try:
            action()
        except expected:
            continue
        raise ShadowDenied(
            'Frozen experimental gate unexpectedly opened'
        )

    return {
        'factor_conditioning': 'CLOSED',
        'auxiliary_consistency': 'CLOSED',
        'real_factor_admission': 'DENIED',
        'actuation': 'DENIED'
    }

def assess(mask, node_frames, windows):
    """Require both endpoint scan flags; keep numerical support separate.

    This is a conservative experimental mask, not an operational policy.
    Historical Schur-factor ownership does not prove current scan presence.
    """
    if (
        type(mask) not in (list, tuple)
        or len(mask) != 9
        or any(type(x) is not bool for x in mask)
    ):
        raise ShadowDenied(
            'Expected exactly nine synthetic availability booleans'
        )

    if (
        type(node_frames) not in (list, tuple)
        or tuple(node_frames) != (0, 2, 4, 6, 8)
    ):
        raise ShadowDenied(
            'Unexpected synthetic node frame schedule'
        )

    if type(windows) not in (list, tuple) or len(windows) != 4:
        raise ShadowDenied(
            'Unexpected optimizer window count'
        )

    output = []

    for idx, window in enumerate(windows, 1):
        if (
            type(window) is not dict
            or window.get('end_node') != idx
        ):
            raise ShadowDenied(
                'Window chronology mismatch'
            )

        support = window.get('factor_support')
        if type(support) is not dict:
            raise ShadowDenied(
                'Support diagnostics missing'
            )

        st = support.get('status')
        present = support.get('current_lidar_factor_available')

        if type(st) is not str or type(present) is not bool:
            raise ShadowDenied(
                'Malformed numeric factor metadata'
            )

        count = window.get('active_lidar_factor_count')

        if (
            type(count) is not int
            or count < 0
            or bool(count) != present
        ):
            raise ShadowDenied(
                'Active-factor count/presence mismatch'
            )

        frame_a, frame_b = node_frames[idx-1:idx+1]
        scan_ready = mask[frame_a] and mask[frame_b]
        numeric_ready = st == 'NUMERICALLY_SUPPORTED' and present

        if not scan_ready:
            decision = 'HOLD_MISSING_ENDPOINT_SCAN'
        elif not numeric_ready:
            decision = 'HOLD_NUMERIC_OR_LIDAR_SUPPORT'
        else:
            decision = 'ELIGIBLE_SYNTHETIC_SHADOW_ONLY'

        output.append({
            'end_node': idx,
            'frame_pair': [frame_a, frame_b],
            'endpoint_scans_available': scan_ready,
            'numeric_support_status': st,
            'current_lidar_factor_available': present,
            'shadow_decision': decision,
            'physical_sensor_health_verified': False,
        })

    return {
        'node_frame_scan_mask': [
            mask[k] for k in node_frames
        ],
        'missing_node_frames': [
            k for k in node_frames if not mask[k]
        ],
        'window_decisions': output,
        'global_shadow_decision': (
            'ELIGIBLE_SYNTHETIC_SHADOW_ONLY'
            if all(
                x['shadow_decision']
                == 'ELIGIBLE_SYNTHETIC_SHADOW_ONLY'
                for x in output
            )
            else 'HOLD_SYNTHETIC_SHADOW'
        ),
        'physical_sensor_health_verified': False,
        'real_factor_admission': 'DENIED'
    }

def run_case(condition, origin='ANALYTIC_FIXTURE'):
    reject_origin(origin)

    if condition not in CASES:
        raise ShadowDenied(
            'Unlisted manufactured condition'
        )

    frozen_gates()

    from trust_robot import analytic_marginalized_fusion as s

    fixture, truth = s.make_fixture(condition)

    if any(
        m.get('measurement_origin') != 'ANALYTIC_FIXTURE'
        or m.get('physical_clock_verified') is not False
        for m in fixture['imu']
    ):
        raise ShadowDenied(
            'Unexpected fixture origin'
        )

    if (
        (condition == 'lidar_dropout')
        != (fixture['available'][4] is False)
    ):
        raise ShadowDenied(
            'Frozen named dropout condition mismatch'
        )

    if (
        condition != 'lidar_dropout'
        and not all(fixture['available'])
    ):
        raise ShadowDenied(
            'Unlisted missing scan in synthetic fixture'
        )

    legacy, la = s.estimate_marginalized(fixture)
    reported, ra = s.estimate_marginalized_with_support(
        fixture, support_policy='report'
    )

    for records, audit in ((legacy, la), (reported, ra)):
        if not (
            len(records) == 5
            and audit.get('accepted_window_count') == 4
            and audit.get('schur_elimination_count') == 3
            and audit.get('unaccounted_factor_count') == 0
            and audit.get('factor_reuse_after_marginalization') is False
        ):
            raise ShadowDenied(
                'Frozen estimator accounting changed'
            )

    if canonical(legacy) != canonical(reported):
        raise ShadowDenied(
            'Numeric reporting modified frozen trajectory'
        )

    shadow = assess(
        fixture['available'], s.NODE_FRAMES, ra['windows']
    )

    if (
        condition == 'lidar_dropout'
        and shadow['global_shadow_decision']
        != 'HOLD_SYNTHETIC_SHADOW'
    ):
        raise ShadowDenied(
            'Known synthetic missing scan escaped shadow hold'
        )

    return {
        'condition': condition,
        'shadow': shadow,
        'synthetic_fixture_metrics': s.score(
            reported, [truth[k] for k in s.NODE_FRAMES]
        ),
        'frozen_estimator_unchanged': True,
        'real_sensor_data_used': False,
        'real_sensor_health_inferred': False,
        'factor_weighting_executed': False,
        'source_blame_assigned': False,
        'real_factor_admission': 'DENIED',
        'robot_actuation': 'DENIED'
    }

def execute():
    return {
        'schema': SCHEMA,
        'scenario_results': {
            c: run_case(c) for c in CASES
        },
        'scope': 'OFFLINE_MANUFACTURED_FIXTURES_ONLY',
        'physical_clock_and_extrinsics_qualified': False,
        'independent_health_label_count': 0,
        'real_factor_admission': 'DENIED',
        'robot_actuation': 'DENIED',
    }
