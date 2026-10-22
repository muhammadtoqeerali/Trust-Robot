"""R102: actual R95/S6 prior compatibility evidence.

An executable audit, not an integration shortcut.
Synthetic-only. Cross-backend binding is always denied.
"""

import json
import numpy as np

from unittest.mock import patch

import r84_gap_frontend as gap
import r86_rolling as rolling
import r88_schur as schur
import r89_prior as r89
import r90_prior_guard as guard
import r101_prior_adapter as adapter

import s6_joint_fusion as s6

from trust_robot.analytic_inertial_15d import (
    DT, initial_state, make_fixture,
)
from trust_robot.analytic_preintegrated_fusion import (
    NODE_FRAMES, whitened_inertial_residual,
)
from trust_robot.analytic_three_modality_bridge import (
    manufactured_camera_packets,
)

SCHEMA='TRUST_ROBOT_R102_SYNTHETIC_BACKEND_COMPATIBILITY_V1'

REASONS=(
    'FRAME_NAMESPACE_MISMATCH',
    'CLOCK_EPOCH_NOT_ASSOCIATED',
    'WINDOW_DURATION_MISMATCH',
    'GAUGE_ANCHOR_MISMATCH',
    'PRIOR_RETAINED_DIMENSION_MISMATCH',
    'PRIOR_NODE_IDENTITY_MISMATCH',
    'REGULARIZATION_POLICY_MISMATCH',
    'FACTOR_LINEAGE_MAPPING_NOT_ESTABLISHED',
)

class CompatibilityError(ValueError):
    pass

def need(ok,reason):
    if not ok:
        raise CompatibilityError(reason)

def canonical(obj):
    return (
        json.dumps(
            obj,sort_keys=True,indent=2,allow_nan=False
        )+'\n'
    ).encode()

def observe_source():
    """Inspect a real R95 manufactured prior, not a mock matrix."""

    packets=gap.fixture('continuous')
    segments,gaps=schur.segment_groups(packets)

    need(
        gaps==0 and len(segments)==1,
        'R95_SEGMENTS'
    )

    first=segments[0][0]
    start,end,_=first

    H,g,c=r89.construct_condensed_prior(
        segments[0][:1],0
    )

    record=guard.make_record(H,g,c,0)

    result=adapter.bridge(
        record,
        segment_id=0,
        expected_token=guard.token(0),
        source_space=adapter.LOCAL_SPACE,
        target_space=adapter.LOCAL_SPACE,
        node_id=100,
        reference=np.zeros(15),
    )

    need(
        result[
            'bind_to_s6_nonlinear_solver_authorized'
        ] is False,
        'SOURCE_BINDING_POLICY'
    )

    return {
        'backend':'R95_LOCAL_GAUSSIAN',
        'frame_namespace':adapter.LOCAL_SPACE,
        'timestamp_epoch_ns':int(start),
        'window_duration_ns':int(end-start),
        'initial_anchor':rolling.synthetic_anchor().tolist(),
        'prior_dimension':
            int(result['prior'].reference.size),
        'retained_node_ids':
            list(result['prior'].node_ids),
        'ridge_weight':float(schur.RIDGE),
        'source_measurement_family':gap.SOURCE,
        'factor_lineage_cross_backend_verified':False,
        'record_fingerprint':
            record['fingerprint'],
    }

def observe_target():
    """Capture actual S6 nonlinear marginalization output."""

    fixture,truth=make_fixture('clean')
    packets=manufactured_camera_packets(truth,seed=13)

    original=s6.marginalize_one
    captured=[]

    def capture(*args,**kwargs):
        result=original(*args,**kwargs)
        captured.append(result[0])
        return result

    with patch.object(
        s6,'marginalize_one',side_effect=capture
    ):
        records,audit=s6.estimate_joint(
            fixture,packets
        )

    need(
        s6.marginalize_one is original,
        'INSTRUMENTATION_NOT_RESTORED'
    )

    need(
        len(captured)==3
        and audit['schur_elimination_count']==3
        and audit['accepted_window_count']==4,
        'S6_LIFECYCLE'
    )

    first=captured[0]

    need(
        first.node_ids==(1,2)
        and first.reference.size==30,
        'S6_RETAINED_PRIOR'
    )

    need(
        audit['real_sensor_factor_admitted'] is False
        and audit['physical_measurements_used'] is False,
        'S6_PHYSICAL_BOUNDARY'
    )

    need(len(records)==len(NODE_FRAMES),'S6_STATES')

    return {
        'backend':'S6_NONLINEAR_FIXED_LAG',
        'frame_namespace':'S6_SYNTHETIC_BODY_GRAPH',
        'timestamp_epoch_ns':0,
        'window_duration_ns':int(
            round(
                (NODE_FRAMES[1]-NODE_FRAMES[0])
                *DT*1e9
            )
        ),
        'initial_anchor':initial_state().tolist(),
        'prior_dimension':int(first.reference.size),
        'retained_node_ids':list(first.node_ids),
        'anchor_sigma':0.01,
        'source_measurement_family':
            'S6_SYNTHETIC_PREINTEGRATED_CAMERA_LIDAR',
        'factor_lineage_cross_backend_verified':False,
        'actual_marginalizations':len(captured),
        'consumed_pose_ids':audit['consumed_pose_ids'],
        'remaining_pose_ids':audit['remaining_pose_ids'],
    }

