"""A47-2: strict synthetic-only scan availability and scale-sensitivity shadow.

Selection here is an *explanatory manifest* for the frozen manufactured LiDAR
frontend, NOT estimator factor removal, health-driven selection, inferred
sensor reliability, real sensor admission or physical robot control.
"""
from __future__ import annotations
import hashlib
from itertools import product
import json
import math

SCHEMA='TRUST_ROBOT_R135_A47_2_FACTOR_SELECTION_ABSTENTION_SHADOW_V1'
PRIOR_SCHEMA='TRUST_ROBOT_R135_A47_1_NUMERIC_CAMERA_SCALE_SENSITIVITY_V1'
CONDITIONS=('clean','lidar_dropout')
SCALES=(0.5,1.0,2.0)
EXPECTED={
    (condition,enabled,mul)
    for condition in CONDITIONS
    for enabled in (False,True)
    for mul in ((1.0,2.0) if not enabled else SCALES)
}
EXPECTED_EDGES=((0,1),(0,2),(1,2),(1,3),(2,3),(2,4),(3,4))

class ShadowBoundary(ValueError):
    pass

def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()

def require(cond,reason):
    if not cond: raise ShadowBoundary(reason)

def guard(origin='ANALYTIC_FIXTURE'):
    require(type(origin) is str and origin=='ANALYTIC_FIXTURE','Physical or unknown source denied')
    from trust_robot.observation_aware_support_shadow_v1 import frozen_gates
    from trust_robot.factor_conditioning import (
        assert_factor_scale_execution_authorized,
        assert_information_rescaling_authorized,
        assert_covariance_inflation_authorized,
        FactorConditioningContractError,
    )
    x=frozen_gates()
    require(x['factor_conditioning']=='CLOSED' and x['auxiliary_consistency']=='CLOSED',
            'Frozen gates unexpectedly changed')
    for check in (
        assert_factor_scale_execution_authorized,
        assert_information_rescaling_authorized,
        assert_covariance_inflation_authorized,
    ):
        try: check()
        except FactorConditioningContractError: continue
        raise ShadowBoundary('Operational factor-conditioning gate unexpectedly open')

def mask_for(condition):
    require(type(condition) is str and condition in CONDITIONS,'Unlisted synthetic condition')
    flags=[True]*9
    if condition=='lidar_dropout':flags[4]=False
    return flags

def factor_ownership(mask):
    from trust_robot.factor_ownership_availability_bridge_v1 import model
    x=model(mask)
    edges=[tuple(p) for p in x['lidar_edge_keys']]
    require(len(edges)==len(set(edges)) and set(edges).issubset(EXPECTED_EDGES),
            'Unknown/reused manufactured LiDAR edge')
    require(x['lidar_factor_count']==len(edges),'Inconsistent factor cardinality')
    missing=[list(p) for p in EXPECTED_EDGES if p not in edges]
    return {
        'lidar_edge_keys_present':[list(x) for x in edges],
        'lidar_edge_keys_absent_due_to_known_scan_mask':missing,
        'lidar_factor_count':len(edges),
        'missing_node_frames':x['missing_node_frames'],
        'known_endpoint_shadow_holds':x['required_shadow_holds'],
        'selection_basis':'EXPLICIT_MANUFACTURED_SCAN_AVAILABILITY_ONLY',
        'unverified_sensor_health_used_for_selection':False,
        'runtime_factor_deletion_executed':False,
    }

