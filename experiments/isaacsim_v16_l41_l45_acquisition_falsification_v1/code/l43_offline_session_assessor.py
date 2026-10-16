"""L43 offline-only simulated capture-session binding and partial-capture tests.

No actual payload measurement, live hook wiring, or cryptographic source
attestation. Consistent forged metadata could pass; model is a contract test.
"""
import argparse, copy, hashlib, json, sqlite3
from pathlib import Path

BASE='8d5a1701df3e9d755ac0a4b5adda2845873f52eb'
PINS={
 'l42source':'604aab4d79548261b0ab7c99abfa8b4ba2f77b07b9a2447c8a61627a4aee4981',
 'l42verifier':'47eb2ca0696986f456a78d59c5eb85fbab232c656f70e743dd6c24a5f9feb0d9',
 'l42plan':'1b4acef236b12b58d912b20a8c920835e44f44f23fc517fe325f799b5638836d',
 'l42report':'cb4beb8acb5888e93aa1b041adf6971290f76b25840953ca7b747472caaa2573',
 'l42validation':'be450eee7acc97b10e17acb8bf826e3958196ba7bbb46af5613c413ef4fe40ac',
 'l41report':'67e0be9b1da5944cf41a3bfeccdfdd5110e5e672de6c4fc7370bf3fa1914e798',
 'candidate':'4384b085f79dff51af5dbbf8a4c4bf4cae6deffc906bfbcaf8a8ef00a7e05dec',
 'guard':'b6bcabaf081bb1d6bf31b0ff907369bef841cf012d33b4ec407efd9bd6d94965',
 'outbox':'1df54c21a92bbf48387b48e1b78a0b71ea0298767005df7e3f7548f307a99736',
 'contract':'ee8dfaa3a0f95813d29efa68f65a3222a39cce5e12cf855c4c3508791dcc05f9',
 'fixture':'b2fa0728d1aa867d162bae7e463f7bf353b058222d2700eaf392cd271ed97736',
}
MODALITIES=('camera','lidar','imu')
NAMES=('challenge_v1.json','admission_v1.json','seal_v1.json')

