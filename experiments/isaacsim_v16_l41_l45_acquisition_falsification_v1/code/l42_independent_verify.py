"""L42 independent read-only outbox and boundary evidence verification."""
import argparse
import copy
import hashlib
import json
import sqlite3
from pathlib import Path

BASE='8d5a1701df3e9d755ac0a4b5adda2845873f52eb'
PINS={
 'candidate':'4384b085f79dff51af5dbbf8a4c4bf4cae6deffc906bfbcaf8a8ef00a7e05dec',
 'guard':'b6bcabaf081bb1d6bf31b0ff907369bef841cf012d33b4ec407efd9bd6d94965',
 'protocol':'1df54c21a92bbf48387b48e1b78a0b71ea0298767005df7e3f7548f307a99736',
 'contract':'ee8dfaa3a0f95813d29efa68f65a3222a39cce5e12cf855c4c3508791dcc05f9',
 'fixture':'b2fa0728d1aa867d162bae7e463f7bf353b058222d2700eaf392cd271ed97736',
 'l41report':'67e0be9b1da5944cf41a3bfeccdfdd5110e5e672de6c4fc7370bf3fa1914e798',
 'l41validation':'e1507fa4233bc918246a518c4a3b56c474149f843030cd238d7887fcc91a3a84',
}
NAMES=('challenge_v1.json','admission_v1.json','seal_v1.json')
MUTATIONS=[
 ('wrong_parent',lambda r:r.update(parent_commit='0'*40)),
 ('wrong_builder',lambda r:r.update(builder_source_sha256='0'*64)),
 ('wrong_contract',lambda r:r.update(binding_contract_sha256='0'*64)),
 ('wrong_candidate',lambda r:r['source_sha256'].update(candidate='0'*64)),
 ('wrong_guard',lambda r:r['source_sha256'].update(guard='0'*64)),
 ('wrong_protocol',lambda r:r['source_sha256'].update(protocol='0'*64)),
 ('wrong_l41report',lambda r:r['source_sha256'].update(l41report='0'*64)),
 ('wrong_session',lambda r:r.update(session_id='FAKE')),
 ('wrong_nonce',lambda r:r.update(nonce_sha256='0'*64)),
 ('wrong_registry_digest',lambda r:r.update(registry_sha256='0'*64)),
 ('wrong_challenge_receipt',lambda r:r['outbox_receipts_sha256'].update(challenge_v1_json='0'*64) if False else r['outbox_receipts_sha256'].update({'challenge_v1.json':'0'*64})),
 ('wrong_admission_receipt',lambda r:r['outbox_receipts_sha256'].update({'admission_v1.json':'0'*64})),
 ('wrong_seal_receipt',lambda r:r['outbox_receipts_sha256'].update({'seal_v1.json':'0'*64})),
 ('wrong_outbox_count',lambda r:r.update(outbox_records=2)),
 ('wrong_final_stage',lambda r:r.update(registry_state='ADMITTED')),
 ('preflight_promoted',lambda r:r.update(pre_simulator_guard_denied=False)),
 ('seal_promoted',lambda r:r.update(postexport_guard_denied=False)),
 ('replay_accepted',lambda r:r.update(replay_admit_denied=False)),
 ('simulator_executed',lambda r:r.update(simulator_executed=True)),
 ('unexpected_payload',lambda r:r.update(actual_per_modality_payloads=1)),
 ('unexpected_measurement',lambda r:r.update(new_sensor_measurements=1)),
 ('physical_sync_claim',lambda r:r.update(physical_sync_verified=True)),
 ('hardware_claim',lambda r:r.update(hardware_attestation_verified=True)),
 ('pose_factor_claim',lambda r:r.update(pose_factors_authorized=1)),
 ('health_label_claim',lambda r:r.update(health_labels_generated=1)),
]

def need(value,msg):
 if not value:raise ValueError(msg)

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))

