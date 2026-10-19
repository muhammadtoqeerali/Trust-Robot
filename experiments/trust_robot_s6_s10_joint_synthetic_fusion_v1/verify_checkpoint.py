"""Standalone immutable, SHA-pinned S6–S10 checkpoint verifier."""
import ast
import hashlib
import json
import pathlib
import subprocess
import xml.etree.ElementTree as ET

ROOT=pathlib.Path(__file__).resolve().parent
REPO=ROOT.parents[1]
BASE='ebe97e3ee3d3c9872b2b5643de5124bb0cfacf43'

def need(ok,reason):
    if not ok:raise ValueError('S6_S10_CHECKPOINT_FAIL:'+reason)

def sha(path):
    p=pathlib.Path(path)
    need(p.is_file() and not p.is_symlink() and p.stat().st_nlink==1 and 0<p.stat().st_size<5000000,'UNSAFE_FILE:'+str(p))
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read(path):return json.loads(pathlib.Path(path).read_text(encoding='utf-8'))

def cases(path):return list(ET.parse(path).getroot().iter('testcase'))

m=read(ROOT/'checkpoint_manifest_v1.json')
need(m['schema']=='TRUST_ROBOT_S6_S10_JOINT_FUSION_CHECKPOINT_V1' and
     m['parent_commit']==BASE and m['branch']=='kios-isaacsim-v15-integration','MANIFEST')
need(len(m['frozen_sha256'])==30 and set(m['file_sha256'])==set(m['frozen_sha256'])|{'README.md'},'FROZEN_INVENTORY')
need([len(m['phase_files'][str(i)]) for i in range(6,11)]==[6,7,6,6,5],'PHASE_FILE_COUNTS')
need({x for i in range(6,11) for x in m['phase_files'][str(i)]}==set(m['frozen_sha256']),'PHASE_FILE_MEMBERSHIP')
actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()}
need(actual==set(m['file_sha256'])|{'checkpoint_manifest_v1.json','verify_checkpoint.py'} and len(actual)==33,'EXACT_ARCHIVE_INVENTORY')
need(not any(p.is_symlink() for p in ROOT.rglob('*')),'SYMLINK')
for rel,expect in m['file_sha256'].items():
    pure=pathlib.PurePosixPath(rel)
    need(not pure.is_absolute() and '..' not in pure.parts and len(expect)==64,'RELATIVE_PATH')
    need(sha(ROOT/rel)==expect,'SHA:'+rel)
    if rel.endswith('.py'):ast.parse((ROOT/rel).read_text(encoding='utf-8'))
    elif rel.endswith('.json'):read(ROOT/rel)
    elif rel.endswith('.xml'):ET.parse(ROOT/rel)
need(all(m['file_sha256'][p]==h for p,h in m['frozen_sha256'].items()),'PIN_MISMATCH')

expected_docs={'AGENTS.md','docs/TRUST_ROBOT_PROJECT_STATE.md','docs/audits/trust_robot/TRUST_ROBOT_KIOS_S6_S10_JOINT_SYNTHETIC_FUSION_V1.md'}
need(set(m['documentation_sha256'])==expected_docs,'DOCUMENT_INVENTORY')
manifest_rel=(ROOT/'checkpoint_manifest_v1.json').relative_to(REPO).as_posix()
commit=subprocess.check_output(['git','-C',str(REPO),'rev-list','-1','HEAD','--',manifest_rel],text=True).strip()
for rel,expect in m['documentation_sha256'].items():
    payload=(subprocess.check_output(['git','-C',str(REPO),'show',commit+':'+rel])
             if commit else (REPO/rel).read_bytes())
    need(hashlib.sha256(payload).hexdigest()==expect,'DOCUMENT_SHA:'+rel)
prior=REPO/'experiments/trust_robot_s1_s5_core_6dof_readiness_v1'
need(sha(prior/'checkpoint_manifest_v1.json')==m['prior_checkpoint_manifest_sha256'] and
     sha(prior/'verify_checkpoint.py')==m['prior_checkpoint_verifier_sha256'],'PRIOR_CHECKPOINT_SHA')

s=lambda path:m['frozen_sha256'][path]
r={i:read(ROOT/f'evidence/s{i}_report.json') for i in range(6,11)}
v={i:read(ROOT/f'evidence/s{i}_validation.json') for i in range(6,11)}
for i,num in ((6,23),(7,22),(8,27),(9,43),(10,219)):
    cc=cases(ROOT/f'evidence/s{i}_junit.xml')
    need(len(cc)==num and len({(c.get('classname'),c.get('name')) for c in cc})==num and
         not any(ch.tag in ('failure','error','skipped') for c in cc for ch in c),'JUNIT:'+str(i))
    need(r[i]['source_sha256' if i==6 else 'engine_sha256']==s(f'code/s{i}_'+
         {6:'joint_fusion',7:'factor_support',8:'correlated_conflict',9:'adversarial',10:'integration_review'}[i]+'.py'),'ENGINE_SHA:'+str(i))
    need(v[i]['verifier_sha256']==s(f'code/s{i}_independent_verify.py') and
         v[i]['report_sha256']==s(f'evidence/s{i}_report.json'),'REPORT_VERIFIER_SHA:'+str(i))
    need(r[i]['junit_sha256' if i!=10 else 'combined_junit_sha256']==s(f'evidence/s{i}_junit.xml'),'JUNIT_SHA:'+str(i))
    need(r[i]['test_cases_passed' if i==6 else 'unit_tests_passed' if i in (7,8,9) else 'regression_total']==num,'REPORT_TESTS:'+str(i))
    need(v[i]['unit_tests_verified' if i in (6,7,8,9) else 'total_regression_tests_verified']==num,'VERIFIED_TESTS:'+str(i))
    need(r[i]['real_sensor_factor_execution_authorized' if i in (6,8,9,10) else 'real_sensor_factor_admission'] is False,'RECORDED_ADMISSION:'+str(i))
