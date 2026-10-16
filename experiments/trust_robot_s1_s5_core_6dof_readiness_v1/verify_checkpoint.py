"""Standalone SHA-pinned S1–S5 historical checkpoint verifier."""
import ast,hashlib,json,pathlib,subprocess,xml.etree.ElementTree as ET
ROOT=pathlib.Path(__file__).resolve().parent
REPO=ROOT.parents[1]
BASE='79a2abf6de6ff68df23de8bd04b538ce0c95b46b'
def need(ok,msg):
    if not ok: raise ValueError('S1_S5_CHECKPOINT_FAIL:'+msg)
def sha(p):
    p=pathlib.Path(p)
    need(p.is_file() and not p.is_symlink() and p.stat().st_nlink==1 and p.stat().st_size<5000000,'UNSAFE_FILE:'+str(p))
    return hashlib.sha256(p.read_bytes()).hexdigest()
def js(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
m=js(ROOT/'checkpoint_manifest_v1.json')
need(m['schema']=='TRUST_ROBOT_S1_S5_CHECKPOINT_V1' and m['parent_commit']==BASE,'MANIFEST_ID')
need(m['branch']=='kios-isaacsim-v15-integration','BRANCH')
need(len(m['frozen_sha256'])==28 and set(m['file_sha256'])==set(m['frozen_sha256'])|{'README.md'},'FROZEN_INVENTORY')
need([len(m['phase_files'][str(i)]) for i in range(1,6)]==[4,5,7,7,5],'PHASE_COUNTS')
need(set(x for i in range(1,6) for x in m['phase_files'][str(i)])==set(m['frozen_sha256']),'PHASE_INVENTORY')
actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()}
need(actual==set(m['file_sha256'])|{'checkpoint_manifest_v1.json','verify_checkpoint.py'} and len(actual)==31,'ARCHIVE_FILE_INVENTORY')
need(not any(p.is_symlink() for p in ROOT.rglob('*')),'SYMLINK_IN_ARCHIVE')
for rel,expected in m['file_sha256'].items():
    path=pathlib.PurePosixPath(rel)
    need(not path.is_absolute() and '..' not in path.parts,'UNSAFE_RELATIVE_PATH')
    need(sha(ROOT/rel)==expected,'HASH:'+rel)
    if rel.endswith('.py'):ast.parse((ROOT/rel).read_text(encoding='utf-8'))
    if rel.endswith('.json'):js(ROOT/rel)
    if rel.endswith('.xml'):ET.parse(ROOT/rel)
for rel,expected in m['frozen_sha256'].items():need(m['file_sha256'][rel]==expected,'PIN:'+rel)
expected_docs={'AGENTS.md','docs/TRUST_ROBOT_PROJECT_STATE.md','docs/audits/trust_robot/TRUST_ROBOT_KIOS_S1_S5_CORE_6DOF_READINESS_V1.md'}
need(set(m['documentation_sha256'])==expected_docs,'DOC_INVENTORY')
manifest_rel=(ROOT/'checkpoint_manifest_v1.json').relative_to(REPO).as_posix()
commit=subprocess.check_output(['git','-C',str(REPO),'rev-list','-1','HEAD','--',manifest_rel],text=True).strip()
for rel,expected in m['documentation_sha256'].items():
    if commit: value=hashlib.sha256(subprocess.check_output(['git','-C',str(REPO),'show',commit+':'+rel])).hexdigest()
    else: value=sha(REPO/rel)
    need(value==expected,'DOCUMENTATION_AT_CHECKPOINT:'+rel)
