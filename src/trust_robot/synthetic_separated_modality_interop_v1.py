"""A45-2: offline comparison of legacy replacement and existing separate factors.

Uses published synthetic 15D solvers. Separate fixed numerical residual scales
are engineering assumptions, NOT calibrated uncertainties or health weights.
No source blame, physical measurements or robot control.
"""
from __future__ import annotations
import hashlib
import json
import math

SCHEMA = 'TRUST_ROBOT_R135_A45_2_SEPARATED_MODALITY_INTEROP_V1'
ORIGIN = 'ANALYTIC_FIXTURE'
CASES = (
    ('clean', 13, False),
    ('clean', 13, True),
    ('lidar_dropout', 13, False),
    ('lidar_dropout', 13, True),
    ('clean', 31, True),
    ('lidar_dropout', 31, True),
)

class BoundaryError(ValueError):
    pass

def canonical(value):
    return (json.dumps(
        value, sort_keys=True, separators=(',', ':'), allow_nan=False
    ) + '\n').encode()

def guard(origin):
    if type(origin) is not str or origin != ORIGIN:
        raise BoundaryError('Recorded/physical/unknown factors forbidden')

    from trust_robot.observation_aware_support_shadow_v1 import frozen_gates
    from trust_robot.auxiliary_consistency import (
        assert_source_attribution_authorized,
        AuxiliaryConsistencyContractError,
    )

    frozen_gates()

    try:
        assert_source_attribution_authorized()
    except AuxiliaryConsistencyContractError:
        return

    raise BoundaryError(
        'Physical source attribution gate unexpectedly opened'
    )

def check_id_partition(consumed, remaining, expected):
    if any(type(x) is not str or not x for x in consumed+remaining):
        raise BoundaryError('Unqualified measurement identity')

    if (
        len(set(consumed)) != len(consumed)
        or len(set(remaining)) != len(remaining)
        or set(consumed) & set(remaining)
        or set(consumed) | set(remaining) != set(expected)
        or len(consumed)+len(remaining) != len(expected)
    ):
        raise BoundaryError('Lost, reused or duplicated camera measurement')

def mirrored_ambiguity():
    """Identical pairwise gap, opposite assumed source error assignments."""
    from trust_robot.clean_backbone import PoseSE3

    nominal = PoseSE3.identity()
    shifted = PoseSE3(
        (0.125, 0.0, 0.0),
        (1.0, 0.0, 0.0, 0.0)
    )

    def distance(first, second):
        v = first.inverse().compose(second).translation_m
        return round(math.sqrt(sum(float(x)**2 for x in v)), 12)

    gap1 = distance(nominal, shifted)
    gap2 = distance(shifted, nominal)

    if gap1 != gap2 or gap1 <= 0:
        raise BoundaryError('Pairwise symmetric counterexample changed')

    return {
        'manufactured_translation_gap_m': gap1,
        'swapped_source_gap_m': gap2,
        'same_pairwise_discrepancy': True,
        'hypothetical_causes': [
            'CAMERA_DEVIATES_LIDAR_ASSUMED_NOMINAL',
            'LIDAR_DEVIATES_CAMERA_ASSUMED_NOMINAL',
        ],
        'physical_responsible_modality': 'UNRESOLVED',
        'causal_probability_calibrated': False,
        'physical_noise_scales_estimated': False,
    }