def _valid_row(row):
    require(type(row) is dict,'Malformed scale experiment row')
    condition=row.get('condition')
    enabled=row.get('camera_enabled')
    scale=row.get('hypothetical_camera_residual_scale_multiplier')
    require(type(condition) is str and condition in CONDITIONS,'Unlisted condition')
    require(type(enabled) is bool and type(scale) is float,'Unqualified camera/scale fields')
    key=(condition,enabled,scale)
    require(key in EXPECTED,'Unlisted scale/camera condition')
    require(type(row.get('seed')) is int and row['seed']==13,'Unlisted manufactured seed')
    require(row.get('real_factor_admission')=='DENIED' and row.get('robot_actuation')=='DENIED',
            'Physical gate changed')
    require(row.get('physical_sensor_health_classification')=='ABSTAIN' and
            row.get('physical_responsible_modality')=='UNRESOLVED',
            'Unqualified health classification')
    require(row.get('factor_scale_execution_authorized') is False and
            row.get('physical_factor_scale_calibrated') is False and
            row.get('numerical_scale_tuning_is_health_inference') is False,
            'Real factor weighting or calibrated scales claimed')
    require(type(row.get('estimated_trajectory_sha256')) is str and
            len(row['estimated_trajectory_sha256'])==64 and
            set(row['estimated_trajectory_sha256']).issubset(set('0123456789abcdef')),
            'Missing immutable synthetic trajectory fingerprint')
    scales=row.get('numerical_camera_residual_scales_m_rad')
    require(type(scales) is list and len(scales)==2 and
            all(type(x) is float and math.isfinite(x) for x in scales) and
            math.isclose(scales[0],0.03*scale,abs_tol=1e-12,rel_tol=0) and
            math.isclose(scales[1],0.04*scale,abs_tol=1e-12,rel_tol=0),
            'Unrecognized fixed synthetic residual scales')
    p=row.get('final_synthetic_position_m')
    require(type(p) is list and len(p)==3 and all(type(x) is float and math.isfinite(x) for x in p),
            'Invalid numerical solver output')
    require(row.get('numerical_solver_accepted_windows')==4 and
            type(row['numerical_solver_accepted_windows']) is int,
            'Unexpected frozen window chronology')
    ownership=factor_ownership(mask_for(condition))
    require(row.get('camera_factor_count')==(2 if enabled else 0) and
            type(row['camera_factor_count']) is int and
            row.get('lidar_factor_count')==ownership['lidar_factor_count'] and
            type(row['lidar_factor_count']) is int and
            row.get('missing_lidar_shadow_windows')==ownership['known_endpoint_shadow_holds'],
            'Front-end factor count or dropout holds mismatch')
    return key,ownership