r={i:js(ROOT/f'evidence/s{i}_report.json') for i in range(1,6)}
v={i:js(ROOT/f'evidence/s{i}_validation.json') for i in range(1,6)}
s=lambda rel:m['frozen_sha256'][rel]
need(r[1]['m2dgr_trajectory_count']==36 and r[1]['m2dgr_sync_entries']==140 and r[1]['m2dgr_sync_qualified']==0 and r[1]['analytic_module_count']==16,'S1_SCOPE')
need(r[1]['m2dgr_split_counts']=={'train':22,'validation_calibration':7,'confirmation_test':7},'FROZEN_SPLIT')
need(r[2]['regression_test_count']==104 and r[2]['regression_counts']=={'passed':104,'failed':0,'errored':0,'skipped':0} and r[2]['factor_gate_probe']['negative_control_count']==8,'S2_RESULT')
need(v[2]['verified_test_count']==104 and v[2]['verified_recorded_factor_denials']==8 and r[2]['s1_report_sha256']==s('evidence/s1_report.json') and r[2]['s1_validation_sha256']==s('evidence/s1_validation.json'),'S2_LINEAGE')
need(r[3]['test_cases_passed']==41 and v[3]['verified_unit_tests']==41 and r[3]['supported_stream_count']==4 and r[3]['real_pose_factor_execution_authorized'] is False,'S3_RESULT')
need(r[3]['s2_report_sha256']==s('evidence/s2_report.json') and r[3]['s2_validation_sha256']==s('evidence/s2_validation.json'),'S3_LINEAGE')
need(r[4]['tests_passed']==55 and v[4]['verified_tests']==55 and r[4]['unqualified_gate_instances']==32 and v[4]['verified_closed_gate_instances']==32 and r[4]['recorded_sensor_factors_generated']==0,'S4_RESULT')
need(r[4]['s3_report_sha256']==s('evidence/s3_report.json') and r[4]['s3_validation_sha256']==s('evidence/s3_validation.json'),'S4_LINEAGE')
m4=js(ROOT/'evidence/s4_matrix.json')
need(len(m4['streams'])==4 and all(len(row['requirement_gates'])==8 and all(val is False for val in row['requirement_gates'].values()) for row in m4['streams']),'S4_CLOSED_GATES')
m5=js(ROOT/'evidence/s5_matrix.json')
need(r[5]['negative_control_count']==32 and v[5]['false_promotion_controls_reviewed']==32 and v[5]['existing_regression_tests_verified']==104 and v[5]['s3_contract_tests_verified']==41 and v[5]['s4_contract_tests_verified']==55,'S5_RESULT')
need(r[5]['matrix_sha256']==s('evidence/s5_matrix.json') and v[5]['matrix_sha256']==s('evidence/s5_matrix.json') and v[5]['report_sha256']==s('evidence/s5_report.json'),'S5_LINEAGE')
need(m5['next_implementation']['work_id']=='S6_CPU_ONLY_INDEPENDENT_CAMERA_LIDAR_SAME_EDGE_FUSION' and m5['next_implementation']['real_sensor_admission'] is False,'S6_SCOPE')
need(m5['s1_s4_report_and_matrix_sha256']=={'s1':s('evidence/s1_report.json'),'s2':s('evidence/s2_report.json'),'s3':s('evidence/s3_report.json'),'s4':s('evidence/s4_report.json'),'s4_matrix':s('evidence/s4_matrix.json')},'S5_PRIOR_PHASES')
for i,num in ((2,104),(3,41),(4,55)):
    cases=list(ET.parse(ROOT/f'evidence/s{i}_junit.xml').getroot().iter('testcase'))
    need(len(cases)==num and not any(c.find(t) is not None for c in cases for t in ('failure','error','skipped')),f'S{i}_JUNIT')
for i in range(1,6):
    need(v[i]['report_sha256']==s(f'evidence/s{i}_report.json') if i!=1 else v[i]['report_sha256']==s('evidence/s1_report.json'),'VALIDATION_REPORT_'+str(i))
need(r[3]['engine_sha256']==s('code/s3_contract.py') and r[4]['engine_sha256']==s('code/s4_requirements.py') and r[5]['engine_sha256']==s('code/s5_review.py'),'ENGINE_SOURCE_LINK')
need(v[4]['verifier_sha256']==s('code/s4_independent_verify.py') and v[5]['verifier_sha256']==s('code/s5_independent_verify.py'),'REPAIRED_VERIFIER_LINK')
for key in ('physical_capture_time_verified','cross_modal_sync_verified','full_sensor_extrinsics_verified','real_sensor_factor_execution_authorized','m2dgr_scoring_authorized','empirical_health_training_authorized','live_simulator_launch_authorized'):
    need(m[key] is False,'SCIENTIFIC_GATE:'+key)
for key in ('new_sensor_acquisitions','scientific_pose_factors','health_labels'):need(m[key]==0,'SCIENCE_COUNT:'+key)
print('S1_S5_CHECKPOINT_INTEGRITY=PASS')
print('S1_S5_28_FROZEN_SOURCE_REPORT_TEST_HASHES=VERIFIED')
print('S1_S5_104_41_55_TEST_EVIDENCE=VERIFIED')
print('S1_S5_COMMIT_SCOPED_DOCUMENTATION=VERIFIED')
print('S1_S5_SCIENTIFIC_ADMISSION=DENIED')
print('SCIENTIFIC_POSE_FACTORS=0')
