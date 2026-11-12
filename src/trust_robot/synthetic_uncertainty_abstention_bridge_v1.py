"""Synthetic descriptive comparison, abstention, and common-mode blind spot.

Consumes A46-1/2RR manufactured factor reports; no learned health, fitted
thresholds, physical clocks, covariance calibration, source blame or control.
"""
from __future__ import annotations
import json
import math

SCHEMA='TRUST_ROBOT_R135_A46_3_UNCERTAINTY_ABSTENTION_V1'
METRICS=('camera_vs_lidar_translation_m','camera_vs_imu_translation_m','lidar_vs_imu_translation_m')
NUMERIC_EQUALITY_TOL=1e-9  # Numerical identity only; NOT a health/fault threshold.
EXPECTED=(('baseline',13),('camera_only',13),('lidar_only',13),('joint_common_mode',13),('joint_opposing',13),('dropout_and_camera',13),('baseline',31),('joint_common_mode',31))

class EvidenceDenied(ValueError): pass

def canonical(x):
    return (json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()

def require(ok,reason):
    if not ok: raise EvidenceDenied(reason)

def triad_values(row):
    require(type(row) is dict,'Invalid triad')
    require(row.get('physical_threshold_selected') is False and row.get('physical_sensor_uncertainty_calibrated') is False,'Unexpected physical calibration')
    v={}
    for key in METRICS:
        x=row.get(key)
        require(type(x) is float and math.isfinite(x) and x>=0,'Unqualified synthetic residual '+key)
        v[key]=x
    return v

def evaluate(report,reference):
    require(type(report) is dict and report.get('schema')=='TRUST_ROBOT_R135_A46_2_TRI_MODAL_CONSISTENCY_LIMITS_V1','Wrong tri-modal report')
    require(type(reference) is dict and reference.get('schema')=='TRUST_ROBOT_R135_A46_1_JOINT_FAULT_IDENTIFIABILITY_V1','Wrong joint-fault report')
    for obj in (report,reference):
        require(obj.get('real_factor_admission')=='DENIED' and obj.get('robot_actuation')=='DENIED','Physical gate changed')
    require(report.get('faulty_source_identified') is False and report.get('calibrated_health_probabilities_available') is False and report.get('third_modality_is_not_trusted_physical_reference') is True and report.get('real_sensor_data_accessed') is False,'Health or data provenance changed')
    require(reference.get('physical_sensor_source_attribution')=='UNRESOLVED' and reference.get('calibrated_health_probability_available') is False and reference.get('actual_sensor_data_accessed') is False,'Joint-fault scientific boundaries changed')
    rows=report.get('eight_manufactured_factor_cases')
    refrows=reference.get('cases')
    require(type(rows) is list and type(refrows) is list and len(rows)==len(refrows)==8,'Wrong synthetic design coverage')
    by={};prior={}
    for row in rows:
        require(type(row) is dict and type(row.get('scenario')) is str and type(row.get('seed')) is int,'Bad scenario identity')
        k=(row['scenario'],row['seed'])
        require(k in EXPECTED and k not in by,'Duplicate/unlisted tri-modal case')
        require(row.get('manufactured_relative_pose_edge')==[0,1] and row.get('imu_proxy_derived_from_samples')==[0,1] and row.get('imu_proxy_is_independent_physical_reference') is False,'Unqualified IMU source')
        require(row.get('known_scripted_fault_is_detected_source') is False and row.get('physical_responsible_modality')=='UNRESOLVED','Source attribution changed')
        require(row.get('real_factor_admission')=='DENIED' and row.get('robot_actuation')=='DENIED','Case physical gates changed')
        holds=row.get('known_lidar_hold_windows')
        require(holds==([2,3] if k[0]=='dropout_and_camera' else []),'Unexpected dropout ownership')
        vals=triad_values(row.get('triad'))
        by[k]=(vals,holds,row)
    for row in refrows:
        require(type(row) is dict and type(row.get('scenario')) is str and type(row.get('seed')) is int,'Bad joint-case identity')
        k=(row['scenario'],row['seed'])
        require(k in EXPECTED and k not in prior,'Duplicate/unlisted joint case')
        prior[k]=row
    require(set(by)==set(EXPECTED)==set(prior),'Incomplete source coverage')
    for key in EXPECTED:
        v,holds,row=by[key];r=prior[key]
        require(v[METRICS[0]]==r['pair_translation_gap_m'] and row['lidar_factor_count']==r['lidar_factors'] and holds==r['lidar_drop_shadow_windows'],'A46-1/2RR source disagreement')
    cases=[]
    for key in EXPECTED:
        name,seed=key
        value,holds,_=by[key]
        baseline=by['baseline',seed][0]
        delta={k:round(value[k]-baseline[k],12) for k in METRICS}
        changed={k:('CHANGED_SYNTHETIC_ONLY' if abs(delta[k])>NUMERIC_EQUALITY_TOL else 'UNCHANGED_SYNTHETIC_ONLY') for k in METRICS}
        cases.append({
            'scenario':name,'seed':seed,
            'relative_to_matched_seed_baseline_m':delta,
            'pairwise_contrast':changed,
            'manufactured_lidar_availability_shadow':('HOLD_MISSING_LIDAR_ENDPOINT' if holds else 'NO_KNOWN_ENDPOINT_DROPOUT'),
            'held_windows':holds,
            'uncertainty_decision':'ABSTAIN_UNCALIBRATED_REAL_HEALTH',
            'factor_weight_update_authorized':False,
            'physical_source_attribution':'UNRESOLVED'
        })
    indexed={(x['scenario'],x['seed']):x for x in cases}
    for seed in (13,31):
        c=indexed['joint_common_mode',seed]['pairwise_contrast']
        require(c[METRICS[0]]=='UNCHANGED_SYNTHETIC_ONLY' and c[METRICS[1]]=='CHANGED_SYNTHETIC_ONLY' and c[METRICS[2]]=='CHANGED_SYNTHETIC_ONLY','Common mode with fixed third proxy not reproduced')
    shared=report.get('all_three_shared_shift_diagnostic_counterexamples')
    require(type(shared) is list and len(shared)==2 and {x.get('seed') for x in shared}=={13,31},'Missing all-three proxy counterexamples')
    for s in shared:
        require(s.get('translation_pairwise_metrics_unchanged') is True and s.get('imu_proxy_shift_is_raw_imu_corruption') is False and s.get('physical_failure_attribution')=='UNRESOLVED','Invalid all-three counterexample scope')
        require(all(type(s.get('delta_translation_metrics_m',{}).get(k)) is float and abs(s['delta_translation_metrics_m'][k])<=NUMERIC_EQUALITY_TOL for k in METRICS),'Shared translation gauge not reproduced')
    return {
        'schema':SCHEMA,
        'synthetic_case_count':len(cases),'cases':cases,
        'all_three_common_translation_gauge_examples':len(shared),
        'common_mode_pairwise_invariance':'DEMONSTRATED_SYNTHETICALLY',
        'independent_physical_reference_available':False,
        'calibrated_reliability_probability_available':False,
        'operational_factor_weight_updates':False,
        'real_health_classification':'ABSTAIN',
        'physical_culprit':'UNRESOLVED',
        'real_factor_admission':'DENIED',
        'robot_actuation':'DENIED',
    }
