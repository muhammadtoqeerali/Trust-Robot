"""R98 synthetic nonlinear S6 factor and Schur consistency audit.

Uses original S6 SE(3) relative-pose factors and nonlinear
optimization. Examines a separately relinearized local Gaussian
quadratic but does not relinearize an already eliminated factor
or claim nonlinear posterior equivalence.

Synthetic truth is used solely to manufacture camera packets;
it is never supplied to estimate_joint.
"""

import json
import numpy as np

from trust_robot.analytic_inertial_15d import (
    initial_state, make_fixture,
)
from trust_robot.analytic_preintegrated_fusion import (
    make_factors,
)
from trust_robot.analytic_three_modality_bridge import (
    manufactured_camera_packets,
)
from trust_robot.analytic_schur_marginalization import (
    finite_difference_linearization,
    marginalize_one,
    synthetic_initial_anchor,
)

from s6_joint_fusion import (
    assemble_joint,
    estimate_joint,
    selected_residuals,
    whitened_pose_residual,
)

SCHEMA='TRUST_ROBOT_R98_SYNTHETIC_NONLINEAR_JOINT_AUDIT_V1'
DIM=15

class R98Error(ValueError):
    pass

def need(ok,reason):
    if not ok:
        raise R98Error(reason)

def canonical(x):
    return (
        json.dumps(
            x,sort_keys=True,indent=2,allow_nan=False
        )+'\n'
    ).encode()

def state(row):
    fields=(
        'position_m',
        'rotation_vector_rad',
        'velocity_m_s',
        'gyro_bias',
        'accel_bias',
    )

    x=np.concatenate([
        np.asarray(row[k],dtype=float)
        for k in fields
    ])

    need(
        x.shape==(DIM,)
        and np.isfinite(x).all(),
        'INVALID_ESTIMATOR_STATE'
    )

    return x