def run_case(condition, seed, camera_enabled, origin=ORIGIN):
    guard(origin)

    if (
        type(condition) is not str
        or condition not in ('clean', 'lidar_dropout')
        or type(seed) is not int
        or seed not in (13, 31)
        or type(camera_enabled) is not bool
    ):
        raise BoundaryError(
            'Only six listed manufactured controls are authorized'
        )

    from trust_robot.analytic_inertial_15d import make_fixture
    from trust_robot.analytic_preintegrated_fusion import (
        make_factors, NODE_FRAMES
    )
    from trust_robot.analytic_three_modality_bridge import (
        manufactured_camera_packets,
        execute_case as legacy_case,
    )
    from trust_robot.analytic_separated_modalities import (
        estimate_separated,
        camera_factor_map,
        CAMERA_POSITION_SCALE_M,
        CAMERA_ROTATION_SCALE_RAD,
    )
    from trust_robot.factor_ownership_availability_bridge_v1 import model

    if tuple(NODE_FRAMES) != (0, 2, 4, 6, 8):
        raise BoundaryError('Frozen 15D frame schedule changed')

    if (
        not math.isfinite(CAMERA_POSITION_SCALE_M)
        or not math.isfinite(CAMERA_ROTATION_SCALE_RAD)
        or CAMERA_POSITION_SCALE_M <= 0
        or CAMERA_ROTATION_SCALE_RAD <= 0
    ):
        raise BoundaryError(
            'Invalid fixed synthetic residual scales'
        )

    fixture, manufactured_truth = make_fixture(condition)

    if (
        len(fixture['imu']) != 8
        or any(
            m.get('measurement_origin') != ORIGIN
            or m.get('physical_clock_verified') is not False
            for m in fixture['imu']
        )
    ):
        raise BoundaryError('Fixture provenance changed')

    if condition == 'lidar_dropout':
        if fixture['available'][4] is not False:
            raise BoundaryError(
                'Synthetic dropout fixture changed'
            )
    elif not all(fixture['available']):
        raise BoundaryError(
            'Clean fixture availability changed'
        )

    inertial, lidar, counts = make_factors(fixture)
    expected = model(fixture['available'])

    if (
        set(inertial) != {
            (0, 1), (1, 2), (2, 3), (3, 4)
        }
        or sorted(lidar) != [
            tuple(x) for x in expected['lidar_edge_keys']
        ]
        or counts['lidar_factor_count'] != len(lidar)
    ):
        raise BoundaryError(
            'Frozen factor ownership changed'
        )

    packets = (
        manufactured_camera_packets(
            manufactured_truth,
            seed=seed
        )
        if camera_enabled else ()
    )

    camera = camera_factor_map(packets)
    ids = [
        packet.measurement_id
        for packet in camera.values()
    ]

    if (
        len(camera) != (2 if camera_enabled else 0)
        or len(set(ids)) != len(ids)
    ):
        raise BoundaryError(
            'Synthetic camera factor identity changed'
        )

    overlap = len(set(lidar) & set(camera))
    expected_overlap = (
        (2 if condition == 'clean' else 1)
        if camera_enabled else 0
    )

    if overlap != expected_overlap:
        raise BoundaryError(
            'Camera/LiDAR graph overlap changed'
        )

    estimated, audit = estimate_separated(
        fixture, packets
    )

    if (
        len(estimated) != 5
        or audit['camera_factor_count'] != len(camera)
        or audit['lidar_factor_count'] != len(lidar)
        or audit['imu_factor_count'] != 4
        or audit['accepted_window_count'] != 4
        or audit['schur_elimination_count'] != 3
        or audit['unaccounted_factor_count'] != 0
        or audit['factor_reuse_after_marginalization'] is not False
        or audit['same_edge_camera_and_lidar_supported'] is not True
        or audit['independent_source_residual_blocks'] is not True
        or audit['real_sensor_factor_execution_authorized'] is not False
        or audit['physical_observability_verified'] is not False
        or audit['empirical_covariance_calibrated'] is not False
        or audit['health_factor_conditioning_executed'] is not False
    ):
        raise BoundaryError(
            'Separated estimator scientific/accounting contract changed'
        )

    check_id_partition(
        audit['consumed_camera_ids'],
        audit['remaining_camera_ids'],
        ids
    )

    actual_lidar = [
        tuple(x) for x in (
            audit['consumed_lidar_keys']
            + audit['remaining_lidar_keys']
        )
    ]
    actual_imu = [
        tuple(x) for x in (
            audit['consumed_imu_keys']
            + audit['remaining_imu_keys']
        )
    ]

    if (
        len(actual_lidar) != len(set(actual_lidar))
        or set(actual_lidar) != set(lidar)
        or len(actual_imu) != len(set(actual_imu))
        or set(actual_imu) != set(inertial)
    ):
        raise BoundaryError(
            'Lost/reused LiDAR or IMU factors'
        )

    for win in audit['windows']:
        support = win['source_specific_support']

        if (
            win['accepted'] is not True
            or support['separate_source_residual_blocks'] is not True
            or support['physical_observability_verified'] is not False
            or support['real_sensor_noise_calibrated'] is not False
            or support['runtime_health_weighting_enabled'] is not False
        ):
            raise BoundaryError(
                'Unqualified source-specific window support'
            )

    legacy = legacy_case(
        condition,
        seed,
        camera_enabled=camera_enabled
    )

    ledger = legacy['relative_pose_factors']
    legacy_lidar = len(lidar) - overlap
    legacy_total = legacy_lidar + len(camera)

    if (
        ledger['synthetic_camera_factor_count'] != len(camera)
        or ledger['synthetic_lidar_factor_count'] != legacy_lidar
        or ledger['total_relative_pose_factor_count'] != legacy_total
        or ledger['same_edge_measurements_double_counted'] is not False
        or ledger['backend_can_independently_weight_camera'] is not False
        or legacy['estimated_node_count'] != 5
        or legacy['real_sensor_data_used'] is not False
    ):
        raise BoundaryError(
            'Legacy substitution contract changed'
        )

    return {
        'condition': condition,
        'seed': seed,
        'manufactured_camera_enabled': camera_enabled,
        'legacy_pose_slots': legacy_total,
        'legacy_camera_slots': len(camera),
        'legacy_lidar_slots': legacy_lidar,
        'separated_pose_factors': len(camera) + len(lidar),
        'separated_camera_factors': len(camera),
        'separated_lidar_factors': len(lidar),
        'same_edge_separate_source_pairs': overlap,
        'camera_measurement_id_count': len(ids),
        'separate_source_factor_ownership_verified': True,
        'synthetic_lidar_missing_node_frames': expected['missing_node_frames'],
        'shadow_only_lidar_hold_windows': expected['required_shadow_holds'],
        'fixed_camera_residual_scales_calibrated': False,
        'real_source_attribution': 'UNRESOLVED',
        'real_factor_admission': 'DENIED',
        'robot_actuation': 'DENIED',
        'separated_estimated_state_count': len(estimated),
        'legacy_numeric_trajectory_sha256':
            legacy['estimated_trajectory_sha256'],
        'separated_numeric_trajectory_sha256':
            hashlib.sha256(canonical(estimated)).hexdigest(),
    }

def execute():
    guard(ORIGIN)

    controls = [
        run_case(*c)
        for c in CASES
    ]

    return {
        'schema': SCHEMA,
        'manufactured_mirrored_causality_counterexample':
            mirrored_ambiguity(),
        'separated_vs_substitution_controls': controls,
        'existing_separated_estimator_used': True,
        'fixed_scales_are_empirically_calibrated': False,
        'real_sensor_data_opened': False,
        'physical_source_attribution': 'UNRESOLVED',
        'real_factor_admission': 'DENIED',
        'robot_actuation': 'DENIED',
    }
