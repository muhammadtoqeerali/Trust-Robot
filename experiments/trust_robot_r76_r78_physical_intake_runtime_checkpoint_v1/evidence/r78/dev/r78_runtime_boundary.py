"""Runtime evidence barrier: shape admission is never execution permission.

Uses SHA-pinned R76/R77 off-Git code + frozen repository sensor/factor gates.
No real input or GT is opened and no customer-supplied approval switch exists.
"""
from __future__ import annotations
import hashlib
import json
import pathlib

import r76_intake as intake
import r77_bridge as bridge

SCHEMA='TRUST_ROBOT_R78_RECORDED_FACTOR_RUNTIME_BOUNDARY_V1'
BASE='c1f59bb5e38bdfece14798031c0d911441b28de8'
CODE_PINS={
 'r76_intake.py':'db8db10193f589cdef290397d433e7af94a8e9eddbcc9b01382ce245d223830d',
 'r77_bridge.py':'9a010207a7ed8a5c61a8427ee2dd4ecc9fca6fe01dfd4aa0d3629f8c462d6dde',
}
REPORT_PINS={
 'r76_source_intake_contract_v1.json':'c3d18535c4b622620c35aad4e839f89793d4eb3b1fbddf4828ee8103144f8be6',
 'r76_independent_validation_v1.json':'5c244e64cfb9e891196ad70cc2a5cca10fb8a50914708bd1889d44417e84d311',
 'r77_intake_sensor_factor_boundary_v1.json':'3bf5764305f10d68a3d3c43f6b371d4338337cebf483d4b2599dbdcd261ae75c',
 'r77_independent_validation_v1.json':'778d609c3be64c2526d5b155d3c264bf41d4ef9d2a92c6a48500eece79a8d13a',
}
class RuntimeBoundaryError(ValueError):
    pass
class RealExecutionDenied(RuntimeBoundaryError):
    pass

def require(ok, reason):
    if not ok:
        raise RuntimeBoundaryError(reason)

def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()

def require_pin(path, expected):
    p=pathlib.Path(path)
    require(p.is_file() and not p.is_symlink() and sha(p)==expected,
            'PIN_MISMATCH:'+p.name)
    return p

def validate_receipts(r77, independent):
    require(r77.get('schema')==bridge.SCHEMA,'R77_SCHEMA')
    require(r77.get('status')=='PASS_SOFTWARE_ONLY','R77_STATUS')
    require(r77.get('git_baseline')==BASE,'R77_BASE')
    require(r77.get('trajectory')=='room_02' and r77.get('split')=='train','R77_TRAIN')
    require(r77.get('historical_gates_checked')==11 and r77.get('synthetic_claim_shapes_validated')==11,'R77_GATE_COUNT')
    require(r77.get('historical_timing_receipts_checked')==5,'R77_TIMING_COUNT')
    require(len(r77.get('candidate_claim_names',[]))==11 and len(set(r77['candidate_claim_names']))==11,'R77_CLAIMS')
    for key in ('m2dgr_sensor_admission_gate_rejected','multimodal_recorded_factor_gate_rejected','gt_recovery_status_preserved'):
        require(r77.get(key) is True,'R77_GATE:'+key)
    for key in ('apparently_filled_author_candidate_admitted','new_physical_evidence_received',
                'physical_frame_qualified','physical_clock_qualified','real_pose_factors_authorized',
                'health_training_authorized','ate_rpe_authorized','confirmation_test_accessed','raw_gt_or_rosbag_opened'):
        require(r77.get(key) is False,'R77_DENIAL:'+key)
    require(r77.get('scientific_gates_closed')==11,'R77_SCIENCE_COUNT')
    require(independent.get('schema')=='TRUST_ROBOT_R77_INDEPENDENT_GATE_BRIDGE_VALIDATION_V1','INDEPENDENT_SCHEMA')
    require(independent.get('status')=='PASS' and independent.get('scientific_gates_closed')==11,'INDEPENDENT_STATUS')
    require(independent.get('existing_sensor_factor_gates_remained_closed') is True,'INDEPENDENT_FACTORS')
    require(independent.get('physical_sources_qualified')==0,'INDEPENDENT_QUALIFICATION')
    require(independent.get('raw_gt_or_rosbag_opened') is False and independent.get('confirmation_test_accessed') is False,'INDEPENDENT_PRIVACY')
    require(independent.get('primary_result_sha256')==REPORT_PINS['r77_intake_sensor_factor_boundary_v1.json'],'INDEPENDENT_REPORT_HASH')
    return True

