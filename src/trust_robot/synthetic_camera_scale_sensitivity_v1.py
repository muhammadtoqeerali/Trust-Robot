"""R135-A47-1 numerical scale sensitivity on existing separated 15D estimator.

The scalings are predeclared engineering perturbations, NOT health weights,
calibrated covariance, inferred reliability, an operational factor-selection
policy, or permission to run physical sensors or modify robot behavior.
"""
from __future__ import annotations
import hashlib, json, math
from unittest.mock import patch

SCHEMA='TRUST_ROBOT_R135_A47_1_NUMERIC_CAMERA_SCALE_SENSITIVITY_V1'
ORIGIN='ANALYTIC_FIXTURE'
MULTIPLIERS=(0.5, 1.0, 2.0)
CONDITIONS=('clean','lidar_dropout')
SEED=13
CASES=tuple(
    (condition, multiplier, enabled)
    for condition in CONDITIONS
    for enabled in (True,False)
    for multiplier in (MULTIPLIERS if enabled else (1.0,2.0))
)

class SensitivityBoundary(ValueError): pass

def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()

def sha(value): return hashlib.sha256(canonical(value)).hexdigest()

def guard(origin):
    if type(origin) is not str or origin!=ORIGIN:
        raise SensitivityBoundary('Physical, recorded or unknown input prohibited')
    from trust_robot.synthetic_joint_fault_identifiability_v1 import guard as published_guard
    published_guard(origin)
    from trust_robot.factor_conditioning import (
        assert_factor_scale_execution_authorized,
        assert_information_rescaling_authorized,
        assert_covariance_inflation_authorized,
        FactorConditioningContractError,
    )
    for call in (
        assert_factor_scale_execution_authorized,
        assert_information_rescaling_authorized,
        assert_covariance_inflation_authorized,
    ):
        try: call()
        except FactorConditioningContractError: continue
        raise SensitivityBoundary('Phase-8 operational conditioning gate unexpectedly open')

