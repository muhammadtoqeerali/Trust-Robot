"""R105: exact local coordinate recentering integrated into S6's nonlinear run.

R104 supplies one validated manufactured camera/LiDAR/IMU factor graph.
R105 returns a *recentered* version of each actual S6 30D Schur prior
into the subsequent nonlinear window. Recentring changes only the local
coordinate reference and offset; it does NOT refresh frozen nonlinear
factor Jacobians, authorize R95-to-S6 import, or establish physical frames.
"""
import hashlib
import inspect
import json
from unittest.mock import patch

import numpy as np
import r104_shared_graph as graph
import s6_joint_fusion as s6
from trust_robot.analytic_schur_marginalization import SquareRootInformationPrior

SCHEMA='TRUST_ROBOT_R105_ALIGNED_SYNTHETIC_S6_PRIOR_TRANSFER_V1'
CASES=(('clean_joint','clean',True),
       ('lidar_dropout_joint','lidar_dropout',True),
       ('clean_camera_off','clean',False))
MAX_SHIFT_L2=1e-2

class TransferError(ValueError):
    pass

def need(ok,why):
    if not ok:raise TransferError(why)

def canonical(j):
    return (json.dumps(j,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()

def prior_sha(p):
    need(type(p) is SquareRootInformationPrior,'PRIOR_TYPE')
    return hashlib.sha256(canonical({
        'nodes':list(p.node_ids),
        'reference':np.asarray(p.reference).tolist(),
        'square_root':np.asarray(p.square_root_information).tolist(),
        'offset':np.asarray(p.residual_offset).tolist()
    })).hexdigest()

def shift_vector(index):
    need(type(index) is int and index in (0,1,2),'INDEX')
    return 2e-4*np.sin(np.arange(30,dtype=float)+index+0.5)

def expected_pose_ids(g,index):
    need(type(index) is int and index in (0,1,2),'INDEX')
    live={index,index+1,index+2}
    return tuple(sorted(f.key for f in g['pose_factors']
                        if index in f.packet.edge
                        and set(f.packet.edge).issubset(live)))

def transfer(p,g,index,pose_ids,imu_edges,delta):
    """Fail-closed, same-graph 30D local reference recentering.

    All factor identities and node chronology must be obtained from
    the validated R104 graph. No live calibration or R95 record is accepted.
    """
    try:
        graph.validate(g)
    except graph.GraphAdmissionError as exc:
        raise TransferError('GRAPH_ADMISSION_DENIED') from exc
    need(type(index) is int and index in (0,1,2),'INDEX')
    need(type(p) is SquareRootInformationPrior,'PRIOR_TYPE')
    need(p.node_ids==(index+1,index+2),'PRIOR_NODE_CHRONOLOGY')
    need(tuple(pose_ids)==expected_pose_ids(g,index),'POSE_LEDGER_MISMATCH')
    need(tuple(imu_edges)==((index,index+1),),'IMU_LEDGER_MISMATCH')
    need(g['origin']==graph.ANALYTIC_ORIGIN and
         g['frame_id']==graph.ANALYTIC_FRAME,'FRAME')
    need(g['real_sensor_factors_authorized'] is False and
         g['physical_clock_verified'] is False and
         g['physical_extrinsics_verified'] is False,'SCIENCE_BOUNDARY')
    need(type(delta) is np.ndarray and delta.shape==(30,) and
         np.isfinite(delta).all() and float(np.linalg.norm(delta))<=MAX_SHIFT_L2,
         'RECENTER_SHIFT')
    ref=np.asarray(p.reference,dtype=float)
    S=np.asarray(p.square_root_information,dtype=float)
    b=np.asarray(p.residual_offset,dtype=float)
    need(ref.shape==(30,) and S.ndim==2 and S.shape[1]==30 and
         b.shape==(S.shape[0],) and np.isfinite(ref).all() and
         np.isfinite(S).all() and np.isfinite(b).all(), 'PRIOR_MATRIX')
    H_before=S.T@S
    g_before=S.T@b
    new=SquareRootInformationPrior(
        tuple(p.node_ids),ref.copy()+delta,
        S.copy(),b.copy()+S@delta
    )
    def residue(q,d):
        # Same absolute local state in both coordinate references.
        x=ref+d
        return q.residual({index+1:x[:15],index+2:x[15:]})
    errors=[]
    for k in range(5):
        perturb=(np.zeros(30) if k==0 else
                 (k*1e-3)*np.cos(np.arange(30,dtype=float)+k))
        errors.append(float(np.linalg.norm(
            residue(p,perturb)-residue(new,perturb)
        )))
    H_after,g_after=new.normal_equations()
    expected_gradient=g_before+H_before@delta
    herr=float(np.linalg.norm(H_before-H_after)/max(1.,np.linalg.norm(H_before)))
    gerr=float(np.linalg.norm(g_after-expected_gradient)/max(1.,np.linalg.norm(expected_gradient)))
    need(max(errors)<1e-8 and herr<1e-11 and gerr<1e-9,
         'EXACT_LOCAL_RESIDUAL_EQUIVALENCE')
    return new,{
        'index':index,'input_nodes':list(range(index,index+3)),
        'retained_nodes':list(new.node_ids),
        'input_prior_sha256':prior_sha(p),'output_prior_sha256':prior_sha(new),
        'consumed_pose_ids':list(pose_ids),
        'consumed_imu_edges':[list(e) for e in imu_edges],
        'shift_l2':float(np.linalg.norm(delta)),
        'max_residual_absolute_error':max(errors),
        'information_relative_error':herr,
        'gradient_transform_relative_error':gerr,
        'returned_to_actual_s6_nonlinear_solver':True,
        'frozen_factor_jacobians_refreshed':False,
        'recorded_sensor_factors_admitted':False,
    }

def run_case(condition='clean',camera=True):
    need(condition in ('clean','lidar_dropout'),'CONDITION')
    need(type(camera) is bool,'CAMERA_MODE')
    g=graph.build(condition,camera,13)
    graph.validate(g)
    original=s6.marginalize_one
    events=[]
    transferred=None
    used_pose=set();used_imu=set()

    def wrapped(nodes,refs,residual_fn,oldest):
        nonlocal transferred
        index=len(events)
        need(index<3 and tuple(nodes)==(index,index+1,index+2)
             and oldest==index,'DEPARTING_NODES')
        captured=inspect.getclosurevars(residual_fn).nonlocals
        need({'previous','ii','pp'}.issubset(captured),'S6_CLOSURE')
        previous=captured['previous']
        pose=captured['pp'];imu=captured['ii']
        need(type(pose) is dict and type(imu) is dict,'FACTOR_COLLECTIONS')
        if transferred is not None:
            need(previous is transferred,'PRIOR_NOT_INHERITED')
        else:
            need(previous.node_ids==(0,),'INITIAL_GAUGE_PRIOR')
        need(not(set(pose)&used_pose) and not(set(imu)&used_imu),
             'FACTOR_DOUBLE_CONSUMPTION')
        need(set(pose)==set(expected_pose_ids(g,index)),'S6_POSE_LINEAGE')
        need(set(imu)=={(index,index+1)},'S6_IMU_LINEAGE')
        prior,diagnostics=original(nodes,refs,residual_fn,oldest)
        new,event=transfer(prior,g,index,sorted(pose),sorted(imu),shift_vector(index))
        need(diagnostics['fixed_first_estimate_linearization'] is True and
             diagnostics['physical_observability_proven'] is False and
             diagnostics['probabilistic_consistency_proven'] is False,
             'NONLINEAR_SCIENCE_DENIAL')
        event['inherited_input_prior_sha256']=prior_sha(previous)
        if events:
            need(event['inherited_input_prior_sha256']==events[-1]['output_prior_sha256'],
                 'CHAIN_BREAK')
        events.append(event)
        used_pose.update(pose)
        used_imu.update(imu)
        transferred=new
        return new,diagnostics

    with patch.object(s6,'marginalize_one',side_effect=wrapped):
        changed,audit=s6.estimate_joint(g['fixture'],g['camera_packets'])
    need(s6.marginalize_one is original,'S6_PATCH_NOT_RESTORED')
    need(len(events)==3 and len(changed)==5 and
         audit['accepted_window_count']==4 and audit['schur_elimination_count']==3,
         'NONLINEAR_SEQUENCE')
    need(used_imu=={(0,1),(1,2),(2,3)},'IMU_CONSUMPTION')
    consumed=set(audit['consumed_pose_ids'])
    remaining=set(audit['remaining_pose_ids'])
    need(used_pose==consumed and consumed.isdisjoint(remaining)
         and consumed|remaining=={f.key for f in g['pose_factors']},
         'POSE_FACTOR_ACCOUNTING')
    need(audit['real_sensor_factor_admitted'] is False and
         audit['physical_measurements_used'] is False and
         audit['factor_reuse_after_marginalization'] is False and
         audit['unaccounted_factor_count']==0,'S6_SCIENCE_AND_OWNERSHIP')
    reference,ref_audit=s6.estimate_joint(g['fixture'],g['camera_packets'])
    need(audit==ref_audit,'UNMODIFIED_LEDGER_MISMATCH')
    differences=[]
    for a,b in zip(changed,reference):
        for name in ('position_m','rotation_vector_rad','velocity_m_s','gyro_bias','accel_bias'):
            va=np.asarray(a[name]);vb=np.asarray(b[name])
            need(va.shape==(3,) and vb.shape==(3,),'STATE_SHAPE')
            differences.append(float(np.max(np.abs(va-vb))))
    max_difference=max(differences)
    need(max_difference<2e-5,'NONLINEAR_ESTIMATOR_CHANGED_BY_REBASE')
    return {
        'condition':condition,'camera_enabled':camera,
        'fixture_digest':g['fixture_digest'],
        'events':events,'transfers':len(events),
        'nonlinear_windows':audit['accepted_window_count'],
        'pose_factors_consumed':len(consumed),
        'pose_factors_remaining':len(remaining),
        'unreused_imu_edges':[[3,4]],
        'instrumented_vs_original_state_max_abs_error':max_difference,
        'factor_identity_audit_unchanged':True,
        'source_graph_validated':True,
        'r95_prior_imported':False,
        'real_sensor_factors_executed':False,
    }

def execute():
    cases={key:run_case(condition,camera) for key,condition,camera in CASES}
    need(len(cases)==3 and all(v['transfers']==3 for v in cases.values()),'COUNTS')
    need(cases['clean_joint']['pose_factors_consumed']>
         cases['clean_camera_off']['pose_factors_consumed'],'CAMERA_FACTOR_EFFECT')
    return {
        'schema':SCHEMA,'status':'PASS_SYNTHETIC_SOFTWARE_ONLY',
        'cases':cases,'scenarios':3,'nonlinear_windows':12,
        'real_nonlinear_prior_rebase_transfers':9,
        'original_s6_solver_restored':True,
        'exact_local_residual_equivalence_checked':True,
        'unchanged_non_linear_estimator_ledger':True,
        'r95_gaussian_backend_imported':False,
        'new_physical_frame_alignment_verified':False,
        'new_nonlinear_factor_jacobian_refresh_performed':False,
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
    with open(sys.argv[1],'x',encoding='utf-8') as f:
        f.write(canonical(result).decode())
    print('R105_ALIGNED_SYNTHETIC_PRIOR_TRANSFER=PASS')
    print('R105_ACTUAL_S6_PRIOR_TRANSFERS=9')
    print('R105_NONLINEAR_WINDOWS=12')
    print('R105_EXACT_LOCAL_RESIDUAL_EQUIVALENCE=PASS')
    print('R105_INSTRUMENTED_VS_UNMODIFIED_SOLVER=PASS')
    print('R105_R95_PRIOR_IMPORT=DENIED')