def context(repo, r76dev, r76out, r77dev, r77out):
    repo,r76dev,r76out,r77dev,r77out=map(pathlib.Path,(repo,r76dev,r76out,r77dev,r77out))
    for module,root,name in ((intake,r76dev,'r76_intake.py'),(bridge,r77dev,'r77_bridge.py')):
        p=require_pin(root/name,CODE_PINS[name])
        require(pathlib.Path(module.__file__).resolve()==p.resolve(),'PYTHON_MODULE_IDENTITY:'+name)
    for root,name in ((r76out,'r76_source_intake_contract_v1.json'),
                      (r76out,'r76_independent_validation_v1.json'),
                      (r77out,'r77_intake_sensor_factor_boundary_v1.json'),
                      (r77out,'r77_independent_validation_v1.json')):
        require_pin(root/name,REPORT_PINS[name])
    r77=json.loads((r77out/'r77_intake_sensor_factor_boundary_v1.json').read_text())
    independent=json.loads((r77out/'r77_independent_validation_v1.json').read_text())
    validate_receipts(r77,independent)
    gates,timing,snapshot=bridge.load_state(repo,r76out)
    require(sorted(gates)==r77['candidate_claim_names'],'CANDIDATE_IDENTITY')
    require(len(timing)==5 and len(snapshot['by_id'])==36,'SPLIT_INVENTORY')
    require(bridge.assert_real_factor_gates_closed(snapshot) is True,'ORIGINAL_GATES')
    return gates,snapshot

def inspect_format_only(candidate, repo, r76dev, r76out, r77dev, r77out):
    gates,snapshot=context(repo,r76dev,r76out,r77dev,r77out)
    try:
        result=bridge.assess_candidate(candidate,gates,snapshot)
    except (bridge.BridgeError,intake.IntakeError,KeyError,TypeError) as exc:
        raise RuntimeBoundaryError('CANDIDATE_REJECTED') from exc
    require(result.get('candidate_format_valid') is True,'FORMAT')
    for k in ('source_content_independently_verified','recorded_sensor_factor_admitted',
              'multimodal_pose_factor_admitted','physical_calibration_qualified',
              'physical_clock_qualified','health_training_authorized','ate_rpe_authorized'):
        require(result.get(k) is False,'UNAUTHORIZED_CLAIM:'+k)
    return {'schema':SCHEMA,'claim_id':result['claim_id'],
            'candidate_shape_valid':True,'physical_source_admitted':False,
            'recorded_factor_executable':False,'health_training_authorized':False,
            'ate_rpe_authorized':False,'status':'FORMAT_ONLY_EXECUTION_DENIED'}

def require_recorded_execution(candidate, repo, r76dev, r76out, r77dev, r77out):
    # Intentionally cannot return an authorization token, including for a
    # syntactically complete or author-like candidate.
    inspect_format_only(candidate,repo,r76dev,r76out,r77dev,r77out)
    raise RealExecutionDenied('Real sensor factor execution requires future independently qualified physical sources')

def build(repo,r76dev,r76out,r77dev,r77out,output):
    gates,snapshot=context(repo,r76dev,r76out,r77dev,r77out)
    audited=[]
    for claim in sorted(gates):
        candidate=bridge.synthetic_candidate(claim,gates,filled=True,source_class='author_source_candidate')
        result=inspect_format_only(candidate,repo,r76dev,r76out,r77dev,r77out)
        require(result['recorded_factor_executable'] is False,'RUNTIME_BYPASS')
        try:
            require_recorded_execution(candidate,repo,r76dev,r76out,r77dev,r77out)
        except RealExecutionDenied:
            pass
        else:
            raise RuntimeBoundaryError('RUNTIME_EXECUTION_OPENED')
        audited.append(claim)
    result={
        'schema':SCHEMA,'status':'PASS_SOFTWARE_ONLY','git_parent_commit':BASE,
        'trajectory_id':'room_02','split':'train','claims_evaluated':audited,
        'candidate_shapes_tested':11,'apparently_filled_author_like_cases_denied':11,
        'existing_sensor_factor_gates_tested':2,'historical_timing_receipts':5,
        'source_code_sha256':CODE_PINS,'prior_private_report_sha256':REPORT_PINS,
        'scientific_gates_closed':11,'physically_qualified_sources':0,
        'runtime_authorizations':0,'raw_gt_or_rosbag_opened':False,
        'confirmation_test_accessed':False,'real_pose_factors_authorized':False,
        'health_training_authorized':False,'ate_rpe_authorized':False,
        'git_modified':False,
    }
    with (pathlib.Path(output)/'r78_runtime_boundary_decision_v1.json').open('x',encoding='utf-8') as f:
        json.dump(result,f,sort_keys=True,indent=2,allow_nan=False)
        f.write('\n')
    print('R78_FORMAT_ONLY_AUTHOR_LIKE_CASES=11_DENIED')
    print('R78_HARD_EXECUTION_BOUNDARY=11_DENIED')
    print('R78_EXISTING_RECORDED_FACTOR_GATES=2_CLOSED')

if __name__=='__main__':
    import sys
    build(*sys.argv[1:])
