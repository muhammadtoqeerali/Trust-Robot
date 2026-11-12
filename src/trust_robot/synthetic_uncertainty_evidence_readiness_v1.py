"""Private A48-2 crosswalk; it does NOT calibrate real sensor uncertainties.

Published metadata and Phase-5/6/8 software contracts are the only inputs.
A repo document is a statement of missing evidence, not an independent witness.
"""
from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
import hashlib, json

SCHEMA='TRUST_ROBOT_R135_A48_2_PHYSICAL_UNCERTAINTY_READINESS_V1'
ORIGIN='REPOSITORY_METADATA_ONLY'
DOCS={
 'historical_synthetic_decision':'docs/audits/trust_robot/TRUST_ROBOT_R135_A21_EVIDENCE_DECISION_V1.md',
 'm2dgr_readiness':'docs/audits/trust_robot/TRUST_ROBOT_R135_A22_M2DGR_READINESS_V1.md',
 'prospective_requests':'docs/audits/trust_robot/TRUST_ROBOT_R135_A23_EVIDENCE_REQUEST_V1.md',
 'last_published_scale_shadow':'docs/audits/trust_robot/TRUST_ROBOT_R135_A47_3_CAMERA_SCALE_AND_FACTOR_SELECTION_SHADOW_V1.md',
 'probabilistic_calibration_contract':'docs/audits/trust_robot/TRUST_ROBOT_PHASE6_PROBABILISTIC_CALIBRATION_CONTRACT_V1.md',
}
CHECKS={
 'historical_synthetic_decision':('All 11 M2DGR admission gates remain CLOSED.',),
 'm2dgr_readiness':('- TRAIN: 22;','- VALIDATION_CALIBRATION: 7;','- CONFIRMATION_TEST: 7.'),
 'prospective_requests':('Thirteen evidence requests','All eleven original M2DGR admission gates'),
 'last_published_scale_shadow':('0.03 m and 0.04 rad','not physical localization error'),
 'probabilistic_calibration_contract':('It is not geometric sensor calibration','validation/calibration data only'),
}

class Boundary(ValueError): pass

