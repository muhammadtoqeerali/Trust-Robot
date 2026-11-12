"""A46-1 manufactured camera/LiDAR joint-factor faults, existing 15D solver.

Only a precomputed synthetic LiDAR registration factor is perturbed; no scan
is changed or re-registered. Camera measurements are manufactured relative
poses. The solver uses fixed numerical scales, not calibrated health weights.
"""
from __future__ import annotations

from dataclasses import replace
from unittest.mock import patch
import hashlib
import json
import math

SCHEMA = 'TRUST_ROBOT_R135_A46_1_JOINT_FAULT_IDENTIFIABILITY_V1'
ORIGIN = 'ANALYTIC_FIXTURE'
EDGE = (0, 1)
DELTA_M = 0.125

DESIGNS = {
    'baseline': ('clean', 0.0, 0.0),
    'camera_only': ('clean', DELTA_M, 0.0),
    'lidar_only': ('clean', 0.0, DELTA_M),
    'joint_common_mode': ('clean', DELTA_M, DELTA_M),
    'joint_opposing': ('clean', DELTA_M, -DELTA_M),
    'dropout_and_camera': ('lidar_dropout', DELTA_M, 0.0),
}

class ContractError(ValueError):
    pass

def canonical(x):
    return (
        json.dumps(
            x, sort_keys=True, separators=(',', ':'), allow_nan=False
        ) + '\n'
    ).encode()

def sha(x):
    return hashlib.sha256(canonical(x)).hexdigest()

def guard(origin):
    if type(origin) is not str or origin != ORIGIN:
        raise ContractError(
            'No live/recorded/unknown measurements authorized'
        )

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

    raise ContractError(
        'Source-attribution gate unexpectedly open'
    )

def shift_x(p, amount):
    from trust_robot.clean_backbone import PoseSE3

    if (
        not isinstance(p, PoseSE3)
        or type(amount) is not float
        or amount not in (-DELTA_M, 0.0, DELTA_M)
    ):
        raise ContractError(
            'Only frozen pose translations permitted'
        )

    t = p.translation_m

    return PoseSE3(
        (
            float(t[0]) + amount,
            float(t[1]),
            float(t[2]),
        ),
        p.quaternion_wxyz,
    )

def construct(design, seed=13, origin=ORIGIN):
    guard(origin)

    if (
        type(design) is not str
        or design not in DESIGNS
        or type(seed) is not int
        or seed not in (13, 31)
    ):
        raise ContractError(
            'Unlisted manufactured intervention'
        )

    from trust_robot.analytic_inertial_15d import make_fixture
    from trust_robot.analytic_preintegrated_fusion import (
        make_factors, NODE_FRAMES,
    )
    from trust_robot.analytic_three_modality_bridge import (
        manufactured_camera_packets, CAMERA_EDGES,
    )
    from trust_robot.analytic_separated_modalities import camera_factor_map
    from trust_robot.factor_ownership_availability_bridge_v1 import model

    condition, cam_dx, lidar_dx = DESIGNS[design]

    if (
        tuple(NODE_FRAMES) != (0, 2, 4, 6, 8)
        or tuple(CAMERA_EDGES) != ((0, 1), (2, 3))
    ):
        raise ContractError(
            'Frozen estimator topology changed'
        )

    fixture, truth = make_fixture(condition)

    if (
        len(fixture['imu']) != 8
        or any(
            x.get('measurement_origin') != ORIGIN
            or x.get('physical_clock_verified') is not False
            for x in fixture['imu']
        )
    ):
        raise ContractError(
            'Synthetic input provenance changed'
        )

    expected = model(fixture['available'])
    imu, lidar, counts = make_factors(fixture)

    if (
        set(imu) != {(0,1),(1,2),(2,3),(3,4)}
        or sorted(lidar) != [
            tuple(x) for x in expected['lidar_edge_keys']
        ]
        or counts['lidar_factor_count'] != len(lidar)
        or counts['imu_samples_reused'] is not False
        or EDGE not in lidar
    ):
        raise ContractError(
            'Synthetic frontend provenance/factors changed'
        )

    camera = camera_factor_map(
        manufactured_camera_packets(truth, seed=seed)
    )

    if (
        len(camera) != 2
        or EDGE not in camera
        or len({
            v.measurement_id for v in camera.values()
        }) != 2
    ):
        raise ContractError(
            'Synthetic camera identity changed'
        )

    if any(
        p.origin != ORIGIN or p.modality != 'camera'
        for p in camera.values()
    ):
        raise ContractError(
            'Unexpected camera measurement origin'
        )

    new_camera = dict(camera)
    new_lidar = dict(lidar)

    new_camera[EDGE] = replace(
        camera[EDGE],
        measurement=shift_x(
            camera[EDGE].measurement, cam_dx
        ),
    )

    new_lidar[EDGE] = shift_x(
        lidar[EDGE], lidar_dx
    )

    if (
        set(new_lidar) != set(lidar)
        or set(new_camera) != set(camera)
    ):
        raise ContractError(
            'Intervention changed factor ownership'
        )

    return (
        fixture, imu, new_lidar, counts,
        tuple(new_camera[k] for k in sorted(new_camera)),
        expected,
    )

def gap(camera, lidar):
    from trust_robot.synthetic_cross_modal_ambiguity_v1 import pose_gap

    return pose_gap(
        lidar, camera
    )['relative_translation_difference_m']