def need(v,s):
 if not v:raise ValueError(s)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def bytes_sha(data):return hashlib.sha256(data).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,obj):
 with Path(p).open('x',encoding='utf-8') as f:
  json.dump(obj,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')

def ground(a):
 for k,h in PINS.items():
  p=Path(getattr(a,k));need(p.is_file() and not p.is_symlink() and p.stat().st_nlink==1,'UNSAFE_'+k)
  need(sha(p)==h,'FROZEN_HASH_'+k)
 l42=load(a.l42report);v42=load(a.l42validation);plan=load(a.l42plan);l41=load(a.l41report)
 need(l42['schema']=='TRUST_ROBOT_L42_OFFLINE_HOOK_OUTBOX_COMPATIBILITY_V1','L42_SCHEMA')
 need(l42['source_sha256']['candidate']==PINS['candidate'],'L42_CANDIDATE')
 need(l42['builder_source_sha256']==PINS['l42source'] and l42['binding_contract_sha256']==PINS['l42plan'],'L42_SOURCE_BINDING')
 need(v42['bridge_report_sha256']==PINS['l42report'] and v42['verified_adversarial_count']==25,'L42_VALIDATION')
 need(plan['acquisition_time_receipt_binding_implemented'] is False,'INCORRECT_L42_PROMOTION')
 need(l41['readiness_verdict']=='LIVE_CAPTURE_DENIED_SCIENCE_GATES_CLOSED','L41_GATE')
 folder=Path(a.session);db=folder/'registry.sqlite'
 need(db.is_file() and not db.is_symlink() and l42['registry_sha256']==sha(db),'L42_REGISTRY_HASH')
 con=sqlite3.connect('file:'+str(db.resolve())+'?mode=ro',uri=True)
 try:
  con.execute('PRAGMA query_only=ON')
  need(con.execute('PRAGMA quick_check').fetchone()[0]=='ok','L42_DB_CHECK')
  sessions=con.execute('SELECT session_id,nonce_hash,state FROM sessions').fetchall()
  rows=con.execute('SELECT stage,payload,digest,published FROM outbox ORDER BY stage').fetchall()
 finally: con.close()
 need(len(sessions)==1 and sessions[0][2]=='SEALED','L42_DB_SESSION')
 need(len(rows)==3,'L42_DB_OUTBOX')
 digests={}
 for i,(stage,body,digest,published) in enumerate(rows):
  need(stage==i and published==1 and bytes_sha(body)==digest,'L42_OUTBOX_ROW')
  rp=folder/'receipts'/NAMES[i]
  need(rp.is_file() and not rp.is_symlink() and rp.read_bytes()==body,'L42_RECEIPT_BYTES')
  obj=json.loads(body)
  need(obj['session_id']==sessions[0][0] and obj['nonce_hash']==sessions[0][1],'L42_RECEIPT_IDENTITY')
  need(obj['candidate_sha256']==PINS['candidate'] and obj['contract_sha256']==PINS['contract'] and obj['fixture_sha256']==PINS['fixture'],'L42_RECEIPT_LINEAGE')
  need(obj['simulator_launch_authorized'] is False and obj['new_sensor_measurements']==0,'L42_RECEIPT_SCOPE')
  if i:need(obj['prior_receipt_sha256']==rows[i-1][2],'L42_RECEIPT_CHAIN')
  digests[NAMES[i]]=digest
 need(l42['session_id']==sessions[0][0] and l42['nonce_sha256']==sessions[0][1],'L42_REPORT_IDENTITY')
 need(l42['outbox_receipts_sha256']==digests,'L42_REPORT_OUTBOX')
 need(l42['pre_simulator_guard_denied'] is True and l42['postexport_guard_denied'] is True,'L42_GUARDS')
 return {'session_id':sessions[0][0],'nonce_hash':sessions[0][1],'receipts':digests,'db_sha':sha(db)}

def evt(g,mod,counter):
 sid=g['session_id'];run='L43_SYNTHETIC_'+sid
 return {
  'capture_event_id':f'{sid}:{mod}:{counter}',
  'capture_counter':counter,
  'modality_id':mod,
  'session_id':sid,
  'run_id':run,
  'nonce_hash':g['nonce_hash'],
  'challenge_receipt_sha256':g['receipts']['challenge_v1.json'],
  'admission_receipt_sha256':g['receipts']['admission_v1.json'],
  'seal_receipt_sha256':g['receipts']['seal_v1.json'],
  'candidate_source_sha256':PINS['candidate'],
  'synthetic_payload_sha256':bytes_sha(f'L43_NOT_SENSOR|{sid}|{mod}|{counter}'.encode()),
  'timestamp_clock_domain':'OFFLINE_SYNTHETIC_UNTRUSTED',
  'untrusted_time_tick':MODALITIES.index(mod)*10+counter,
  'physical_capture_verified':False,
 }

def manifest(g):
 return {
  'schema':'TRUST_ROBOT_L43_SYNTHETIC_SESSION_MANIFEST_V1',
  'parent_git_commit':BASE,
  'session_id':g['session_id'],
  'nonce_hash':g['nonce_hash'],
  'run_id':'L43_SYNTHETIC_'+g['session_id'],
  'registry_snapshot_sha256':g['db_sha'],
  'challenge_receipt_sha256':g['receipts']['challenge_v1.json'],
  'admission_receipt_sha256':g['receipts']['admission_v1.json'],
  'seal_receipt_sha256':g['receipts']['seal_v1.json'],
  'candidate_source_sha256':PINS['candidate'],
  'guard_source_sha256':PINS['guard'],
  'interface_contract_sha256':PINS['contract'],
  'fixture_transcript_sha256':PINS['fixture'],
  'declared_expected_counts':{'camera':2,'lidar':2,'imu':2},
  'events':[evt(g,m,n) for m in MODALITIES for n in (1,2)],
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
  'scientific_pose_factors':0,
  'health_labels':0,
 }

def assess(m,g):
 try:
  reference=manifest(g)
  need(type(m) is dict and set(m)==set(reference),'MANIFEST_FIELDS')
  for key in reference:
   if key!='events':need(m[key]==reference[key],'MANIFEST_'+key)
  need(type(m['events']) is list and len(m['events'])<=6,'EVENT_COUNT')
  reference_events=reference['events'];indices=[]
  for event in m['events']:
   need(type(event) is dict,'EVENT_FORMAT')
   matches=[i for i,e in enumerate(reference_events) if e==event]
   need(len(matches)==1,'EVENT_IDENTITY_OR_PAYLOAD')
   indices.append(matches[0])
  need(indices==sorted(set(indices)),'EVENT_DUPLICATE_OR_ORDER')
  if len(indices)<6:
   return 'INCOMPLETE_SYNTHETIC_REVIEW_NO_SEAL'
  need(indices==list(range(6)),'COMPLETE_EVENT_SET')
  return 'COMPLETE_SYNTHETIC_NOT_ACQUISITION'
 except (ValueError,KeyError,TypeError,IndexError):
  return 'QUARANTINED'

def mutations(base):
 """Deliberate metadata and omission mutations; no actual sensor data."""
 cases=[]
 def edit(name,fn):
  c=copy.deepcopy(base);fn(c);cases.append((name,c))
 for name,key,val in [
  ('wrong_parent','parent_git_commit','0'*40),
  ('wrong_schema','schema','INVALID'),
  ('wrong_session','session_id','CROSS_SESSION'),
  ('wrong_nonce','nonce_hash','0'*64),
  ('wrong_challenge','challenge_receipt_sha256','0'*64),
  ('wrong_admission','admission_receipt_sha256','0'*64),
  ('wrong_seal','seal_receipt_sha256','0'*64),
  ('wrong_candidate','candidate_source_sha256','0'*64),
  ('wrong_guard','guard_source_sha256','0'*64),
  ('wrong_contract','interface_contract_sha256','0'*64),
  ('wrong_fixture','fixture_transcript_sha256','0'*64),
  ('wrong_runid','run_id','REPLAYED_RUN'),
  ('wrong_registry','registry_snapshot_sha256','0'*64),
 ]:
  edit(name,lambda a,k=key,v=val:a.update({k:v}))
 for name,key,val in [
  ('event_wrong_session','session_id','CROSS_SESSION'),
  ('event_wrong_runid','run_id','OTHER_RUN'),
  ('event_wrong_nonce','nonce_hash','0'*64),
  ('event_wrong_challenge','challenge_receipt_sha256','0'*64),
  ('event_wrong_admission','admission_receipt_sha256','0'*64),
  ('event_wrong_seal','seal_receipt_sha256','0'*64),
  ('event_wrong_candidate','candidate_source_sha256','0'*64),
  ('event_wrong_modality','modality_id','unknown'),
  ('event_wrong_counter','capture_counter',99),
  ('event_negative_counter','capture_counter',-1),
  ('event_wrong_event_id','capture_event_id','DUPLICATE'),
  ('event_wrong_payload_hash','synthetic_payload_sha256','f'*64),
  ('event_malformed_payload_hash','synthetic_payload_sha256','invalid'),
  ('event_wrong_clock_domain','timestamp_clock_domain','PHYSICAL_TRUSTED'),
  ('event_clock_decrease','untrusted_time_tick',0),
 ]:
  edit(name,lambda a,k=key,v=val:a['events'][0].update({k:v}))
 for name,func in [
  ('drop_one_camera',lambda a:a['events'].pop(0)),
  ('drop_one_lidar',lambda a:a['events'].pop(2)),
  ('drop_one_imu',lambda a:a['events'].pop(4)),
  ('drop_both_camera',lambda a:a.update(events=[x for x in a['events'] if x['modality_id']!='camera'])),
  ('drop_both_lidar',lambda a:a.update(events=[x for x in a['events'] if x['modality_id']!='lidar'])),
  ('drop_both_imu',lambda a:a.update(events=[x for x in a['events'] if x['modality_id']!='imu'])),
  ('duplicate_event',lambda a:a['events'].__setitem__(1,copy.deepcopy(a['events'][0]))),
  ('add_extra_event',lambda a:a['events'].append(copy.deepcopy(a['events'][-1]))),
  ('reorder_events',lambda a:a['events'].reverse()),
  ('counter_gap',lambda a:a['events'][1].update(capture_counter=3)),
  ('empty_event_set',lambda a:a.update(events=[])),
 ]: edit(name,func)
 for name,key,value in [
  ('live_launch_claim','live_simulator_launch_authorized',True),
  ('physical_payload_claim','independent_payload_authenticity_verified',True),
  ('physical_sync_claim','physical_exposure_sync_verified',True),
  ('independent_groundtruth_claim','independent_6dof_reference_verified',True),
  ('pose_factor_claim','scientific_pose_factors',1),
  ('health_label_claim','health_labels',1),
  ('new_measurement_claim','actual_sensor_measurements',1),
  ('seal_capture_claim','seal_binds_actual_capture_payloads',True),
  ('hardware_witness_claim','independent_hardware_witness_verified',True),
  ('multi_host_claim','multi_host_replay_protection_verified',True),
  ('trusted_clock_claim','trusted_clock_verified',True),
 ]:edit(name,lambda a,k=key,v=value:a.update({k:v}))
 return cases

def main(a):
 g=ground(a);m=manifest(g)
 need(assess(m,g)=='COMPLETE_SYNTHETIC_NOT_ACQUISITION','BASELINE_DENIED')
 cases=mutations(m);need(len(cases)==50 and len(set(n for n,_ in cases))==50,'CASE_INVENTORY')
 results=[]
 for name,sample in cases:
  decision=assess(sample,g)
  need(decision!='COMPLETE_SYNTHETIC_NOT_ACQUISITION','ADVERSARY_ACCEPTED_'+name)
  results.append({'name':name,'decision':decision})
 need(sum(c['decision']=='INCOMPLETE_SYNTHETIC_REVIEW_NO_SEAL' for c in results)==7,'PARTIAL_CAPTURE_COVERAGE')
 save(a.manifest,m)
 report={
  'schema':'TRUST_ROBOT_L43_SESSION_BINDING_PARTIAL_CAPTURE_VALIDATION_V1',
  'parent_commit':BASE,'assessor_source_sha256':sha(__file__),
  'synthetic_manifest_sha256':sha(a.manifest),
  'l42_plan_sha256':PINS['l42plan'],'l42_report_sha256':PINS['l42report'],
  'l42_validation_sha256':PINS['l42validation'],
  'frozen_source_sha256':PINS,'l42_session_id':g['session_id'],
  'l42_nonce_sha256':g['nonce_hash'],'l42_registry_sha256':g['db_sha'],
  'l42_receipts_sha256':g['receipts'],
  'complete_synthetic_manifest_decision':'COMPLETE_SYNTHETIC_NOT_ACQUISITION',
  'adversarial_cases':results,'adversarial_cases_rejected':len(results),
  'incomplete_cases_require_review':7,
  'synthetic_event_count':len(m['events']),
  'synthetic_modalities':list(MODALITIES),
  'actual_acquisition_time_integration_implemented':False,
  'live_simulator_launch_authorized':False,
  'actual_new_sensor_measurements':0,
  'seal_binds_actual_capture_payloads':False,
  'trusted_independent_witness':False,
  'physical_time_synchronization_verified':False,
  'independent_6dof_groundtruth_verified':False,
  'scientific_pose_factors':0,'health_labels':0,
  'existing_l42_database_modified':False,'git_commit_or_push_performed':False,
  'limitations':['Synthetic metadata is not sensor data',
   'The archived L40 seal does not bind actual per-sensor capture payloads',
   'A fully consistent attacker-controlled rewrite is not prevented by self-hashing',
   'No independent issuer, trusted sensor hardware, or real-time clock proved'],
  'next':'L44_INCOMPLETE_CAPTURE_COMMIT_BOUNDARY_AND_FAIL_CLOSED_RECOVERY',
 }
 save(a.report,report)
 print('L43_SYNTHETIC_SESSION_BINDING=VERIFIED')
 print('L43_ADVERSARIAL_SESSION_CONTROLS='+str(len(results))+'_REJECTED')
 print('L43_PARTIAL_CAPTURE_REVIEW_CASES=7')
 print('L43_SENSOR_PAYLOAD_ATTESTATION=NOT_IMPLEMENTED')
 print('L43_OFFLINE_FALSIFICATION=PASS')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for name in (*PINS,'session','manifest','report'):
  p.add_argument('--'+name,required=True)
 main(p.parse_args())
