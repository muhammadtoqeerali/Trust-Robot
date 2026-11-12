"""Fixed-point camera Jacobian information identity in manufactured 15D states.

Numeric camera residual scales are NOT measured covariance, learned health,
empirical reliability or authorization for physical factor weighting.
This is a local camera-only 3D translation-Jacobian subblock audit, NOT a
full 15D posterior covariance, multi-sensor information sum, or accuracy score.
"""
from __future__ import annotations
from unittest.mock import patch
import hashlib,json,math
import numpy as np

SCHEMA='TRUST_ROBOT_R135_A48_1_SYNTHETIC_CAMERA_INFORMATION_SCALING_V1'
SCALES=(0.5,1.0,2.0)
CONDITIONS=('clean','lidar_dropout')
SEEDS=(13,31)
EDGES=((0,1),(2,3))
STEP=1e-6  # Finite-difference step for fixed synthetic Jacobian ONLY.

class Boundary(ValueError): pass

def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()

def guard(origin='ANALYTIC_FIXTURE'):
    if type(origin) is not str or origin!='ANALYTIC_FIXTURE':
        raise Boundary('Recorded/live/unknown input denied')
    from trust_robot.observation_aware_support_shadow_v1 import frozen_gates
    from trust_robot.factor_conditioning import (
        assert_factor_scale_execution_authorized,
        assert_information_rescaling_authorized,
        assert_covariance_inflation_authorized,
        FactorConditioningContractError,
    )
    from trust_robot.observation_aware_support_shadow_v1 import ShadowDenied
    try:
        gates=frozen_gates()
    except ShadowDenied as exc:
        raise Boundary('Frozen scientific gate unexpectedly opened') from exc
    if gates['factor_conditioning']!='CLOSED' or gates['auxiliary_consistency']!='CLOSED':
        raise Boundary('Scientific gates changed')
    for fn in (assert_factor_scale_execution_authorized,assert_information_rescaling_authorized,assert_covariance_inflation_authorized):
        try: fn()
        except FactorConditioningContractError: continue
        raise Boundary('Physical factor conditioning unexpectedly authorized')

def evaluate(condition,seed,edge,multiplier,origin='ANALYTIC_FIXTURE'):
    guard(origin)
    if (type(condition) is not str or condition not in CONDITIONS or
        type(seed) is not int or seed not in SEEDS or
        type(edge) is not tuple or edge not in EDGES or
        type(multiplier) is not float or multiplier not in SCALES):
        raise Boundary('Unlisted synthetic information design')
    from trust_robot.analytic_inertial_15d import make_fixture
    from trust_robot.analytic_preintegrated_fusion import NODE_FRAMES,make_factors
    from trust_robot.analytic_three_modality_bridge import manufactured_camera_packets
    from trust_robot.analytic_separated_modalities import camera_factor_map
    from trust_robot import analytic_separated_modalities as sep
    from trust_robot.factor_ownership_availability_bridge_v1 import model
    if tuple(NODE_FRAMES)!=(0,2,4,6,8): raise Boundary('Frame chronology changed')
    original_pos=sep.CAMERA_POSITION_SCALE_M
    original_rot=sep.CAMERA_ROTATION_SCALE_RAD
    if (not math.isclose(original_pos,0.03,abs_tol=1e-15) or
        not math.isclose(original_rot,0.04,abs_tol=1e-15)):
        raise Boundary('Development scales changed')
    fixture,truth=make_fixture(condition)
    _,lidar,counts=make_factors(fixture)
    ownership=model(fixture['available'])
    if (len(lidar)!=ownership['lidar_factor_count'] or
        counts['imu_samples_reused'] is not False or
        ownership['required_shadow_holds']!=([2,3] if condition=='lidar_dropout' else [])):
        raise Boundary('Manufactured LiDAR factor ownership changed')
    packets=manufactured_camera_packets(truth,seed=seed)
    camera=camera_factor_map(packets)
    if set(camera)!=set(EDGES) or any(x.origin!='ANALYTIC_FIXTURE' or x.modality!='camera' for x in camera.values()):
        raise Boundary('Manufactured camera factor provenance changed')
    i,j=edge
    previous=np.asarray(truth[NODE_FRAMES[i]],dtype=float).copy()
    current=np.asarray(truth[NODE_FRAMES[j]],dtype=float).copy()
    measurement=camera[edge].measurement
    if previous.shape!=(15,) or current.shape!=(15,): raise Boundary('Unexpected synthetic 15D state')
    with patch.object(sep,'CAMERA_POSITION_SCALE_M',original_pos*multiplier), \
         patch.object(sep,'CAMERA_ROTATION_SCALE_RAD',original_rot*multiplier):
        residual=np.asarray(sep.camera_residual(previous,current,measurement))
        J=np.empty((6,3),dtype=float)
        for k in range(3):
            plus=current.copy(); minus=current.copy()
            plus[k]+=STEP;minus[k]-=STEP
            fp=np.asarray(sep.camera_residual(previous,plus,measurement))
            fm=np.asarray(sep.camera_residual(previous,minus,measurement))
            J[:,k]=(fp-fm)/(2*STEP)
    if sep.CAMERA_POSITION_SCALE_M!=original_pos or sep.CAMERA_ROTATION_SCALE_RAD!=original_rot:
        raise Boundary('Temporary camera scales not restored')
    info=J.T@J
    tr=float(np.trace(info))
    if (residual.shape!=(6,) or J.shape!=(6,3) or not np.isfinite(residual).all() or
        not np.isfinite(J).all() or not np.isfinite(info).all() or
        tr<=0 or np.max(np.abs(info-info.T))>1e-8):
        raise Boundary('Invalid fixed-point camera Jacobian information')
    return {
      'condition':condition,'seed':seed,'edge':list(edge),'scale_multiplier':multiplier,
      'camera_residual':residual.tolist(),'camera_translation_jacobian':J.tolist(),
      'camera_translation_information_trace':tr,
      'lidar_factors_unchanged':len(lidar),'lidar_shadow_holds_unchanged':ownership['required_shadow_holds'],
      'camera_source_id':camera[edge].measurement_id,
      'manufactured_truth_used_only_as_fixed_point':True,
      'full_15d_covariance_estimated':False,'physical_calibration_established':False,
      'operational_factor_weighting_executed':False,'real_factor_admission':'DENIED',
      'physical_sensor_health':'ABSTAIN','source_attribution':'UNRESOLVED',
    }