def pair_signature(camera, lidar):
    return sha({
        'camera': camera.to_dict(),
        'lidar': lidar.to_dict(),
    })

def run_case(design, seed=13, origin=ORIGIN):
    guard(origin)

    fixture, imu, lidar, counts, packets, expected = construct(
        design, seed, origin
    )

    from trust_robot import analytic_separated_modalities as solver
    from trust_robot.analytic_separated_modalities import camera_factor_map

    camera = camera_factor_map(packets)
    base_factory = solver.make_factors

    # Local intervention only. The frozen estimator source is untouched.
    with patch.object(
        solver, 'make_factors',
        return_value=(imu, lidar, counts),
    ) as mocked:
        records, audit = solver.estimate_separated(
            fixture, packets
        )

        if mocked.call_count != 1:
            raise ContractError(
                'Unexpected synthetic factor-factory calls'
            )

    if solver.make_factors is not base_factory:
        raise ContractError(
            'Factor factory leaked beyond synthetic experiment'
        )

    if not (
        len(records) == 5
        and audit['camera_factor_count'] == 2
        and audit['lidar_factor_count'] == len(lidar)
        and audit['imu_factor_count'] == 4
        and audit['accepted_window_count'] == 4
        and audit['schur_elimination_count'] == 3
        and audit['unaccounted_factor_count'] == 0
        and audit['factor_reuse_after_marginalization'] is False
        and audit['independent_source_residual_blocks'] is True
        and audit['same_edge_camera_and_lidar_supported'] is True
        and audit['real_sensor_factor_execution_authorized'] is False
        and audit['empirical_covariance_calibrated'] is False
        and audit['health_factor_conditioning_executed'] is False
    ):
        raise ContractError(
            'Existing separate solver accounting changed'
        )

    ids = [p.measurement_id for p in packets]
    accounted = (
        audit['consumed_camera_ids']
        + audit['remaining_camera_ids']
    )

    if (
        sorted(ids) != sorted(accounted)
        or len(set(accounted)) != 2
    ):
        raise ContractError(
            'Camera measurement identity lost/reused'
        )

    lidarkeys = [
        tuple(v)
        for v in (
            audit['consumed_lidar_keys']
            + audit['remaining_lidar_keys']
        )
    ]

    if (
        len(lidarkeys) != len(set(lidarkeys))
        or set(lidarkeys) != set(lidar)
    ):
        raise ContractError(
            'LiDAR factor identity lost/reused'
        )

    if not all(
        w['source_specific_support']['real_sensor_noise_calibrated'] is False
        and w['source_specific_support']['physical_observability_verified'] is False
        and w['source_specific_support']['runtime_health_weighting_enabled'] is False
        for w in audit['windows']
    ):
        raise ContractError(
            'Unexpected physical support admission'
        )

    condition, cam_dx, lidar_dx = DESIGNS[design]

    return {
        'scenario': design,
        'seed': seed,
        'manufactured_imu_condition': condition,
        'scripted_camera_shift_x_m': cam_dx,
        'scripted_lidar_shift_x_m': lidar_dx,
        'pair_translation_gap_m': gap(
            camera[EDGE].measurement, lidar[EDGE]
        ),
        'pair_observation_sha256': pair_signature(
            camera[EDGE].measurement, lidar[EDGE]
        ),
        'trajectory_sha256': sha(records),
        'final_synthetic_position_m': records[-1]['position_m'],
        'camera_factors': 2,
        'lidar_factors': len(lidar),
        'lidar_drop_shadow_windows': expected['required_shadow_holds'],
        'window_numerical_support': [
            w['source_specific_support']['status']
            for w in audit['windows']
        ],
        'known_scripted_design_is_inferred_fault': False,
        'responsible_real_modality': 'UNRESOLVED',
        'real_factor_admission': 'DENIED',
        'robot_actuation': 'DENIED',
        'post_frontend_lidar_factor_perturbed': lidar_dx != 0.0,
        'actual_lidar_scans_reprocessed': False,
    }

def execute():
    rows = [
        run_case(name, 13)
        for name in DESIGNS
    ]

    rows += [
        run_case(name, 31)
        for name in ('baseline', 'joint_common_mode')
    ]

    k = {
        (x['scenario'], x['seed']): x
        for x in rows
    }

    for seed in (13, 31):
        nominal = k['baseline', seed]
        common = k['joint_common_mode', seed]

        if (
            nominal['pair_translation_gap_m']
            != common['pair_translation_gap_m']
            or nominal['pair_observation_sha256']
            == common['pair_observation_sha256']
        ):
            raise ContractError(
                'Common-mode discrepancy invariance not reproduced'
            )

    if (
        k['dropout_and_camera', 13]['lidar_drop_shadow_windows']
        != [2, 3]
    ):
        raise ContractError(
            'Known synthetic dropout escaped shadow'
        )

    return {
        'schema': SCHEMA,
        'case_count': len(rows),
        'cases': rows,
        'common_mode_pairwise_discrepancy_unchanged_for_two_seeds': True,
        'joint_synthetic_fault_diagnosis': 'AMBIGUOUS',
        'physical_sensor_source_attribution': 'UNRESOLVED',
        'calibrated_health_probability_available': False,
        'physical_covariance_verified': False,
        'actual_sensor_data_accessed': False,
        'real_factor_admission': 'DENIED',
        'robot_actuation': 'DENIED',
    }
