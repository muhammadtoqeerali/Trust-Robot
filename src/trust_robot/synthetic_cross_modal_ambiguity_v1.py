"""A45-1: manufactured camera-vs-LiDAR pose disagreement and slot ownership.

No physical event time, geometry calibration, health labels, source blame,
operational consistency calculation, independent camera weighting or controls.
"""
from __future__ import annotations
import json
import math

SCHEMA='TRUST_ROBOT_R135_A45_1_SYNTHETIC_CROSS_MODAL_AMBIGUITY_V1'
ORIGIN='ANALYTIC_FIXTURE'

class EvidenceBoundary(ValueError):
    pass

def canonical(value):
    return (
        json.dumps(
            value,sort_keys=True,separators=(',',':'),allow_nan=False
        )+'\n'
    ).encode()

def guard(origin):
    if type(origin) is not str or origin != ORIGIN:
        raise EvidenceBoundary(
            'Recorded, live, or unknown origin is prohibited'
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

    raise EvidenceBoundary(
        'Attribution unexpectedly authorized'
    )

def pose_gap(lidar, camera):
    from trust_robot.clean_backbone import PoseSE3

    if not isinstance(lidar,PoseSE3) or not isinstance(camera,PoseSE3):
        raise EvidenceBoundary(
            'Only typed manufactured relative poses'
        )

    delta=lidar.inverse().compose(camera)

    t=math.sqrt(
        sum(float(x)*float(x) for x in delta.translation_m)
    )

    q=delta.quaternion_wxyz
    angle=2.0*math.degrees(
        math.acos(min(1.0,max(0.0,abs(float(q[0])))))
    )

    if not (math.isfinite(t) and math.isfinite(angle)):
        raise EvidenceBoundary('Nonfinite diagnostic')

    return {
        'relative_translation_difference_m':round(t,12),
        'relative_rotation_difference_deg':round(angle,12),
        'selected_physical_threshold':False,
        'physical_metric_calibrated':False,
    }

def refuse_attribution(source):
    raise EvidenceBoundary(
        'Pairwise disagreement cannot assign cause: '
        +str(type(source).__name__)
    )

def competing_hypotheses(evidence):
    if (
        type(evidence) is not dict
        or type(
            evidence.get('relative_translation_difference_m')
        ) is not float
        or type(
            evidence.get('relative_rotation_difference_deg')
        ) is not float
        or evidence.get('selected_physical_threshold') is not False
        or evidence.get('physical_metric_calibrated') is not False
        or not all(
            math.isfinite(evidence[k]) and evidence[k]>=0
            for k in (
                'relative_translation_difference_m',
                'relative_rotation_difference_deg'
            )
        )
    ):
        raise EvidenceBoundary(
            'Ineligible discrepancy evidence'
        )

    return {
        'observed_pairwise_difference':dict(evidence),
        'compatible_unverified_hypotheses':[
            'CAMERA_MEASUREMENT_ASSUMED_NOMINAL',
            'LIDAR_MEASUREMENT_ASSUMED_NOMINAL',
        ],
        'responsible_modality':'UNRESOLVED',
        'hypothesis_probability_assigned':False,
        'sensor_health_classified':False,
    }

def paired_fixture(seed=13,origin=ORIGIN):
    guard(origin)

    if type(seed) is not int or seed not in (13,31):
        raise EvidenceBoundary(
            'Only two frozen synthetic seeds'
        )

    from trust_robot.analytic_inertial_15d import make_fixture
    from trust_robot.analytic_preintegrated_fusion import (
        make_factors,NODE_FRAMES
    )
    from trust_robot.analytic_three_modality_bridge import (
        manufactured_camera_packets,CAMERA_EDGES
    )
    from trust_robot.multimodal_factor_interface import (
        assemble_synthetic_pose_slot,CAMERA_SOURCE,ANALYTIC_FRAME
    )

    if (
        tuple(NODE_FRAMES)!=(0,2,4,6,8)
        or tuple(CAMERA_EDGES)!=((0,1),(2,3))
    ):
        raise EvidenceBoundary(
            'Frozen synthetic chronology changed'
        )

    fixture, manufactured_truth = make_fixture('clean')

    if (
        len(fixture['available'])!=9
        or any(v is not True for v in fixture['available'])
    ):
        raise EvidenceBoundary(
            'Clean synthetic scan source changed'
        )

    inertial,lidar,meta=make_factors(fixture)
    camera=manufactured_camera_packets(
        manufactured_truth,seed=seed
    )

    if (
        len(inertial)!=4
        or len(lidar)!=7
        or len(camera)!=2
        or meta.get('imu_samples_reused') is not False
        or meta.get('lidar_factor_count')!=7
    ):
        raise EvidenceBoundary(
            'Frozen frontend factor counts changed'
        )

    observations=[]

    for packet in camera:
        if (
            packet.edge not in lidar
            or packet.modality!='camera'
            or packet.origin!=ORIGIN
            or packet.source_id!=CAMERA_SOURCE
            or packet.frame_id!=ANALYTIC_FRAME
        ):
            raise EvidenceBoundary(
                'Manufactured camera provenance mismatch'
            )

        diag=pose_gap(
            lidar[packet.edge],packet.measurement
        )

        observations.append({
            'edge':list(packet.edge),
            'synthetic_camera_measurement_id':packet.measurement_id,
            'diagnostic_only':competing_hypotheses(diag),
        })

    combined,ledger=assemble_synthetic_pose_slot(
        lidar,camera,NODE_FRAMES
    )

    if (
        len(combined)!=7
        or ledger['synthetic_camera_factor_count']!=2
        or ledger['synthetic_lidar_factor_count']!=5
        or ledger['total_relative_pose_factor_count']!=7
        or ledger['replaced_lidar_edges']!=[[0,1],[2,3]]
        or ledger['same_edge_measurements_double_counted'] is not False
        or ledger['backend_can_independently_weight_camera'] is not False
        or ledger['real_sensor_factor_execution_authorized'] is not False
        or len(ledger['factor_ledger'])!=7
        or any(
            row['origin']!=ORIGIN
            for row in ledger['factor_ledger']
        )
    ):
        raise EvidenceBoundary(
            'Legacy same-edge pose-slot ownership changed'
        )

    return {
        'seed':seed,
        'paired_camera_lidar_edges':observations,
        'camera_lidar_edge_overlap_count':2,
        'frozen_legacy_pose_slot':{
            'relative_pose_slot_count':7,
            'camera_substitutions':2,
            'remaining_lidar_slots':5,
            'same_edge_double_counted':False,
            'independent_camera_information_scaling_available':False,
        },
        'physical_sensor_source_attribution':'UNRESOLVED',
        'real_factors_admitted':False,
    }

def solver_control(condition,enabled,origin=ORIGIN):
    guard(origin)

    if (
        condition not in ('clean','lidar_dropout')
        or type(enabled) is not bool
    ):
        raise EvidenceBoundary(
            'Unlisted frozen synthetic experiment'
        )

    from trust_robot.analytic_three_modality_bridge import execute_case

    row=execute_case(
        condition,13,camera_enabled=enabled
    )

    info=row['relative_pose_factors']

    for k in (
        'camera_pixels_processed',
        'real_sensor_data_used',
        'health_factor_weighting_executed',
        'physical_synchronization_verified',
        'factor_covariance_empirically_calibrated'
    ):
        if row.get(k) is not False:
            raise EvidenceBoundary(
                'Unexpected real-data / calibrated capability'
            )

    if (
        row['estimated_node_count']!=5
        or row['inertial_factor_count']!=4
        or row['accepted_window_count']!=4
        or row['schur_elimination_count']!=3
        or row['factor_accounting_valid'] is not True
        or info['same_edge_measurements_double_counted'] is not False
        or info['backend_can_independently_weight_camera'] is not False
        or info['real_sensor_factor_execution_authorized'] is not False
    ):
        raise EvidenceBoundary(
            'Synthetic factor accounting changed'
        )

    expected={
        ('clean',False):(0,7,7),
        ('clean',True):(2,5,7),
        ('lidar_dropout',False):(0,3,3),
        ('lidar_dropout',True):(2,2,4),
    }

    expected_row=expected[condition,enabled]

    actual=(
        info['synthetic_camera_factor_count'],
        info['synthetic_lidar_factor_count'],
        info['total_relative_pose_factor_count']
    )

    if actual!=expected_row:
        raise EvidenceBoundary(
            'Frozen camera substitution counts changed'
        )

    return {
        'condition':condition,
        'manufactured_camera_enabled':enabled,
        'camera_slots':actual[0],
        'lidar_slots':actual[1],
        'total_pose_slots':actual[2],
        'solver_state_count':5,
        'numeric_trajectory_digest':row['estimated_trajectory_sha256'],
        'real_sensor_factor_admission':'DENIED',
        'physical_attribution':'UNRESOLVED',
    }

def execute():
    guards=paired_fixture(seed=13)
    repeat_seed=paired_fixture(seed=31)

    controls=[
        solver_control(c,e)
        for c,e in (
            ('clean',False),
            ('clean',True),
            ('lidar_dropout',False),
            ('lidar_dropout',True),
        )
    ]

    return {
        'schema':SCHEMA,
        'pairwise_synthetic_cases':[guards,repeat_seed],
        'frozen_solver_controls':controls,
        'consistency_signal':'SYNTHETIC_DESCRIPTIVE_DIFFERENCE_ONLY',
        'attribution':'UNRESOLVED',
        'real_health_probabilities_inferred':False,
        'independent_camera_factor_weighting_executed':False,
        'real_factor_admission':'DENIED',
        'robot_actuation':'DENIED',
        'm2dgr_data_opened':False,
        'nova_contacted':False,
    }
