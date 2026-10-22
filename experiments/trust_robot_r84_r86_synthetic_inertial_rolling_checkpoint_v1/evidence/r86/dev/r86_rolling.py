"""R86: controlled synthetic nonlinear rolling inertial state optimization.

Reuses R84 timestamp gap partitions and R85 covariance-whitened 15D
factors. Each segment has a new synthetic fixed anchor; a gap never
becomes a factor. Initial guesses are deliberately perturbed.

No independent truth, recorded sensor factors or physical calibration.
No Schur marginalization: the preceding fitted state is a fixed boundary.
"""
from __future__ import annotations
import hashlib
import json
import math

import numpy as np
from scipy.optimize import least_squares

import r84_gap_frontend as gap
import r85_fusion as fusion
from trust_robot.analytic_inertial_15d import G, as_rotation
from trust_robot.analytic_preintegrated_fusion import whitened_inertial_residual

SCHEMA='TRUST_ROBOT_R86_SYNTHETIC_GAP_AWARE_ROLLING_OPTIMIZER_V1'
MAX_NFEV=45
PERTURBATION=np.array([.04,-.03,.02, .008,-.005,.004, .04,-.03,.02,
                       .0001,-.00008,.00005, .002,-.001,.0015])

class RollingError(ValueError):
    pass

def need(v,message):
    if not v:
        raise RollingError(message)

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(value):
    return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()

def synthetic_anchor():
    """One declared manufactured gauge origin, independently per segment."""
    x=np.zeros(15,dtype=np.float64)
    x[:3]=[.1,-.2,.05]
    x[6:9]=[.25,-.08,.11]
    return x

def constructed_endpoint(xi,pre):
    """Propagate a manufactured factor-consistent endpoint, NOT truth."""
    need(xi.shape==(15,) and np.isfinite(xi).all(),'INVALID_BOUNDARY')
    Ri=as_rotation(xi)
    T=float(pre['total_dt'])
    xj=xi.copy()
    xj[:3]=xi[:3]+xi[6:9]*T+.5*G*T*T+Ri.apply(pre['delta_p'])
    xj[3:6]=(Ri*pre['delta_R']).as_rotvec()
    xj[6:9]=xi[6:9]+G*T+Ri.apply(pre['delta_v'])
    need(np.isfinite(xj).all(),'NONFINITE_SYNTHETIC_ENDPOINT')
    return xj

def solve_edge(xi,readings):
    """Optimize one 15D endpoint with preceding endpoint fixed.

    The factor is the ONLY optimization constraint; no independent
    accuracy is implied by the manufactured closure target.
    """
    need(len(readings)>0,'NO_READINGS')
    factor=fusion.make_factor(readings)
    pre=factor['preintegration']
    lower=factor['whitener']
    target=constructed_endpoint(xi,pre)
    initial=target+PERTURBATION
    def residual(x):
        return whitened_inertial_residual(xi,x,(pre,lower))
    before=float(np.linalg.norm(residual(initial)))
    fit=least_squares(residual,initial,method='trf',loss='linear',
                      max_nfev=MAX_NFEV,ftol=1e-11,xtol=1e-11,gtol=1e-11)
    after=float(np.linalg.norm(residual(fit.x)))
    rank=int(np.linalg.matrix_rank(fit.jac,tol=1e-7))
    endpoint_error=float(np.linalg.norm(fit.x-target))
    need(bool(fit.success) and np.isfinite(fit.x).all(),'OPTIMIZER_FAILURE')
    need(np.isfinite(fit.jac).all() and rank==15,'LOCAL_JACOBIAN_RANK')
    need(before>1e-3 and after<1e-6 and after<before/100.,'RESIDUAL_REDUCTION')
    need(endpoint_error<1e-4,'MANUFACTURED_ENDPOINT_RECOVERY')
    return fit.x.copy(),{
        'nfev':int(fit.nfev),
        'cost':float(fit.cost),
        'jacobian_rank':rank,
        'jacobian_columns':15,
        'initial_residual_norm':before,
        'final_residual_norm':after,
        'constructed_endpoint_state_error_norm':endpoint_error,
        'preintegration_time_s':float(pre['total_dt']),
        'full_correlated_15d_whitening_used':True,
        'constructed_endpoint_independent_reference':False,
        'previous_state_fixed_as_boundary':True,
        'schur_marginalization_applied':False,
        'real_measurement_factor_executable':False,
    }