def local_schur_check(fixture,factors,records):
    """Independently compare the locally frozen Schur equations."""

    imu,_,_=make_factors(fixture)

    nodes=(0,1,2)
    values={
        i:state(records[i])
        for i in nodes
    }

    prior=synthetic_initial_anchor(
        initial_state(),sigma=0.01
    )

    exiting_imu={
        (0,1):imu[(0,1)]
    }

    exiting_pose={
        f.key:f
        for f in factors
        if 0 in f.packet.edge
        and max(f.packet.edge)<=2
    }

    need(len(exiting_pose)>=2,'POSE_SUPPORT')

    modalities={
        f.packet.modality
        for f in exiting_pose.values()
    }

    need(
        modalities=={'camera','lidar'},
        'JOINT_NONLINEAR_SUPPORT'
    )

    def objective(mapping):
        return selected_residuals(
            mapping,prior,exiting_imu,exiting_pose
        )

    reference=np.concatenate([
        values[i] for i in nodes
    ])

    def flattened(flat):
        s={
            node:flat[k*DIM:(k+1)*DIM]
            for k,node in enumerate(nodes)
        }
        return objective(s)

    r0,J=finite_difference_linearization(
        flattened,reference
    )

    need(
        J.shape[1]==45
        and np.isfinite(J).all(),
        'LINEARIZATION'
    )

    H=J.T@J
    g=J.T@r0

    Hmm=H[:DIM,:DIM]
    Hmk=H[:DIM,DIM:]
    Hkm=H[DIM:,:DIM]
    Hkk=H[DIM:,DIM:]

    gm=g[:DIM]
    gk=g[DIM:]

    H_expected=Hkk-Hkm@np.linalg.solve(
        Hmm,Hmk
    )

    H_expected=0.5*(
        H_expected+H_expected.T
    )

    g_expected=gk-Hkm@np.linalg.solve(
        Hmm,gm
    )

    condensed,diagnostics=marginalize_one(
        nodes,values,objective,0
    )

    need(
        condensed.node_ids==(1,2),
        'RETAINED_PRIOR_NODES'
    )

    H_actual,g_actual=condensed.normal_equations()

    herr=float(
        np.linalg.norm(H_actual-H_expected)
        /max(1.,np.linalg.norm(H_expected))
    )

    gerr=float(
        np.linalg.norm(g_actual-g_expected)
        /max(1.,np.linalg.norm(g_expected))
    )

    need(
        herr<1e-6
        and gerr<1e-6,
        'INDEPENDENT_SCHUR_NORMAL_EQUATIONS'
    )

    # Compare relative energies: the eliminated-state
    # additive constant is not represented by the prior.
    delta=1e-5*np.sin(
        np.arange(30,dtype=float)+0.31
    )

    def reduced_batch_energy(d):
        old=-np.linalg.solve(
            Hmm,gm+Hmk@d
        )

        full=np.r_[old,d]

        return 0.5*float(
            np.linalg.norm(r0+J@full)**2
        )

    def prior_energy(d):
        shifted={
            1:values[1]+d[:DIM],
            2:values[2]+d[DIM:],
        }

        residual=condensed.residual(shifted)

        return 0.5*float(
            residual@residual
        )

    batch_delta=(
        reduced_batch_energy(delta)
        -reduced_batch_energy(np.zeros(30))
    )

    prior_delta=(
        prior_energy(delta)
        -prior_energy(np.zeros(30))
    )

    energy_error=abs(batch_delta-prior_delta)

    need(
        energy_error<1e-5,
        'SCHUR_REDUCED_ENERGY'
    )

    # Nonlinear-vs-frozen-local-linear approximation.
    # This is a diagnostic, not a permission to refresh
    # eliminated historical nonlinear factors.
    shift=1e-3*np.sin(
        np.arange(45,dtype=float)+0.17
    )

    actual_residual=flattened(
        reference+shift
    )

    local_prediction=r0+J@shift

    nonlinear_drift=float(
        np.linalg.norm(
            actual_residual-local_prediction
        )
    )

    need(
        np.isfinite(nonlinear_drift)
        and nonlinear_drift>=0,
        'NONLINEAR_DRIFT'
    )

    need(
        diagnostics['fixed_first_estimate_linearization']
        is True
        and diagnostics['physical_observability_proven']
        is False
        and diagnostics['probabilistic_consistency_proven']
        is False,
        'PRIOR_SCIENTIFIC_BOUNDARY'
    )

    return {
        'original_node_count':3,
        'eliminated_node':0,
        'retained_nodes':[1,2],
        'joint_departing_pose_factors':len(exiting_pose),
        'departing_imu_factors':len(exiting_imu),
        'information_relative_error':herr,
        'gradient_relative_error':gerr,
        'reduced_energy_difference_abs_error':energy_error,
        'nonlinear_vs_frozen_linear_residual_l2':
            nonlinear_drift,
        'original_nonlinear_factors_refreshed':False,
        'physical_observability_proven':False,
        'posterior_consistency_proven':False,
    }

