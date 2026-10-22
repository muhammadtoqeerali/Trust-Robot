"""R101 guarded R95 Gaussian -> S6 square-root prior representation.

Mathematical representation conversion only.

The source prior has a manufactured R95 local linearization,
fixed gauge and synthetic factor history. It is NOT an S6
nonlinear pose prior until frame, gauge, chronology and
factor ownership are established by a separate integration.

No recorded measurements or physical qualifications.
"""

import json
import math
import numpy as np

import r84_gap_frontend as gap
import r88_schur as schur
import r89_prior as r89
import r90_prior_guard as guard

from trust_robot.analytic_schur_marginalization import (
    SquareRootInformationPrior,
)

SCHEMA='TRUST_ROBOT_R101_SYNTHETIC_PRIOR_ADAPTER_V1'
LOCAL_SPACE='R95_LOCAL_GAUSSIAN_TANGENT_V1'
S6_SPACE='S6_NONLINEAR_STATE_SPACE'
N=15

class BridgeError(ValueError):
    pass

def need(ok,why):
    if not ok:
        raise BridgeError(why)

def canonical(value):
    return (
        json.dumps(
            value,sort_keys=True,indent=2,allow_nan=False
        )+'\n'
    ).encode('utf-8')

def quadratic(H,g,c,d):
    return float(
        0.5*d@H@d-g@d+c
    )

def bridge(
    record, *,
    segment_id,
    expected_token,
    source_space,
    target_space,
    node_id,
    reference,
):
    """Create a quarantined square-root representation.

    Only a separate local-test node (100+segment_id)
    is permitted. Real S6 optimizer nodes are 0..4.
    """

    need(
        type(segment_id) is int
        and 0<=segment_id<=100,
        'SEGMENT_ID'
    )

    need(
        source_space==LOCAL_SPACE
        and target_space==LOCAL_SPACE,
        'FRAME_OR_GAUGE_MISMATCH'
    )

    need(
        type(node_id) is int
        and node_id==100+segment_id,
        'LIVE_S6_NODE_BINDING_DENIED'
    )

    need(
        type(expected_token) is str
        and expected_token==guard.token(segment_id),
        'STALE_LINEARIZATION'
    )

    need(
        type(record) is dict
        and record.get('segment_id')==segment_id
        and record.get('linearization_token')==expected_token,
        'CROSS_SEGMENT_PRIOR_REUSE'
    )

    ref=np.asarray(reference,dtype=float)

    need(
        ref.shape==(N,)
        and np.isfinite(ref).all(),
        'REFERENCE_VECTOR'
    )

    # Existing R90 validation checks source identity,
    # anchor, fingerprint, SPD and scientific denials.
    H,g,c,condition=guard.validate(record)

    admitted=guard.admit(
        record,segment_id,expected_token,
        np.zeros(N,dtype=float)
    )

    need(
        admitted['real_sensor_factor_executable']
        is False
        and admitted['frozen_jacobians_modified']
        is False,
        'SOURCE_AUTHORIZATION'
    )

    # R95: 0.5*d.T@H@d - g.T@d + c
    # S6:  0.5*||S@d + b||^2 + k
    #
    # S.T@S=H and S.T@b=-g.
    S=np.linalg.cholesky(H).T
    b=np.linalg.solve(S.T,-g)

    k=float(c-0.5*b@b)

    need(
        np.isfinite(S).all()
        and np.isfinite(b).all()
        and math.isfinite(k),
        'SQUARE_ROOT_NUMERICS'
    )

    p=SquareRootInformationPrior(
        (node_id,),
        ref.copy(),
        S.copy(),
        b.copy(),
    )

    H2,linear=p.normal_equations()

    h_error=float(
        np.linalg.norm(H2-H)
        /max(1.,np.linalg.norm(H))
    )

    g_error=float(
        np.linalg.norm(linear+g)
        /max(1.,np.linalg.norm(g))
    )

    need(
        h_error<1e-9
        and g_error<1e-9,
        'NORMAL_EQUATION_RECONSTRUCTION'
    )

    errors=[]

    for i in range(4):
        if i==0:
            d=np.zeros(N)
        else:
            d=1e-5*i*np.sin(
                np.arange(N,dtype=float)+i
            )

        original=quadratic(H,g,c,d)

        residual=p.residual({
            node_id:ref+d
        })

        reconstructed=float(
            0.5*residual@residual+k
        )

        err=abs(original-reconstructed)/max(
            1.,abs(original),abs(reconstructed)
        )

        errors.append(float(err))

    need(
        max(errors)<1e-7,
        'QUADRATIC_ENERGY_MISMATCH'
    )

    return {
        'prior':p,
        'additive_constant':k,
        'segment_id':segment_id,
        'source_record_fingerprint':
            record['fingerprint'],
        'linearization_token':expected_token,
        'source_space':source_space,
        'target_space':target_space,
        'quarantine_node_id':node_id,
        'information_relative_error':h_error,
        'gradient_relative_error':g_error,
        'max_energy_relative_error':max(errors),
        'information_condition_number':condition,
        'original_nonlinear_factors_relinearized':False,
        'bind_to_s6_nonlinear_solver_authorized':False,
        'physical_source_verified':False,
    }