def solve(packets):
    graph=fusion.build_graph(packets)
    need(graph['source']=='ANALYTIC_FIXTURE','UNVERIFIED_SOURCE')
    need(graph['real_factor_admission'] is False
         and graph['bridging_gap_factors']==0,'REAL_OR_GAP_FACTOR')
    groups,gap_count=gap.partition(packets)
    need(len(groups)==graph['safe_factor_count'],'GRAPH_COUNT')
    next_segment=-1
    previous_end=None
    state=None
    rows=[]
    reset_count=0
    for i,(start,end,readings) in enumerate(groups):
        edge=graph['edges'][i]
        need(edge['window_index']==i,'EDGE_INDEX')
        need(edge['synthetic_dt_s']>0
             and edge['real_factor_executable'] is False,'EDGE_DENIAL')
        segment=edge['segment_id']
        if state is None or start!=previous_end:
            need(segment==next_segment+1,'SEGMENT_RESTART_INDEX')
            next_segment=segment
            state=synthetic_anchor()
            reset_count+=1
            new_anchor=True
        else:
            need(segment==next_segment,'CROSS_SEGMENT_CONTINUITY')
            new_anchor=False
        need(edge['from_node']==f's{segment}:t{start}'
             and edge['to_node']==f's{segment}:t{end}','EDGE_ENDPOINT_IDENTITY')
        next_state,diagnostic=solve_edge(state,readings)
        need(abs(diagnostic['preintegration_time_s']
                 -(end-start)/1e9)<1e-10,'SEGMENT_DT')
        rows.append({
            'edge_index':i,
            'segment_id':segment,
            'from_node':edge['from_node'],
            'to_node':edge['to_node'],
            'synthetic_anchor_reset_here':new_anchor,
            'synthetic_start_ns':start,
            'synthetic_end_ns':end,
            'imu_sample_pairs':len(readings),
            **diagnostic,
        })
        state=next_state
        previous_end=end
    need(len(rows)==graph['safe_factor_count'],'WINDOW_TOTAL')
    need(reset_count==graph['segment_count']==gap_count+1,'SEGMENT_COUNT')
    need(sum(r['imu_sample_pairs'] for r in rows)
         +gap_count==len(packets)-1,'SAMPLE_ACCOUNTING')
    need(all(rows[i]['synthetic_end_ns']<=rows[i+1]['synthetic_start_ns']
             for i in range(len(rows)-1)),'EDGE_TIME_ORDER')
    return {
        'input_synthetic_packets':len(packets),
        'segments_with_independent_anchors':reset_count,
        'nonlinear_window_solves':len(rows),
        'rejected_gap_pairs':gap_count,
        'inertial_pairs_integrated':sum(r['imu_sample_pairs'] for r in rows),
        'max_final_whitened_residual':max(r['final_residual_norm'] for r in rows),
        'max_constructed_endpoint_recovery_error':max(
            r['constructed_endpoint_state_error_norm'] for r in rows),
        'windows':rows,
        'cross_gap_factor_count':0,
        'independent_gt_or_pose_used':False,
        'real_sensor_factors_admitted':False,
        'physical_clock_qualified':False,
        'schur_marginalization_implemented':False,
        'nonlinear_15d_optimizer_executed':True,
        'global_chain_estimated_across_gaps':False,
    }

def execute(r84,r85,r84sha,r85sha):
    need(r84.get('status')=='PASS_SOFTWARE_ONLY'
         and r85.get('status')=='PASS_SOFTWARE_ONLY','PRIOR_STATUS')
    need(r84.get('scientific_gates_closed')==11
         and r85.get('scientific_gates_closed')==11,'PRIOR_GATES')
    need(r85.get('real_estimator_optimization_executed') is False
         and r85.get('cross_gap_factors_constructed')==0,'PRIOR_SAFETY')
    cases=('continuous','single_gap','accel_injection','gyro_injection')
    output={}
    for name in cases:
        packets=gap.fixture(name)
        need(gap.analyze(packets)==r84['scenarios'][name],'R84_REPLAY:'+name)
        need(fusion.build_graph(packets)==r85['scenarios'][name],'R85_REPLAY:'+name)
        output[name]=solve(packets)
    need(output['continuous']['nonlinear_window_solves']==2
         and output['continuous']['segments_with_independent_anchors']==1
         and output['continuous']['inertial_pairs_integrated']==8,'CLEAN_SOLVER')
    need(output['single_gap']['nonlinear_window_solves']==2
         and output['single_gap']['segments_with_independent_anchors']==2
         and output['single_gap']['rejected_gap_pairs']==1
         and output['single_gap']['inertial_pairs_integrated']==7,'GAP_SOLVER')
    need(output['single_gap']['windows'][1]['synthetic_anchor_reset_here'] is True,
         'GAP_GAUGE_RESET')
    return {
        'schema':SCHEMA,
        'status':'PASS_SOFTWARE_ONLY',
        'r84_report_sha256':r84sha,
        'r85_report_sha256':r85sha,
        'scenario_count':4,
        'scenarios':output,
        'nonlinear_optimization_implemented':True,
        'optimizer_type':'SCIPY_LEAST_SQUARES_FIXED_PREVIOUS_15D_STATE',
        'full_correlated_covariance_whitening_reused':True,
        'synthetic_fixed_anchor_per_continuous_segment':True,
        'independent_reference_accuracy_claimed':False,
        'synthetic_constructed_endpoint_not_independent_gt':True,
        'probabilistic_schur_marginalization_implemented':False,
        'real_lidar_or_imu_factor_execution':False,
        'physical_clock_or_frame_qualified':False,
        'health_labels_or_probabilities_trained':False,
        'ate_rpe_computed':False,
        'raw_rosbags_or_gt_opened':False,
        'confirmation_test_accessed':False,
        'scientific_gates_closed':11,
    }

if __name__=='__main__':
    import sys
    from pathlib import Path
    r84path,r85path,out=map(Path,sys.argv[1:])
    b84=r84path.read_bytes();b85=r85path.read_bytes()
    report=execute(json.loads(b84),json.loads(b85),digest(b84),digest(b85))
    with (out/'r86_synthetic_rolling_optimization_v1.json').open('xb') as f:
        f.write(canonical(report))
    print('R86_SYNTHETIC_GAP_AWARE_ROLLING_OPTIMIZATION=PASS')