def run_case(condition,seed=13,camera=True):
    need(
        condition in ('clean','lidar_dropout'),
        'INVALID_CONDITION'
    )

    need(
        type(seed) is int and 0<=seed<=100000,
        'INVALID_SEED'
    )

    need(type(camera) is bool,'INVALID_CAMERA_MODE')

    fixture,truth=make_fixture(condition)

    packets=(
        manufactured_camera_packets(truth,seed=seed)
        if camera else ()
    )

    imu,lidar,_=make_factors(fixture)
    factors=assemble_joint(lidar,packets)

    # Truth deliberately excluded from estimator call.
    records,audit=estimate_joint(
        fixture,packets
    )

    need(len(records)==5,'STATE_COUNT')
    values=[state(r) for r in records]

    need(
        audit['accepted_window_count']==4
        and audit['schur_elimination_count']==3,
        'NONLINEAR_FIXED_LAG'
    )

    need(
        len(imu)==4
        and audit['factor_reuse_after_marginalization']
        is False
        and audit['unaccounted_factor_count']==0,
        'OWNERSHIP'
    )

    ledger=audit['factor_ledger']

    ids=[x['measurement_id'] for x in ledger]

    need(
        len(ids)==len(set(ids))
        and set(ids)=={f.key for f in factors},
        'MEASUREMENT_IDENTITY'
    )

    consumed=set(audit['consumed_pose_ids'])
    remaining=set(audit['remaining_pose_ids'])

    need(
        consumed.isdisjoint(remaining)
        and consumed|remaining==set(ids),
        'CONSUMPTION_PARTITION'
    )

    for w in audit['windows']:
        need(
            w['accepted'] is True
            and w['rank']==w['state_dimension']
            and w['inertial_factor_count']>=1,
            'NONLINEAR_WINDOW_SUPPORT'
        )

    for f in factors:
        i,j=f.packet.edge

        residual=whitened_pose_residual(
            values[i],values[j],f
        )

        need(
            residual.shape==(6,)
            and np.isfinite(residual).all(),
            'TRUE_SE3_RESIDUAL'
        )

    need(
        audit['physical_measurements_used'] is False
        and audit['real_sensor_factor_admitted'] is False,
        'REAL_FACTOR_DENIED'
    )

    same_edge=audit[
        'same_edge_camera_lidar_count'
    ]

    if camera and condition=='clean':
        need(
            same_edge==2
            and audit['camera_factor_count']==2,
            'SAME_EDGE_MODALITIES'
        )

    if not camera:
        need(
            audit['camera_factor_count']==0
            and same_edge==0,
            'CAMERA_OFF'
        )

    return {
        'condition':condition,
        'camera_enabled':camera,
        'manufactured_camera_seed':(
            seed if camera else None
        ),
        'nonlinear_windows':4,
        'schur_marginalizations':3,
        'pose_factors':len(factors),
        'camera_factors':audit['camera_factor_count'],
        'lidar_factors':audit['lidar_factor_count'],
        'same_edge_camera_lidar':same_edge,
        'distinct_measurement_ids':len(ids),
        'consumed_factors':len(consumed),
        'remaining_factors':len(remaining),
        'fully_ranked_windows':4,
        'pose_residuals_evaluated':len(factors),
        'real_factor_executed':False,
    },(fixture,factors,records)

def execute():
    clean,details=run_case(
        'clean',13,True
    )

    dropout,_=run_case(
        'lidar_dropout',13,True
    )

    camera_off,_=run_case(
        'clean',13,False
    )

    need(
        dropout['lidar_factors']
        <clean['lidar_factors'],
        'DROPOUT_NOT_REPRESENTED'
    )

    need(
        camera_off['camera_factors']==0,
        'CAMERA_ABLATION'
    )

    local=local_schur_check(*details)

    return {
        'schema':SCHEMA,
        'status':'PASS_SYNTHETIC_SOFTWARE_ONLY',
        'cases':{
            'clean_joint':clean,
            'lidar_dropout_joint':dropout,
            'clean_camera_off':camera_off,
        },
        'local_nonlinear_schur_audit':local,
        'nonlinear_solver_cases':3,
        'nonlinear_windows_audited':12,
        'schur_marginalizations_reported':9,
        'distinct_se3_camera_lidar_factor_identities':True,
        'true_s6_nonlinear_se3_residuals_executed':True,
        'r95_gaussian_prior_merged_into_s6':False,
        'synthetic_truth_used_only_for_measurement_generation':True,
        'independent_ground_truth_scoring':False,
        'physical_capture_time_verified':False,
        'physical_extrinsics_verified':False,
        'real_sensor_factors_authorized':False,
        'health_training_authorized':False,
        'ate_rpe_authorized':False,
        'confirmation_test_accessed':False,
        'original_gt_or_rosbags_opened':False,
        'scientific_gates_closed':11,
    }

if __name__=='__main__':
    import sys

    result=execute()

    with open(
        sys.argv[1],'x',encoding='utf-8'
    ) as f:
        f.write(canonical(result).decode())

    print('R98_NONLINEAR_S6_SOLVER=PASS')
    print('R98_NONLINEAR_WINDOWS=12')
    print('R98_SCHUR_MARGINALIZATIONS=9')
    print('R98_LOCAL_INDEPENDENT_SCHUR=PASS')
    print('R98_FACTOR_OWNERSHIP=PASS')
    print('R98_RECORDED_SENSOR_FACTORS=DENIED')