def evaluate(report,origin='ANALYTIC_FIXTURE'):
    guard(origin)
    require(type(report) is dict and report.get('schema')==PRIOR_SCHEMA,'Wrong A47-1 report origin')
    require(report.get('case_count')==10 and type(report['case_count']) is int,'Wrong synthetic matrix size')
    require(report.get('camera_disabled_controls_invariant') is True,'Negative control invalid')
    require(report.get('uncertainty_decision')=='ABSTAIN_UNCALIBRATED_REAL_HEALTH','Improper health decision')
    require(report.get('operational_factor_selection_executed') is False and
            report.get('operational_factor_weighting_executed') is False and
            report.get('physical_calibration_established') is False and
            report.get('real_factor_admission')=='DENIED' and
            report.get('robot_actuation')=='DENIED',
            'Operational execution or physical calibration claimed')
    rows=report.get('cases')
    require(type(rows) is list and len(rows)==10,'Wrong case coverage')
    index={}; ownerships={}
    for row in rows:
        key,ownership=_valid_row(row)
        require(key not in index,'Duplicate synthetic case')
        index[key]=row;ownerships[key]=ownership
    require(set(index)==EXPECTED,'Missing synthetic design cases')
    results=[]; sensitivity={}
    declared=report.get('numerical_scale_sensitivity')
    require(type(declared) is list and len(declared)==6,'Missing numeric-sensitivity entries')
    for x in declared:
        require(type(x) is dict,'Malformed numeric-sensitivity entry')
        condition=x.get('condition');mul=x.get('multiplier')
        require(type(condition) is str and condition in CONDITIONS and
                type(mul) is float and mul in SCALES,'Unlisted sensitivity axis')
        k=(condition,mul)
        require(k not in sensitivity,'Duplicated sensitivity entry')
        val=x.get('synthetic_final_position_gap_to_one_x_m')
        require(type(val) is float and math.isfinite(val) and val>=0 and
                x.get('trajectory_quality_or_health_inferred') is False,
                'Misleading sensitivity evidence')
        actual=round(math.dist(
            index[condition,True,1.0]['final_synthetic_position_m'],
            index[condition,True,mul]['final_synthetic_position_m']),12)
        require(abs(actual-val)<=1e-12,'Numeric sensitivity disagrees with solver output')
        sensitivity[k]=val
    require(set(sensitivity)=={(c,s) for c in CONDITIONS for s in SCALES},'Incomplete scale grid')
    for condition in CONDITIONS:
        require(sensitivity[condition,1.0]==0.0,'Baseline contrast not zero')
        for m in (0.5,2.0):
            require(sensitivity[condition,m]>1e-9,
                    'Expected manufactured numeric scale sensitivity disappeared')
        off1=index[condition,False,1.0];off2=index[condition,False,2.0]
        require(off1['estimated_trajectory_sha256']==off2['estimated_trajectory_sha256'],
                'Camera-disabled scale negative-control mismatch')
    for condition in CONDITIONS:
        for enabled,multipliers in ((True,SCALES),(False,(1.0,2.0))):
            for mul in multipliers:
                key=(condition,enabled,mul); row=index[key]; ownership=ownerships[key]
                results.append({
                    'condition':condition,
                    'camera_enabled_for_manufactured_solver':enabled,
                    'hypothetical_camera_scale_multiplier':mul,
                    'camera_factor_count_in_prior_solve':row['camera_factor_count'],
                    'lidar_factor_count_in_prior_solve':row['lidar_factor_count'],
                    'known_scan_availability_factor_ownership':ownership,
                    'synthetic_final_position_gap_to_1x_m':(
                        sensitivity[condition,mul] if enabled else None),
                    'camera_factor_health_admission':'NOT_EVALUATED',
                    'real_sensor_health':'ABSTAIN_UNCALIBRATED',
                    'source_attribution':'UNRESOLVED',
                    'health_driven_factor_selection':'NOT_AUTHORIZED',
                    'health_driven_factor_weighting':'NOT_AUTHORIZED',
                    'runtime_solver_reexecuted':False,
                    'physical_factor_admission':'DENIED',
                })
    return {
        'schema':SCHEMA,
        'case_count':len(results),
        'cases':results,
        'all_32_synthetic_availability_masks_audited':False,
        'real_health_inference':'ABSTAIN',
        'real_factor_admission':'DENIED',
        'physical_robot_actuation':'DENIED',
        'operational_factor_weighting_executed':False,
        'operational_factor_selection_executed':False,
        'private_numerical_sensitivity_reused_without_new_solver':True,
    }

def all_32_masks():
    guard()
    results=[]
    from trust_robot.factor_ownership_availability_bridge_v1 import FRAMES
    require(tuple(FRAMES)==(0,2,4,6,8),'Frozen frame chronology changed')
    for combination in product((False,True),repeat=5):
        mask=[True]*9
        for frame,present in zip(FRAMES,combination):mask[frame]=present
        ownership=factor_ownership(mask)
        expected_holds=[j for j in range(1,5) if not (mask[FRAMES[j-1]] and mask[FRAMES[j]])]
        require(ownership['known_endpoint_shadow_holds']==expected_holds,
                'Availability-derived shadow inconsistency')
        results.append({
            'node_scan_available':[bool(x) for x in combination],
            'lidar_factor_count':ownership['lidar_factor_count'],
            'known_endpoint_shadow_holds':ownership['known_endpoint_shadow_holds'],
            'real_health_inference':'ABSTAIN',
            'operational_factor_deletion_executed':False,
        })
    require(len(results)==32 and len({tuple(x['node_scan_available']) for x in results})==32,
            'Incomplete 32-mask coverage')
    require({x['lidar_factor_count'] for x in results}=={0,1,2,3,4,5,7},
            'Unexpected frozen graph factor-count distribution')
    return results

def execute(report,origin='ANALYTIC_FIXTURE'):
    result=evaluate(report,origin)
    sweep=all_32_masks()
    result['all_32_synthetic_availability_masks_audited']=True
    result['availability_mask_count']=len(sweep)
    result['availability_sweep']=sweep
    require(result['real_factor_admission']=='DENIED' and
            result['operational_factor_selection_executed'] is False,
            'Forbidden operational execution')
    return result