for i in (6,7,8,9):
    need(v[i]['engine_sha256']==s('code/s'+str(i)+'_'+{6:'joint_fusion',7:'factor_support',8:'correlated_conflict',9:'adversarial'}[i]+'.py'),'ENGINE_VALIDATION:'+str(i))
    need(v[i]['test_sha256']==s(f'code/test_s{i}_'+{6:'joint_fusion',7:'factor_support',8:'correlated_conflict',9:'adversarial'}[i]+'.py'),'TEST_VALIDATION:'+str(i))
need(v[10]['engine_sha256']==s('code/s10_integration_review.py'),'S10_ENGINE_VALIDATION')
failed=cases(ROOT/'evidence/s7_original_failed_junit.xml')
need(len(failed)==22 and sum(c.find('failure') is not None for c in failed)==1 and
     'canonical' in ET.tostring(next(c for c in failed if c.find('failure') is not None),encoding='unicode'),'FAILED_JUNIT_PRESERVATION')
need(r[7]['s6_report_sha256']==s('evidence/s6_report.json') and
     r[8]['s7_report_sha256']==s('evidence/s7_report.json') and
     r[9]['s8_report_sha256']==s('evidence/s8_report.json'),'REPORT_CHAIN')
need(r[7]['s6_validation_sha256']==s('evidence/s6_validation.json') and
     r[8]['s7_validation_sha256']==s('evidence/s7_validation.json') and
     r[9]['s8_validation_sha256']==s('evidence/s8_validation.json'),'VALIDATION_CHAIN')
need(r[10]['original_evidence_sha256']=={
    's2_report':sha(prior/'evidence/s2_report.json'),
    's2_xml':sha(prior/'evidence/s2_junit.xml'),
    's6_report':s('evidence/s6_report.json'),'s6_validation':s('evidence/s6_validation.json'),'s6_xml':s('evidence/s6_junit.xml'),
    's7_report':s('evidence/s7_report.json'),'s7_validation':s('evidence/s7_validation.json'),
    's7_xml':s('evidence/s7_junit.xml'),'s7_failed_xml':s('evidence/s7_original_failed_junit.xml'),
    's8_report':s('evidence/s8_report.json'),'s8_validation':s('evidence/s8_validation.json'),'s8_xml':s('evidence/s8_junit.xml'),
    's9_report':s('evidence/s9_report.json'),'s9_validation':s('evidence/s9_validation.json'),'s9_xml':s('evidence/s9_junit.xml'),
},'S10_HISTORICAL_INPUT_BINDING')
need(r[10]['regression_total']==219 and r[10]['legacy_regressions_reexecuted']==104 and
     r[10]['new_regressions_reexecuted']=={'6':23,'7':22,'8':27,'9':43} and
     v[10]['total_regression_tests_verified']==219 and v[10]['cross_phase_replay_recomputed'] is True and
     v[10]['checkpoint_ready_for_guarded_archival'] is True,'S10_SUMMARY')
fp=r[10]['cross_phase_replay']['clean_joint_trajectory_sha256']
need(len(fp)==64 and fp==r[7]['nonlinear_perturbation']['baseline_states_sha256'] and
     any(x['condition']=='clean' and x['camera_enabled'] is True and x['estimated_states_sha256']==fp for x in r[6]['scenarios']) and
     any(x['camera_shift_m']==0.0 and x['estimated_trajectory_sha256']==fp for x in r[9]['nonlinear_synthetic_scenarios']),'S6_S7_S9_CLEAN_REPLAY')
need(r[10]['cross_phase_replay']['replay_measured_independent_accuracy'] is False and
     r[10]['integration_decision']=='SYNTHETIC_REGRESSION_ONLY_READY_FOR_ARCHIVAL','SCIENTIFIC_SCOPE')
for key in ('real_sensor_factor_execution_authorized','m2dgr_scoring_authorized',
            'health_model_training_authorized','automatic_sensor_suppression_authorized','live_simulator_launch_authorized'):
    need(m[key] is False,'MANIFEST_SCIENCE_BOUNDARY:'+key)
for key in ('new_sensor_acquisitions','scientific_pose_factors','health_labels'):
    need(type(m[key]) is int and m[key]==0,'SCIENCE_COUNT:'+key)
print('S6_S10_CHECKPOINT_INTEGRITY=PASS')
print('S6_S10_30_FROZEN_SOURCE_REPORT_TEST_HASHES=VERIFIED')
print('S6_S10_219_COMBINED_TESTS=VERIFIED')
print('S6_S10_S7_FAILED_AND_REPAIRED_JUNIT=PRESERVED')
print('S6_S10_S6_S7_S9_REPLAY_HASH=VERIFIED')
print('S6_S10_COMMIT_SCOPED_DOCUMENTATION=VERIFIED')
print('REAL_SENSOR_FACTOR_ADMISSION=DENIED')
print('SCIENTIFIC_POSE_FACTORS=0')