def check(r,p,expected):
 need(r['schema']=='TRUST_ROBOT_L42_OFFLINE_HOOK_OUTBOX_COMPATIBILITY_V1','Report schema')
 need(r['parent_commit']==BASE,'Git baseline')
 need(r['builder_source_sha256']==expected['builder'],'Builder source')
 need(r['binding_contract_sha256']==expected['contract_sha'],'Plan source')
 need(r['source_sha256']==PINS,'Source binding')
 need(r['session_id']==expected['session_id'],'Session id')
 need(r['nonce_sha256']==expected['nonce_hash'],'Nonce binding')
 need(r['registry_sha256']==expected['registry_sha'],'DB binding')
 need(r['outbox_receipts_sha256']==expected['receipt_hashes'],'Receipt binding')
 need(r['outbox_records']==3 and r['registry_state']=='SEALED','Outbox state')
 trace=r['subprocess_trace']
 need([entry['action'] for entry in trace]==[
     'issue','publish','admit','publish','replay_admit','seal','publish','replay_seal','status'
 ],'Subprocess event order')
 need(trace[0]['response']=='L40_ISSUE_STATE_COMMITTED_BEFORE_PUBLICATION=PASS','Issue trace')
 need(trace[2]['response']=='L40_ADMITTED_COMMITTED_WITH_OUTBOX=PASS','Admit trace')
 need(trace[4]['response'].startswith('L40_FAIL_CLOSED=ValueError:NONCE_OR_SESSION_ALREADY_CONSUMED'),'Replay admit trace')
 need(trace[5]['response']=='L40_SEALED_COMMITTED_WITH_OUTBOX=PASS','Seal trace')
 need(trace[7]['response'].startswith('L40_FAIL_CLOSED=ValueError:NONCE_OR_SESSION_ALREADY_CONSUMED'),'Replay seal trace')
 need(trace[8]['response']=='L40_FINAL_STATE=SEALED','Final status trace')
 for flag in ('pre_simulator_guard_denied','postexport_guard_denied','replay_admit_denied',
              'replay_seal_denied','offline_fixture_only'):
  need(r[flag] is True,'Flag '+flag)
 for flag in ('source_clock_verified','live_simulator_launch_authorized','simulator_executed',
              'physical_sync_verified','independent_source_authenticity_verified',
              'hardware_attestation_verified','independent_6dof_reference_verified',
              'real_power_loss_durability_verified','git_commit_or_push_performed'):
  need(r[flag] is False,'Unsafe claim '+flag)
 for field in ('actual_per_modality_payloads','new_sensor_measurements',
               'pose_factors_authorized','health_labels_generated'):
  need(r[field]==0,'Scientific promotion '+field)
 need(p['schema']=='TRUST_ROBOT_L42_HOOK_OUTBOX_BINDING_CONTRACT_V1','Contract schema')
 need(p['parent_commit']==BASE and p['source_sha256']==PINS,'Contract lineage')
 need(p['L40_outbox_bound_candidate_sha256']==PINS['candidate'],'Candidate/DB coupling')
 need(p['L40_outbox_fixture_sha256']==PINS['fixture'],'Fixture/DB coupling')
 need(p['hook_binding_mode']=='STATIC_HOOK_COMPATIBILITY_PLUS_SEPARATE_OFFLINE_OUTBOX_SESSION','Boundary scope')
 need([m['modality'] for m in p['future_modalities']]==['camera','lidar','imu'],'Modality coverage')
 for m in p['future_modalities']:
  need(m['capture_count']==0 and m['payload_hashes']==[] and
       m['capture_identity_verified'] is False and m['clock_semantics_verified'] is False,
       'Unauthorized modality evidence')
 for field in ('actual_scene_source_verified','new_runtime_metadata_rebound',
               'acquisition_time_receipt_binding_implemented','independent_hardware_witness_implemented',
               'live_simulator_launch_authorized'):
  need(p[field] is False,'Unqualified implementation claim')
 need(p['pose_factors_authorized']==0 and p['health_labels_generated']==0,'Contract science restriction')


