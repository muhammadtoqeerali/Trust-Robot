"""R94 independent archive integrity and scientific-boundary verifier."""
import hashlib,json,pathlib,stat,sys
BASE='8b6024cc7c09568fc1e5485abdc0a5aa2bb72cd9'
SCHEMA='TRUST_ROBOT_R92_R93_PHYSICAL_EVIDENCE_READINESS_CHECKPOINT_V1'
PHASES={
 'r92':('r92_gap.py','test_r92.py',(
  'r92_evidence_acquisition_order_v1.md','r92_independent_validation_v1.json','r92_physical_source_gap_decision_v1.json')),
 'r93':('r93_readiness.py','test_r93.py',(
  'r93_author_evidence_request_DRAFT_NOT_SENT.md','r93_independent_validation_v1.json','r93_outreach_readiness_v1.json','r93_source_intake_checklist_v1.md'))}

def need(ok,why):
 if not ok:raise ValueError('R94_CHECKPOINT_DENIED:'+why)
def sha(b):return hashlib.sha256(b).hexdigest()
def obj(r,p):return json.loads((r/p).read_bytes())
def check(root):
 need(root.is_dir() and not root.is_symlink(),'ROOT')
 m=obj(root,'checkpoint_manifest_v1.json')
 need(m.get('schema')==SCHEMA and m.get('parent_commit')==BASE,'IDENTITY')
 need(m.get('branch')=='kios-isaacsim-v15-integration','BRANCH')
 pins=m.get('source_sha256');meta=m.get('metadata_sha256')
 need(type(pins) is dict and len(pins)==11 and m.get('source_count')==11,'SOURCE_COUNT')
 need(type(meta) is dict and set(meta)=={'README.md','verify_checkpoint.py'},'META_COUNT')
 names=set()
 for phase,(engine,test,results) in PHASES.items():
  names|={f'evidence/{phase}/dev/{engine}',f'evidence/{phase}/dev/{test}'}
  names|={f'evidence/{phase}/result/{name}' for name in results}
 need(set(pins)==names,'SOURCE_ALLOWLIST')
 expected=names|set(meta)|{'checkpoint_manifest_v1.json'}
 need(len(expected)==14,'FILE_COUNT')
 dirs=set()
 for name in expected:
  p=pathlib.PurePosixPath(name)
  need(not p.is_absolute() and '..' not in p.parts,'PATH')
  dirs|={'/'.join(p.parts[:i]) for i in range(1,len(p.parts))}
 need({str(x.relative_to(root)) for x in root.rglob('*')}==expected|dirs,'EXACT_TREE')
 for d in dirs:
  need((root/d).is_dir() and not (root/d).is_symlink(),'DIR:'+d)
 for name in expected:
  s=(root/name).lstat()
  need(stat.S_ISREG(s.st_mode) and s.st_nlink==1 and 0<s.st_size<2000000,'REGULAR:'+name)
 for name,pin in {**pins,**meta}.items():
  raw=(root/name).read_bytes()
  need(type(pin) is str and len(pin)==64 and sha(raw)==pin,'SHA:'+name)
  need(not any(x in raw for x in (b'/home/'+b'kios/',b'/mnt/'+b'hdd16T/',b'C:'+b'\\Users\\')),'PRIVATE:'+name)
 r92_rel='evidence/r92/result/r92_physical_source_gap_decision_v1.json'
 r93_rel='evidence/r93/result/r93_outreach_readiness_v1.json'
 a,b=obj(root,r92_rel),obj(root,r93_rel)
 v92=obj(root,'evidence/r92/result/r92_independent_validation_v1.json')
 v93=obj(root,'evidence/r93/result/r93_independent_validation_v1.json')
 need(a.get('schema')=='TRUST_ROBOT_R92_PHYSICAL_SOURCE_QUALIFICATION_GAP_V1','R92_SCHEMA')
 need(a.get('status')=='PASS_EXISTING_EVIDENCE_GAP_ANALYSIS_ONLY','R92_STATUS')
 need(a.get('historical_unfilled_gate_receipts')==11 and len(a.get('gate_matrix',{}))==11,'GATES')
 need(a.get('historical_unfilled_timing_receipts')==5 and len(a.get('timing_receipt_matrix',{}))==5,'TIMING')
 need(a.get('tracked_evidence_files_read')==13 and len(a.get('source_files_sha256',{}))==13,'UPSTREAM_SOURCES')
 need(a.get('reference_recovery',{}).get('raw_gt_bytes_recovered_locally') is True,'GT_RECOVERED')
 need(a['reference_recovery'].get('reference_physically_qualified') is False,'GT_UNQUALIFIED')
 need(a['reference_recovery'].get('invalid_rotation_records')==90,'GT_INVALID_ROTATIONS')
 need(len(a.get('priority_actions',[]))==5,'PRIORITIES')
 need(all(x.get('physical_gate_authorized') is False for x in a['gate_matrix'].values()),'NO_GATE_UPGRADE')
 need(all(x.get('physical_capture_time_qualified') is False for x in a['timing_receipt_matrix'].values()),'NO_TIMING_UPGRADE')
 for key in ('new_external_evidence_received_during_r92','real_sensor_factors_authorized','health_training_authorized','ate_rpe_authorized','confirmation_test_accessed','raw_rosbags_or_gt_opened_during_r92'):
  need(a.get(key) is False,'R92_DENIAL:'+key)
 need(a.get('scientific_gates_closed')==11,'R92_11_GATES')
 need(v92.get('status')=='PASS' and v92.get('scientific_gates_closed')==11,'R92_RECEIPT')
 need(v92.get('decision_sha256')==pins[r92_rel],'R92_RESULT_PIN')
 need(v92.get('action_plan_sha256')==pins['evidence/r92/result/r92_evidence_acquisition_order_v1.md'],'R92_PLAN_PIN')
 need(v92.get('engine_sha256')==pins['evidence/r92/dev/r92_gap.py'] and v92.get('tests_sha256')==pins['evidence/r92/dev/test_r92.py'],'R92_CODE_PIN')
 need(b.get('schema')=='TRUST_ROBOT_R93_PHYSICAL_EVIDENCE_OUTREACH_READINESS_V1','R93_SCHEMA')
 need(b.get('status')=='DRAFT_READY_FOR_USER_REVIEW_NOT_SENT','R93_STATUS')
 need(b.get('r92_decision_sha256')==pins[r92_rel],'R92_R93_LINEAGE')
 need(len(b.get('gate_requests',{}))==11 and len(b.get('timing_stream_requests',{}))==5,'R93_REQUIREMENTS')
 need(b.get('raw_gt_recovery_resolved_locally') is True and b.get('raw_gt_re_download_required') is False,'R93_GT_DISTINCTION')
 for key in ('request_sent','response_received','new_external_source_received','source_bytes_independently_verified','physical_qualification_authorized','real_factor_execution_authorized','health_training_authorized','ate_rpe_authorized','confirmation_test_accessed'):
  need(b.get(key) is False,'R93_DENIAL:'+key)
 need(b.get('scientific_gates_closed')==11,'R93_11_GATES')
 need(v93.get('status')=='PASS' and v93.get('scientific_gates_closed')==11,'R93_RECEIPT')
 need(v93.get('r92_decision_sha256')==pins[r92_rel],'R93_RECEIPT_PARENT')
 for key,rel in {
  'engine_sha256':'evidence/r93/dev/r93_readiness.py',
  'tests_sha256':'evidence/r93/dev/test_r93.py',
  'readiness_sha256':r93_rel,
  'unsent_request_sha256':'evidence/r93/result/r93_author_evidence_request_DRAFT_NOT_SENT.md',
  'intake_checklist_sha256':'evidence/r93/result/r93_source_intake_checklist_v1.md'
 }.items():need(v93.get(key)==pins[rel],'R93_SHA:'+key)
 draft=(root/'evidence/r93/result/r93_author_evidence_request_DRAFT_NOT_SENT.md').read_text('utf-8')
 need('DRAFT — NOT SENT' in draft and 'not requesting another GT download' in draft,'DRAFT_LABEL')
 need(m.get('archived_regression_tests')==41 and m.get('historical_scientific_gates')==11 and m.get('historical_timing_receipts')==5,'REGRESSION_COUNTS')
 need(m.get('original_ground_truth_bytes_recovered_prior_to_r92') is True and m.get('author_request_status')=='DRAFT_NOT_SENT','MANIFEST_GT_DRAFT')
 for key in ('physical_ground_truth_qualified','new_physical_sources_received','external_request_sent','physical_sensor_clock_or_extrinsics_qualified','real_sensor_factor_execution_authorized','health_training_authorized','ate_rpe_authorized','gt_or_rosbags_archived','sealed_confirmation_test_accessed'):
  need(m.get(key) is False,'MANIFEST_DENIAL:'+key)
 need(m.get('scientific_gates_closed')==11,'MANIFEST_GATES')
 print('R94_STANDALONE_CHECKPOINT_VERIFIER=PASS')
 print('R94_11_SOURCE_ARTIFACTS_SHA256=PASS')
 print('R94_R92_R93_SOURCE_AND_RECEIPT_LINEAGE=PASS')
 print('R94_EVIDENCE_REQUEST=DRAFT_NOT_SENT')
 print('R94_SCIENTIFIC_GATES=11_CLOSED')

if __name__=='__main__':
 need(len(sys.argv)==3 and sys.argv[1]=='verify','ARGUMENTS')
 check(pathlib.Path(sys.argv[2]))