def run_case(condition, multiplier, camera_enabled=True, origin=ORIGIN):
    guard(origin)
    if (
        type(condition) is not str or condition not in CONDITIONS
        or type(multiplier) is not float or multiplier not in MULTIPLIERS
        or type(camera_enabled) is not bool
    ):
        raise SensitivityBoundary('Unlisted synthetic camera numerical configuration')

    from trust_robot.analytic_inertial_15d import make_fixture
    from trust_robot.analytic_preintegrated_fusion import make_factors,NODE_FRAMES
    from trust_robot.analytic_three_modality_bridge import manufactured_camera_packets
    from trust_robot.factor_ownership_availability_bridge_v1 import model
    from trust_robot import analytic_separated_modalities as sep

    if tuple(NODE_FRAMES)!=(0,2,4,6,8):
        raise SensitivityBoundary('Frozen analytic node schedule changed')

    pos=sep.CAMERA_POSITION_SCALE_M
    rot=sep.CAMERA_ROTATION_SCALE_RAD
    if (
        type(pos) is not float or type(rot) is not float
        or not math.isclose(pos,0.03,abs_tol=1e-15,rel_tol=0)
        or not math.isclose(rot,0.04,abs_tol=1e-15,rel_tol=0)
    ):
        raise SensitivityBoundary('Frozen development residual scales changed')

    fixture, manufactured_truth=make_fixture(condition)
    _,lidar,counts=make_factors(fixture)
    availability=model(fixture['available'])
    if (
        len(lidar)!=availability['lidar_factor_count']
        or counts['lidar_factor_count']!=len(lidar)
        or counts['imu_samples_reused'] is not False
    ):
        raise SensitivityBoundary('LiDAR factor ownership mismatch')

    packets=(
        manufactured_camera_packets(manufactured_truth,seed=SEED)
        if camera_enabled else ()
    )
    expected_camera=2 if camera_enabled else 0
    if len(packets)!=expected_camera or any(
        p.origin!=ORIGIN or p.modality!='camera' for p in packets
    ):
        raise SensitivityBoundary('Manufactured camera provenance changed')

    # Scoped mathematical experiment ONLY, never an operational call-site.
    with patch.object(sep,'CAMERA_POSITION_SCALE_M',pos*multiplier), \
         patch.object(sep,'CAMERA_ROTATION_SCALE_RAD',rot*multiplier):
        records,audit=sep.estimate_separated(fixture,packets)

    if sep.CAMERA_POSITION_SCALE_M!=pos or sep.CAMERA_ROTATION_SCALE_RAD!=rot:
        raise SensitivityBoundary('Numerical scale leaked outside bounded experiment')

    if not (
        len(records)==5
        and audit['camera_factor_count']==expected_camera
        and audit['lidar_factor_count']==len(lidar)
        and audit['imu_factor_count']==4
        and audit['accepted_window_count']==4
        and audit['schur_elimination_count']==3
        and audit['factor_reuse_after_marginalization'] is False
        and audit['unaccounted_factor_count']==0
        and audit['independent_source_residual_blocks'] is True
        and audit['same_edge_camera_and_lidar_supported'] is True
        and audit['real_sensor_factor_execution_authorized'] is False
        and audit['empirical_covariance_calibrated'] is False
        and audit['health_factor_conditioning_executed'] is False
    ):
        raise SensitivityBoundary('Separated 15D scientific/factor invariants violated')

    ids=[p.measurement_id for p in packets]
    owned=audit['consumed_camera_ids']+audit['remaining_camera_ids']
    if len(owned)!=len(set(owned)) or sorted(owned)!=sorted(ids):
        raise SensitivityBoundary('Synthetic camera source IDs lost or reused')
    lidarkeys=[tuple(x) for x in audit['consumed_lidar_keys']+audit['remaining_lidar_keys']]
    if len(lidarkeys)!=len(set(lidarkeys)) or set(lidarkeys)!=set(lidar):
        raise SensitivityBoundary('Synthetic LiDAR factors lost or reused')

    for w in audit['windows']:
        s=w['source_specific_support']
        if (
            s['real_sensor_noise_calibrated'] is not False
            or s['physical_observability_verified'] is not False
            or s['runtime_health_weighting_enabled'] is not False
        ):
            raise SensitivityBoundary('Unexpected physical sensor admission')

    final=records[-1]['position_m']
    if len(final)!=3 or not all(math.isfinite(float(z)) for z in final):
        raise SensitivityBoundary('Nonfinite final synthetic estimate')

    return {
        'condition':condition,
        'seed':SEED,
        'camera_enabled':camera_enabled,
        'hypothetical_camera_residual_scale_multiplier':multiplier,
        'numerical_camera_residual_scales_m_rad':[pos*multiplier,rot*multiplier],
        'estimated_trajectory_sha256':sha(records),
        'final_synthetic_position_m':[float(z) for z in final],
        'camera_factor_count':expected_camera,
        'lidar_factor_count':len(lidar),
        'missing_lidar_shadow_windows':availability['required_shadow_holds'],
        'numerical_solver_accepted_windows':audit['accepted_window_count'],
        'numerical_scale_tuning_is_health_inference':False,
        'factor_scale_execution_authorized':False,
        'physical_factor_scale_calibrated':False,
        'physical_sensor_health_classification':'ABSTAIN',
        'physical_responsible_modality':'UNRESOLVED',
        'real_factor_admission':'DENIED',
        'robot_actuation':'DENIED',
    }

def execute():
    guard(ORIGIN)
    rows=[run_case(*row) for row in CASES]
    assert len(rows)==10
    lookup={(r['condition'],r['camera_enabled'],r['hypothetical_camera_residual_scale_multiplier']):r for r in rows}
    if len(lookup)!=10: raise SensitivityBoundary('Duplicate matrix cases')
    outcomes=[]
    for condition in CONDITIONS:
        baseline=lookup[condition,True,1.0]['final_synthetic_position_m']
        for mul in MULTIPLIERS:
            case=lookup[condition,True,mul]
            gap=math.dist(baseline,case['final_synthetic_position_m'])
            if not math.isfinite(gap) or gap<0:
                raise SensitivityBoundary('Invalid manufactured numerical sensitivity gap')
            outcomes.append({
                'condition':condition,
                'multiplier':mul,
                'synthetic_final_position_gap_to_one_x_m':round(gap,12),
                'trajectory_quality_or_health_inferred':False,
            })
        off_1=lookup[condition,False,1.0]
        off_2=lookup[condition,False,2.0]
        if off_1['estimated_trajectory_sha256']!=off_2['estimated_trajectory_sha256']:
            raise SensitivityBoundary('Camera-disabled control changed under camera-only scale perturbation')
        if off_1['camera_factor_count']!=0 or off_2['camera_factor_count']!=0:
            raise SensitivityBoundary('Camera-disabled control has camera factors')
    return {
        'schema':SCHEMA,
        'case_count':len(rows),
        'cases':rows,
        'numerical_scale_sensitivity':outcomes,
        'camera_disabled_controls_invariant':True,
        'uncertainty_decision':'ABSTAIN_UNCALIBRATED_REAL_HEALTH',
        'operational_factor_selection_executed':False,
        'operational_factor_weighting_executed':False,
        'physical_calibration_established':False,
        'real_factor_admission':'DENIED',
        'robot_actuation':'DENIED',
    }