def canonical(x):
    return (json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()

def require(value,reason):
    if not value: raise Boundary(reason)

def guard(origin=ORIGIN):
    require(type(origin) is str and origin==ORIGIN,'Physical/unknown origin refused')
    from trust_robot import multimodal_health_model as h
    from trust_robot import probabilistic_calibration as c
    from trust_robot import factor_conditioning as f
    tasks=(
      (h.assert_training_authorized,h.HealthModelInterfaceError),
      (h.assert_inference_authorized,h.HealthModelInterfaceError),
      (c.assert_calibration_execution_authorized,c.ProbabilisticCalibrationError),
      (c.assert_calibrated_output_authorized,c.ProbabilisticCalibrationError),
      (f.assert_factor_scale_execution_authorized,f.FactorConditioningContractError),
      (f.assert_information_rescaling_authorized,f.FactorConditioningContractError),
      (f.assert_covariance_inflation_authorized,f.FactorConditioningContractError),
    )
    for action,denial in tasks:
        try: action()
        except denial: continue
        raise Boundary('Closed training/inference/calibration/weighting gate unexpectedly opened')

def documents(repo):
    require(isinstance(repo,(str,Path)),'Repository root required')
    root=Path(repo)
    require(root.is_dir() and not root.is_symlink(),'Invalid repository root')
    result={}
    for label,relative in DOCS.items():
        path=root/relative
        require(path.is_file() and not path.is_symlink() and 0<path.stat().st_size<100000,
                'Missing or unsafe repository evidence: '+relative)
        blob=path.read_bytes()
        try: text=blob.decode('utf-8')
        except UnicodeError as ex: raise Boundary('Non-UTF-8 frozen evidence') from ex
        require(all(part in text for part in CHECKS[label]),
                'Frozen evidence expectation changed: '+label)
        result[label]={'path':relative,'sha256':hashlib.sha256(blob).hexdigest()}
    return result

def assess(repo,origin=ORIGIN):
    guard(origin)
    from trust_robot.multimodal_health_model import CURRENT_EVIDENCE_GATE
    from trust_robot.probabilistic_calibration import CURRENT_CALIBRATION_GATE
    from trust_robot.factor_conditioning import CURRENT_FACTOR_CONDITIONING_GATE
    h=asdict(CURRENT_EVIDENCE_GATE)
    c=asdict(CURRENT_CALIBRATION_GATE)
    f=asdict(CURRENT_FACTOR_CONDITIONING_GATE)
    require(all(h[x]==0 for x in (
        'accepted_baseline_nominality_source_count',
        'accepted_health_supervision_source_count','real_health_label_count')),
        'Accepted real health labels unexpectedly available')
    for key in ('classifier_training_authorized','health_inference_authorized',
                'confirmation_selection_authorized'):
        require(h[key] is False,'Phase5 authorization changed: '+key)
    require(h['confirmation_closed'] is True and h['physical_validation_deferred'] is True,
            'Phase5 physical confirmation gate changed')
    for key in ('phase5_empirical_health_model_complete','trained_health_model_available',
                'uncalibrated_health_model_outputs_available','admissible_health_labels_available',
                'validation_calibration_inputs_available','calibration_objective_selected',
                'temperature_scope_selected','temperature_parameter_selected',
                'calibration_execution_authorized','calibrated_output_authorized',
                'confirmation_selection_authorized'):
        require(c[key] is False,'Phase6 readiness changed: '+key)
    require(c['confirmation_closed'] is True,'Phase6 confirmation gate changed')
    require(f and all(type(v) is bool and v is False for v in f.values()),
            'Phase8 factor-conditioning gate changed')
    bound=documents(repo)
    # Prospective categories, not replacements for the 13 existing requests.
    obligations=(
        ('physical_sensor_measurement_and_capture_provenance','REQUIRES_INDEPENDENT_EVIDENCE'),
        ('capture_applicable_camera_lidar_imu_geometry_and_time','REQUIRES_INDEPENDENT_EVIDENCE'),
        ('independent_6dof_reference_and_time_association','REQUIRES_INDEPENDENT_EVIDENCE'),
        ('real_healthy_degraded_unusable_supervision','REQUIRES_INDEPENDENT_EVIDENCE'),
        ('measurement_residual_noise_and_cross_source_dependence','REQUIRES_EMPIRICAL_VALIDATION'),
        ('validation_only_uncertainty_and_health_calibration','BLOCKED_BY_PHASE5'),
        ('freeze_evaluation_protocol_and_confirmation_partition','REQUIRES_REVIEW'),
    )
    return {
        'schema':SCHEMA,
        'evidence_basis':'PUBLISHED_REPOSITORY_CONTRACTS_AND_DOCUMENTED_GAPS_ONLY',
        'published_document_digest_manifest':bound,
        'current_phase5_health_gate':h,
        'current_phase6_probability_calibration_gate':c,
        'current_phase8_factor_conditioning_gate':f,
        'proposed_a48_readiness_crosswalk':[{'category':a,'status':b} for a,b in obligations],
        'existing_evidence_request_count_per_published_a23':13,
        'existing_m2dgr_gates_closed_per_published_evidence':11,
        'frozen_m2dgr_split_per_published_a22':{'train':22,'validation_calibration':7,'confirmation_test':7},
        'recorded_data_opened':False,'new_physical_evidence_accepted':False,
        'empirical_camera_lidar_imu_covariance_qualified':False,
        'synthetic_information_scaling_is_empirical_covariance':False,
        'physical_health_classification':'ABSTAIN',
        'physical_fault_source_attribution':'UNRESOLVED',
        'real_factor_admission':'DENIED',
        'operational_factor_weighting':'DENIED',
        'robot_actuation':'DENIED',
        'confirmation_test_selection':'CLOSED',
    }