def execute():
    guard()
    rows=[evaluate(cond,seed,edge,mul) for cond in CONDITIONS for seed in SEEDS for edge in EDGES for mul in SCALES]
    if len(rows)!=24: raise Boundary('Missing numeric design')
    identity=[]
    for cond in CONDITIONS:
      for seed in SEEDS:
       for edge in EDGES:
        group={(r['scale_multiplier']):r for r in rows if r['condition']==cond and r['seed']==seed and r['edge']==list(edge)}
        if set(group)!=set(SCALES): raise Boundary('Missing multiplier group')
        base=group[1.0]
        r0=np.asarray(base['camera_residual']);j0=np.asarray(base['camera_translation_jacobian'])
        for mul in (0.5,2.0):
          row=group[mul]
          r=np.asarray(row['camera_residual']);j=np.asarray(row['camera_translation_jacobian'])
          ratio=row['camera_translation_information_trace']/base['camera_translation_information_trace']
          if (not np.allclose(r,r0/mul,rtol=1e-8,atol=1e-9) or
              not np.allclose(j,j0/mul,rtol=1e-6,atol=1e-7) or
              not math.isclose(ratio,1/(mul*mul),rel_tol=1e-6,abs_tol=1e-6)):
              raise Boundary('Numerical information scale identity failed')
          identity.append({'condition':cond,'seed':seed,'edge':list(edge),'multiplier':mul,'fixed_point_information_trace_ratio':round(ratio,9),'expected_analytic_ratio':1/(mul*mul)})
    from trust_robot.analytic_separated_modalities import camera_factor_map
    if camera_factor_map(())!={}: raise Boundary('Camera-off zero-factor control invalid')
    return {'schema':SCHEMA,'case_count':len(rows),'cases':rows,
            'comparison_count':len(identity),'information_scale_identities':identity,
            'camera_disabled_information_contribution_is_zero_by_factor_absence':True,
            'real_factor_admission':'DENIED','health_output':'ABSTAIN',
            'empirical_covariance_calibrated':False,'physical_accuracy_scored':False,
            'operational_factor_weighting_executed':False,'robot_actuation':'DENIED'}