def bind_to_s6_nonlinear_solver(*args,**kwargs):
    """An explicit fail-closed integration boundary."""
    raise BridgeError(
        'S6_NONLINEAR_BINDING_NOT_AUTHORIZED'
    )

def run_case(name):
    need(
        name in (
            'continuous','single_gap',
            'accel_injection','gyro_injection'
        ),
        'SCENARIO'
    )

    packets=gap.fixture(name)
    segments,gaps=schur.segment_groups(packets)

    need(
        len(segments)==gaps+1,
        'GAP_ACCOUNTING'
    )

    rows=[]

    for sid,groups in enumerate(segments):
        prefixes=[]

        for step in range(len(groups)):
            H,g,c=r89.construct_condensed_prior(
                groups[:step+1],sid
            )

            record=guard.make_record(
                H,g,c,sid
            )

            ref=1e-4*np.sin(
                np.arange(N,dtype=float)+sid+step
            )

            result=bridge(
                record,
                segment_id=sid,
                expected_token=guard.token(sid),
                source_space=LOCAL_SPACE,
                target_space=LOCAL_SPACE,
                node_id=100+sid,
                reference=ref,
            )

            need(
                result['prior'].node_ids==(100+sid,)
                and result[
                    'bind_to_s6_nonlinear_solver_authorized'
                ] is False,
                'QUARANTINE'
            )

            prefixes.append({
                'step':step,
                'source_record_fingerprint':
                    result['source_record_fingerprint'],
                'information_relative_error':
                    result['information_relative_error'],
                'gradient_relative_error':
                    result['gradient_relative_error'],
                'max_energy_relative_error':
                    result['max_energy_relative_error'],
                'condition_number':
                    result['information_condition_number'],
                'quarantine_node_id':100+sid,
            })

        rows.append({
            'segment_id':sid,
            'prefixes':prefixes,
            'fresh_synthetic_segment_gauge':True,
            'prior_copied_across_gap':False,
        })

    return {
        'scenario':name,
        'segments':len(rows),
        'timestamp_gaps':gaps,
        'converted_prefixes':
            sum(len(x['prefixes']) for x in rows),
        'rows':rows,
        'cross_gap_prior_reuse':False,
    }

def execute():
    names=(
        'continuous','single_gap',
        'accel_injection','gyro_injection'
    )

    cases={
        name:run_case(name)
        for name in names
    }

    prefixes=sum(
        c['converted_prefixes']
        for c in cases.values()
    )

    segments=sum(
        c['segments']
        for c in cases.values()
    )

    gaps=sum(
        c['timestamp_gaps']
        for c in cases.values()
    )

    need(
        prefixes==16
        and segments==5
        and gaps==1,
        'EXPECTED_FIXTURE_ACCOUNTING'
    )

    return {
        'schema':SCHEMA,
        'status':'PASS_SYNTHETIC_SOFTWARE_ONLY',
        'cases':cases,
        'scenarios':4,
        'converted_gaussian_prior_prefixes':prefixes,
        'independent_synthetic_segments':segments,
        'timestamp_gaps':gaps,
        'source_representation':
            'R95_INFORMATION_FORM_15D',
        'target_representation':
            'S6_SQUARE_ROOT_INFORMATION_PRIOR_15D',
        'source_space':LOCAL_SPACE,
        'target_space':LOCAL_SPACE,
        's6_nonlinear_node_binding_authorized':False,
        'r95_gaussian_backend_merged_into_s6':False,
        'new_nonlinear_pose_factors_executed':False,
        'recorded_sensor_factors_authorized':False,
        'independent_physical_frame_alignment':False,
        'physical_clock_verified':False,
        'physical_extrinsics_verified':False,
        'health_training_authorized':False,
        'ate_rpe_authorized':False,
        'confirmation_test_accessed':False,
        'raw_gt_or_rosbags_opened':False,
        'scientific_gates_closed':11,
    }

if __name__=='__main__':
    import sys

    result=execute()

    with open(
        sys.argv[1],'x',encoding='utf-8'
    ) as f:
        f.write(canonical(result).decode())

    print('R101_GAUSSIAN_TO_SQUARE_ROOT_ADAPTER=PASS')
    print('R101_SYNTHETIC_SCENARIOS=4')
    print('R101_CONVERTED_PRIORS=16')
    print('R101_INDEPENDENT_SEGMENTS=5')
    print('R101_GAP_RESET=PASS')
    print('R101_DIRECT_S6_NONLINEAR_BINDING=DENIED')
    print('R101_REAL_SENSOR_FACTORS=DENIED')
