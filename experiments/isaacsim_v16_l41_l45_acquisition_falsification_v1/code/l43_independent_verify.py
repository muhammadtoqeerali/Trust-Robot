"""L43 separate read-only verifier with independent manifest classifier.

Imports only the mutation inventory from the assessor; validation is
independently implemented from frozen evidence, not its decision function.
"""
import argparse, hashlib, importlib.util, json, sqlite3
from pathlib import Path

BASE='8d5a1701df3e9d755ac0a4b5adda2845873f52eb'
MOD=('camera','lidar','imu')
NAMES=('challenge_v1.json','admission_v1.json','seal_v1.json')

def need(v,s):
 if not v:raise ValueError(s)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def obj(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def dig(s):return hashlib.sha256(s).hexdigest()

def independent_expected(manifest,l42,db_sha):
 sid=l42['session_id'];nonce=l42['nonce_sha256'];rc=l42['outbox_receipts_sha256']
 expected={
 'schema':'TRUST_ROBOT_L43_SYNTHETIC_SESSION_MANIFEST_V1',
 'parent_git_commit':BASE,'session_id':sid,'nonce_hash':nonce,
 'run_id':'L43_SYNTHETIC_'+sid,'registry_snapshot_sha256':db_sha,
 'challenge_receipt_sha256':rc['challenge_v1.json'],
 'admission_receipt_sha256':rc['admission_v1.json'],
 'seal_receipt_sha256':rc['seal_v1.json'],
 'candidate_source_sha256':'4384b085f79dff51af5dbbf8a4c4bf4cae6deffc906bfbcaf8a8ef00a7e05dec',
 'guard_source_sha256':'b6bcabaf081bb1d6bf31b0ff907369bef841cf012d33b4ec407efd9bd6d94965',
 'interface_contract_sha256':'ee8dfaa3a0f95813d29efa68f65a3222a39cce5e12cf855c4c3508791dcc05f9',
 'fixture_transcript_sha256':'b2fa0728d1aa867d162bae7e463f7bf353b058222d2700eaf392cd271ed97736',
 'declared_expected_counts':{'camera':2,'lidar':2,'imu':2},
 'fixture_type':'DERIVED_SYNTHETIC_METADATA_NO_SENSOR',
 'live_simulator_launch_authorized':False,
 'actual_sensor_measurements':0,
 'seal_binds_actual_capture_payloads':False,
 'independent_payload_authenticity_verified':False,
 'independent_hardware_witness_verified':False,
 'physical_exposure_sync_verified':False,
 'trusted_clock_verified':False,
 'multi_host_replay_protection_verified':False,
 'independent_6dof_reference_verified':False,
 'scientific_pose_factors':0,'health_labels':0,
 }
 canonical=[]
 for j,mod in enumerate(MOD):
  for n in (1,2):
   canonical.append({
    'capture_event_id':f'{sid}:{mod}:{n}',
    'capture_counter':n,'modality_id':mod,
    'session_id':sid,'run_id':'L43_SYNTHETIC_'+sid,
    'nonce_hash':nonce,
    'challenge_receipt_sha256':rc['challenge_v1.json'],
    'admission_receipt_sha256':rc['admission_v1.json'],
    'seal_receipt_sha256':rc['seal_v1.json'],
    'candidate_source_sha256':expected['candidate_source_sha256'],
    'synthetic_payload_sha256':dig(f'L43_NOT_SENSOR|{sid}|{mod}|{n}'.encode()),
    'timestamp_clock_domain':'OFFLINE_SYNTHETIC_UNTRUSTED',
    'untrusted_time_tick':j*10+n,
    'physical_capture_verified':False,
   })
 return expected,canonical

def classify(m,l42,db_sha):
 try:
  header, canonical=independent_expected(m,l42,db_sha)
  need(type(m) is dict and set(m)==set(header)|{'events'},'HEADER_KEYS')
  for k,v in header.items():need(m[k]==v,'HEADER_'+k)
  ev=m['events'];need(type(ev) is list and len(ev)<=6,'EVENT_SIZE')
  matches=[]
  for r in ev:
   indices=[i for i,standard in enumerate(canonical) if r==standard]
   need(len(indices)==1,'EVENT_INVALID')
   matches.append(indices[0])
  need(matches==sorted(set(matches)),'EVENT_ORDER_OR_DUP')
  if len(matches)<6:return 'INCOMPLETE_SYNTHETIC_REVIEW_NO_SEAL'
  need(matches==list(range(6)),'EVENT_SET')
  return 'COMPLETE_SYNTHETIC_NOT_ACQUISITION'
 except (ValueError,KeyError,TypeError,IndexError):return 'QUARANTINED'

def main(a):
 r=obj(a.report);m=obj(a.manifest);l42=obj(a.l42report);v42=obj(a.l42validation)
 need(r['schema']=='TRUST_ROBOT_L43_SESSION_BINDING_PARTIAL_CAPTURE_VALIDATION_V1','REPORT_SCHEMA')
 need(r['parent_commit']==BASE and r['assessor_source_sha256']==sha(a.assessor),'ASSESSOR_HASH')
 need(r['synthetic_manifest_sha256']==sha(a.manifest),'MANIFEST_HASH')
 need(r['l42_report_sha256']==sha(a.l42report) and r['l42_validation_sha256']==sha(a.l42validation),'L42_HASH')
 need(v42['bridge_report_sha256']==sha(a.l42report) and v42['verified_adversarial_count']==25,'L42_VALIDATION_LINEAGE')
 need(r['frozen_source_sha256']['l42report']==sha(a.l42report),'L42_PIN')
 db=Path(a.session)/'registry.sqlite'
 need(db.is_file() and not db.is_symlink() and r['l42_registry_sha256']==sha(db)==l42['registry_sha256'],'DB_LINEAGE')
 con=sqlite3.connect('file:'+str(db.resolve())+'?mode=ro',uri=True)
 try:
  con.execute('PRAGMA query_only=ON')
  need(con.execute('PRAGMA quick_check').fetchone()[0]=='ok','DB_INTEGRITY')
  sessions=con.execute('SELECT session_id,nonce_hash,state FROM sessions').fetchall()
  rows=con.execute('SELECT stage,payload,digest,published FROM outbox ORDER BY stage').fetchall()
 finally:con.close()
 need(len(sessions)==1 and sessions[0][2]=='SEALED','SESSION_STATE')
 need(sessions[0][0]==l42['session_id']==r['l42_session_id'] and sessions[0][1]==l42['nonce_sha256']==r['l42_nonce_sha256'],'SESSION_IDENTITY')
 need(len(rows)==3 and len(r['l42_receipts_sha256'])==3,'OUTBOX_LENGTH')
 for i,(stage,body,h,published) in enumerate(rows):
  path=Path(a.session)/'receipts'/NAMES[i]
  need(stage==i and published==1 and dig(body)==h and path.read_bytes()==body,'RECEIPT_CONTENT')
  need(h==l42['outbox_receipts_sha256'][NAMES[i]]==r['l42_receipts_sha256'][NAMES[i]],'RECEIPT_LINEAGE')
  receipt=json.loads(body)
  need(receipt['session_id']==sessions[0][0] and receipt['nonce_hash']==sessions[0][1],'RECEIPT_ID')
  need(receipt['simulator_launch_authorized'] is False and receipt['new_sensor_measurements']==0,'RECEIPT_SCOPE')
  if i:need(receipt['prior_receipt_sha256']==rows[i-1][2],'RECEIPT_CHAIN')
 need(classify(m,l42,sha(db))=='COMPLETE_SYNTHETIC_NOT_ACQUISITION','BASELINE_VERIFICATION')
 spec=importlib.util.spec_from_file_location('l43_inventory',a.assessor)
 source=importlib.util.module_from_spec(spec);spec.loader.exec_module(source)
 cases=source.mutations(m)
 need(len(cases)==50 and len({name for name,_ in cases})==50,'NEGATIVE_INVENTORY')
 expected_names={x['name'] for x in r['adversarial_cases']}
 need(expected_names=={name for name,_ in cases},'CASE_NAME_MATCH')
 outcomes=[]
 for name,candidate in cases:
  result=classify(candidate,l42,sha(db))
  need(result!='COMPLETE_SYNTHETIC_NOT_ACQUISITION','ADVERSARY_ACCEPTED_'+name)
  need(result==next(x['decision'] for x in r['adversarial_cases'] if x['name']==name),'CASE_RESULT_'+name)
  outcomes.append({'name':name,'decision':result})
 need(sum(x['decision']=='INCOMPLETE_SYNTHETIC_REVIEW_NO_SEAL' for x in outcomes)==7,'INCOMPLETE_COUNT')
 for k in ('actual_acquisition_time_integration_implemented','live_simulator_launch_authorized','seal_binds_actual_capture_payloads','trusted_independent_witness','physical_time_synchronization_verified','independent_6dof_groundtruth_verified','existing_l42_database_modified','git_commit_or_push_performed'):
  need(r[k] is False,'UNAUTHORIZED_CLAIM_'+k)
 for k in ('actual_new_sensor_measurements','scientific_pose_factors','health_labels'):
  need(r[k]==0,'UNAUTHORIZED_PROMOTION_'+k)
 out={
  'schema':'TRUST_ROBOT_L43_INDEPENDENT_SESSION_VERIFICATION_V1',
  'parent_commit':BASE,
  'assessor_source_sha256':sha(a.assessor),
  'verifier_source_sha256':sha(__file__),
  'manifest_sha256':sha(a.manifest),
  'report_sha256':sha(a.report),
  'l42_readonly_registry_sha256':sha(db),
  'adversarial_cases_independently_rejected':len(outcomes),
  'partial_capture_cases_requiring_review':7,
  'verified_receipt_count':3,
  'synthetic_record_count':6,
  'live_simulator_launch_authorized':False,
  'real_sensor_samples':0,
  'source_authenticity_verified':False,
  'physical_sync_verified':False,
  'scientific_pose_factors':0,
  'health_labels':0,
 }
 with Path(a.validation).open('x',encoding='utf-8') as f:
  json.dump(out,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
 print('L43_INDEPENDENT_RECEIPT_CHAIN=VERIFIED')
 print('L43_INDEPENDENT_ADVERSARIAL_CONTROLS=50_REJECTED')
 print('L43_INDEPENDENT_PARTIAL_CAPTURE_CASES=7_REVIEW_REQUIRED')
 print('L43_INDEPENDENT_VALIDATION=PASS')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('assessor','manifest','report','validation','session','l42report','l42validation'):
  p.add_argument('--'+n,required=True)
 main(p.parse_args())