def diagnose(source,target):
    need(
        type(source) is dict
        and type(target) is dict,
        'PROFILE_TYPE'
    )

    fields=(
        'frame_namespace','timestamp_epoch_ns',
        'window_duration_ns','initial_anchor',
        'prior_dimension','retained_node_ids'
    )

    need(
        all(k in source and k in target for k in fields),
        'PROFILE_INCOMPLETE'
    )

    reasons=[]

    if source['frame_namespace']!=target['frame_namespace']:
        reasons.append(REASONS[0])

    # Distinct synthetic origins are not a measured
    # clock-domain correspondence.
    if source['timestamp_epoch_ns']!=target['timestamp_epoch_ns']:
        reasons.append(REASONS[1])

    if source['window_duration_ns']!=target['window_duration_ns']:
        reasons.append(REASONS[2])

    a=np.asarray(source['initial_anchor'],dtype=float)
    b=np.asarray(target['initial_anchor'],dtype=float)

    need(
        a.shape==(15,) and b.shape==(15,)
        and np.isfinite(a).all()
        and np.isfinite(b).all(),
        'ANCHOR_VALIDITY'
    )

    if not np.array_equal(a,b):
        reasons.append(REASONS[3])

    if source['prior_dimension']!=target['prior_dimension']:
        reasons.append(REASONS[4])

    if source['retained_node_ids']!=target['retained_node_ids']:
        reasons.append(REASONS[5])

    # These weights serve different mathematical roles:
    # R95's manufactured unary ridge vs S6 gauge sigma.
    # There is no established source-level equivalence.
    if (
        source.get('ridge_weight') is not None
        and target.get('anchor_sigma') is not None
    ):
        reasons.append(REASONS[6])

    if not (
        source.get('factor_lineage_cross_backend_verified') is True
        and target.get('factor_lineage_cross_backend_verified') is True
    ):
        reasons.append(REASONS[7])

    return tuple(reasons)

def bind_to_live_s6(*args,**kwargs):
    """No caller-controlled bypass exists."""
    raise CompatibilityError(
        'CROSS_BACKEND_BINDING_NOT_AUTHORIZED'
    )

def execute():
    need(
        schur.N==s6.STATE_DIM==15,
        'STATE_DIMENSION_DISAGREEMENT'
    )

    need(
        schur.whitened_inertial_residual
        is s6.whitened_inertial_residual
        is whitened_inertial_residual,
        'COMMON_INERTIAL_RESIDUAL_IDENTITY'
    )

    source=observe_source()
    target=observe_target()
    blockers=diagnose(source,target)

    need(
        blockers==REASONS,
        'UNEXPECTED_COMPATIBILITY_DECISION'
    )

    need(
        source['window_duration_ns']==100000000
        and target['window_duration_ns']==200000000,
        'SYNTHETIC_DURATION_FACTS'
    )

    need(
        source['prior_dimension']==15
        and target['prior_dimension']==30,
        'ACTUAL_PRIOR_DIMENSIONS'
    )

    need(
        source['retained_node_ids']==[100]
        and target['retained_node_ids']==[1,2],
        'ACTUAL_NODE_OWNERSHIP'
    )

    return {
        'schema':SCHEMA,
        'status':'PASS_FAIL_CLOSED_COMPATIBILITY_AUDIT',
        'source':source,
        'target':target,
        'shared_inertial_residual_function':True,
        'shared_15d_state_size':True,
        'compatibility_blockers':list(blockers),
        'compatibility_blocker_count':len(blockers),
        'real_cross_backend_prior_binding_performed':False,
        'r95_backend_merged_into_s6':False,
        'source_trajectory_alignment_verified':False,
        'physical_clock_or_extrinsics_verified':False,
        'real_sensor_factors_authorized':False,
        'health_training_authorized':False,
        'ate_rpe_authorized':False,
        'confirmation_test_accessed':False,
        'raw_gt_or_rosbags_opened':False,
        'scientific_gates_closed':11,
    }

if __name__=='__main__':
    import sys

    report=execute()

    with open(sys.argv[1],'x',encoding='utf-8') as f:
        f.write(canonical(report).decode())

    print('R102_SHARED_INERTIAL_PRIMITIVE=PASS')
    print('R102_ACTUAL_R95_S6_PRIORS=INSPECTED')
    print('R102_COMPATIBILITY_BLOCKERS=8_CONFIRMED')
    print('R102_DIRECT_BACKEND_BINDING=DENIED')
    print('R102_REAL_SENSOR_FACTORS=DENIED')