def main(args):
 for key,expected in PINS.items():
  path=Path(getattr(args,key));need(path.is_file() and not path.is_symlink(),'Missing input '+key)
  need(sha(path)==expected,'Frozen input changed '+key)
 folder=Path(args.session);db=folder/'registry.sqlite';rec=folder/'receipts'
 need(db.is_file() and not db.is_symlink(),'DB missing')
 con=sqlite3.connect('file:'+str(db.resolve())+'?mode=ro',uri=True)
 try:
  con.execute('PRAGMA query_only=ON')
  need(con.execute('PRAGMA quick_check').fetchone()[0]=='ok','DB quick_check')
  sessions=con.execute('SELECT session_id,nonce_hash,state FROM sessions').fetchall()
  rows=con.execute('SELECT stage,payload,digest,published FROM outbox ORDER BY stage').fetchall()
 finally:con.close()
 need(len(sessions)==1 and sessions[0][2]=='SEALED','Session state')
 need(len(rows)==3,'Outbox count')
 digests={}
 for index,(stage,body,digest,published) in enumerate(rows):
  need(stage==index and published==1,'Stage publication')
  need(hashlib.sha256(body).hexdigest()==digest,'Outbox content integrity')
  path=rec/NAMES[index];need(path.is_file() and not path.is_symlink(),'Missing receipt')
  need(path.read_bytes()==body,'Published receipt equality')
  obj=json.loads(body)
  need(obj['session_id']==sessions[0][0] and obj['nonce_hash']==sessions[0][1],
       'Receipt session coupling')
  need(obj['candidate_sha256']==PINS['candidate'] and obj['contract_sha256']==PINS['contract']
       and obj['fixture_sha256']==PINS['fixture'],'Receipt source coupling')
  need(obj['new_sensor_measurements']==0 and obj['simulator_launch_authorized'] is False
       and obj['pose_factors_authorized']==0,'Receipt science restriction')
  if index:
   need(obj['prior_receipt_sha256']==rows[index-1][2],'Outbox predecessor chain')
  digests[NAMES[index]]=digest
 plan=load(args.plan);report=load(args.report)
 expected={
  'builder':sha(args.builder),'contract_sha':sha(args.plan),
  'session_id':sessions[0][0],'nonce_hash':sessions[0][1],
  'registry_sha':sha(db),'receipt_hashes':digests,
 }
 check(report,plan,expected)
 denied=[]
 for name,mutate in MUTATIONS:
  candidate=copy.deepcopy(report)
  mutate(candidate)
  try:check(candidate,plan,expected)
  except (ValueError,KeyError,TypeError):denied.append(name)
  else:raise ValueError('Rejected test unexpectedly accepted: '+name)
 need(len(denied)==25 and len(set(denied))==25,'Mutation coverage')
 result={
  'schema':'TRUST_ROBOT_L42_INDEPENDENT_BRIDGE_VALIDATION_V1',
  'parent_commit':BASE,
  'builder_source_sha256':sha(args.builder),
  'verifier_source_sha256':sha(__file__),
  'binding_contract_sha256':sha(args.plan),
  'bridge_report_sha256':sha(args.report),
  'registry_snapshot_sha256':sha(db),
  'receipt_sha256':digests,
  'verified_adversarial_mutations':denied,
  'verified_adversarial_count':len(denied),
  'outbox_rows_verified':3,
  'runtime_hooks_remain_denied':True,
  'live_launch_authorized':False,
  'new_sensor_measurements':0,
  'scientific_pose_factors':0,
  'health_labels':0,
  'hardware_witness_verified':False,
  'physical_sync_verified':False,
 }
 with Path(args.validation).open('x',encoding='utf-8') as f:
  json.dump(result,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
 print('L42_OUTBOX_RECEIPT_CHAIN=VERIFIED')
 print('L42_FROZEN_RUNTIME_HOOK_DENIAL=VERIFIED')
 print('L42_INDEPENDENT_ADVERSARIAL_MUTATIONS=25_REJECTED')
 print('L42_INDEPENDENT_VALIDATION=PASS')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for key in (*PINS,'builder','session','plan','report','validation'):
  p.add_argument('--'+key,required=True)
 main(p.parse_args())
