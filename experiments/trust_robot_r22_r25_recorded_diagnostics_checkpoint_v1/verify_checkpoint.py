"""Standalone, no-ROS, no-bag SHA and scientific-gate R22-R25 verifier.

Reads only committed small code/reports and commit-scoped project docs.
Does not call the original experimental engines or read any raw ROS message.
"""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
BASE='76685f1a6a97fb8e0750224bb927f1b094e63203'
BAG='ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1'
TOPICS={
 '/camera/color/image_raw/compressed':1113,
 '/camera/imu':13858,
 '/handsfree/imu':10426,
 '/velodyne_points':752,
}
COUNTS={'r22':5,'r23':5,'r24':6,'r25':9}
PINS={
 'r22/r22_recorded_content_diagnostics_v1.json':'5f6f3d4e9e3a8e7b49614a8a56ba1cd560d5ccc5b57eae397258f170f03ce849',
 'r22/r22_independent_validation_v1.json':'fb1438277b2099e04fff0b4b0c554d3f4bc010d6fc84a4b8965e80b8ad380b60',
 'r23/r23_train_coverage_diagnostics_v1.json':'8b92dd3e487fa648533d17a5f7c3c5c93c6b4ff4d7e0f299c6a473277a571abd',
 'r23/r23_independent_validation_v1.json':'9c93ed032ae9bb214507a28ebd4bf1b0463baf8257401681b99f32042a99e47b',
 'r24/r24_recorded_diagnostic_stress_v1.json':'f153153549e5ac8701fce637b4168e04e1b482feeba971608a7840f28063b677',
 'r24/r24_independent_validation_v1.json':'3026526d5deb34990ba2921e2057b527cdc4d6f1ffe5990b50976d9ff7fd3ff7',
 'r25/r25_readiness_report_v1.json':'23674298708444aa77cd9aee149f754d9bc6658a65a0678e3463962a6f6d7631',
 'r25/r25_independent_validation_v1.json':'b5172b005e4e8ac9412b6a413ef58be8e9ca8b490131631b7d18ed06cbdbae95',
 'r25/r25_frontend_regressions.xml':'8b6ad20b908013b28fe8ef8240ac995267db463732130b74990545764efc1d2b',
}

def need(ok,name):
 if not ok:raise ValueError('R22_R25_ARCHIVE_DENIED:'+name)
def sha(path):
 path=Path(path)
 need(path.is_file() and not path.is_symlink() and path.stat().st_nlink==1 and 0<path.stat().st_size<5_000_000,'UNSAFE_FILE:'+str(path))
 return hashlib.sha256(path.read_bytes()).hexdigest()
def load(rel):return json.loads((ROOT/rel).read_text(encoding='utf-8'))
def ensure_false(mapping,keys,label):
 for key in keys:need(mapping.get(key) is False,label+':'+key)
def ensure_zero(mapping,keys,label):
 for key in keys:need(type(mapping.get(key)) is int and mapping[key]==0,label+':'+key)

m=load('checkpoint_manifest_v1.json')
need(m['schema']=='TRUST_ROBOT_R22_R25_RECORDED_DIAGNOSTIC_CHECKPOINT_V1' and m['branch']=='kios-isaacsim-v15-integration' and m['parent_commit']==BASE,'MANIFEST')
need(m['authenticated_bag_sha256']==BAG and m['bag_archived'] is False and m['split']=='train','SOURCE_SCOPE')
need(m['phase_counts']==COUNTS and len(m['frozen_sha256'])==25 and set(m['phase_files'])==set(COUNTS),'PHASE_INVENTORY')
need(set.union(*(set(m['phase_files'][k]) for k in COUNTS))==set(m['frozen_sha256']),'PHASE_MEMBERSHIP')
need(all(len(m['phase_files'][k])==COUNTS[k] for k in COUNTS),'PHASE_LENGTHS')
need(set(m['file_sha256'])==set(m['frozen_sha256'])|{'README.md'},'FILE_HASH_SET')
need(set(PINS).issubset(m['frozen_sha256']) and all(m['frozen_sha256'][k]==v for k,v in PINS.items()),'PINNED_REPORTS')
actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()}
need(actual==set(m['file_sha256'])|{'checkpoint_manifest_v1.json','verify_checkpoint.py'},'EXACT_ARCHIVE_FILE_SET')
need(not any(p.is_symlink() for p in ROOT.rglob('*')),'SYMLINK')
for rel,desired in m['file_sha256'].items():
 pure=PurePosixPath(rel)
 need(not pure.is_absolute() and '..' not in pure.parts and pure.suffix in ('.py','.json','.xml','.md') and re.fullmatch('[0-9a-f]{64}',desired),'SAFE_PATH_OR_HASH')
 need(sha(ROOT/rel)==desired,'FILE_SHA:'+rel)
 if rel.endswith('.py'):ast.parse((ROOT/rel).read_text(),filename=rel)
 if rel.endswith('.json'):load(rel)
 if rel.endswith('.xml'):ET.parse(ROOT/rel)
need(all(m['file_sha256'][k]==v for k,v in m['frozen_sha256'].items()),'SOURCE_PINS')
prior=REPO/'experiments/trust_robot_r17_r20_recorded_input_checkpoint_v1'
need(sha(prior/'checkpoint_manifest_v1.json')==m['prior_checkpoint_manifest_sha256'] and
     sha(prior/'verify_checkpoint.py')==m['prior_checkpoint_verifier_sha256'],'PRIOR_CHECKPOINT_HASHES')
need(sha(REPO/'manifests/m2dgr_trajectory_manifest_v1_split_freeze_v1.json')==m['frozen_m2dgr_manifest_sha256'],'FROZEN_SPLIT_HASH')
expected_docs={'AGENTS.md','docs/TRUST_ROBOT_PROJECT_STATE.md','docs/audits/trust_robot/TRUST_ROBOT_KIOS_R22_R25_RECORDED_DIAGNOSTICS_V1.md'}
need(set(m['documentation_sha256'])==expected_docs,'DOC_PATHS')
rel=str((ROOT/'checkpoint_manifest_v1.json').relative_to(REPO))
commit=subprocess.check_output(['git','-C',str(REPO),'rev-list','-1','HEAD','--',rel],text=True).strip()
if commit:
 need(subprocess.check_output(['git','-C',str(REPO),'rev-parse',commit+'^'],text=True).strip()==BASE,'GIT_PARENT')
for doc,expected in m['documentation_sha256'].items():
 blob=(subprocess.check_output(['git','-C',str(REPO),'show',commit+':'+doc]) if commit else (REPO/doc).read_bytes())
 need(hashlib.sha256(blob).hexdigest()==expected,'DOCUMENT_HASH:'+doc)

r22,v22,r23,v23,r24,v24,r25,v25=[load(k) for k in (
 'r22/r22_recorded_content_diagnostics_v1.json',
 'r22/r22_independent_validation_v1.json',
 'r23/r23_train_coverage_diagnostics_v1.json',
 'r23/r23_independent_validation_v1.json',
 'r24/r24_recorded_diagnostic_stress_v1.json',
 'r24/r24_independent_validation_v1.json',
 'r25/r25_readiness_report_v1.json',
 'r25/r25_independent_validation_v1.json')]
need([x.get('trajectory_id') for x in (r22,r23,r24,r25)]==['room_02']*4 and
     [x.get('split') for x in (r22,r23,r24,r25)]==['train']*4,'TRAIN_ONLY')
need(r22.get('schema')=='TRUST_ROBOT_R22_TRAIN_ONLY_SIGNAL_DIAGNOSTICS_V1' and
     r23.get('schema')=='TRUST_ROBOT_R23_INDEX_STRATIFIED_TRAIN_DIAGNOSTICS_V1' and
     r24.get('schema')=='TRUST_ROBOT_R24_TRAIN_RECORDED_DIAGNOSTIC_STRESS_V1' and
     r25.get('schema')=='TRUST_ROBOT_R25_RECORDED_FRONTEND_CHECKPOINT_READINESS_V1','PHASE_SCHEMAS')
need(all(x.get('bag_sha256')==BAG for x in (r22,r23,r24)) and r25['authenticated_bag_sha256']==BAG,'BAG_CHAIN')
need(r22['sample_count']==8 and r22['sensor_stream_count']==4 and set(r22['signals'])==set(TOPICS),'R22_COUNTS')
need(r23['sampled_message_count']==32 and r23['selected_per_topic']==8 and r23['inspected_unique_chunk_count']==30 and r23['indexed_required_stream_messages']==26149 and set(r23['per_topic'])==set(TOPICS),'R23_COUNTS')
for topic,count in TOPICS.items():
 samples=r22['signals'][topic]; row=r23['per_topic'][topic]
 need(len(samples)==2 and len(row['observations'])==8 and row['index_record_count']==count,'SENSOR_COUNTS:'+topic)
 need(row['qualitative_stability_inference_authorized'] is False,'STABILITY_GATE:'+topic)
 need(samples[0]['source']['serialized_message_sha256']==row['observations'][0]['source']['serialized_message_sha256'],'EARLY_SAMPLE_SHA:'+topic)
need(r24['original_selected_messages']==32 and r24['original_chunks_read']==30 and
     r24['message_integrity_and_provenance_challenges_rejected']==128 and
     r24['semantic_payload_challenges_rejected']==8 and r24['lidar_nonfinite_frontend_rejections']==2,'R24_CHALLENGES')
need(r25['targeted_frontend_regressions_passed']==197 and r25['counts']=={
 'topics':list(TOPICS),'indexed_required_messages':26149,'source_chunks':5182,
 'r22_samples':8,'r23_samples':32,'r23_distinct_chunks':30,
 'integrity_mutations_rejected':128,'semantic_mutations_rejected':8,
 'nonfinite_lidar_frontend_denials':2,'recorded_pose_factors':0,'health_labels':0},'R25_COUNTS')
need(r25['readiness_decision']=='READY_FOR_SHA_PINNED_R22_R25_NONFACTOR_GIT_ARCHIVAL' and r25['parent_git_commit']==BASE and r25['descriptive_sample_coverage_not_statistically_qualified'] is True,'R25_DECISION')
need(r25['source_report_sha256']['r22']==sha(ROOT/'r22/r22_recorded_content_diagnostics_v1.json') and
     r25['source_report_sha256']['v22']==sha(ROOT/'r22/r22_independent_validation_v1.json') and
     r25['source_report_sha256']['r23']==sha(ROOT/'r23/r23_train_coverage_diagnostics_v1.json') and
     r25['source_report_sha256']['v23']==sha(ROOT/'r23/r23_independent_validation_v1.json') and
     r25['source_report_sha256']['r24']==sha(ROOT/'r24/r24_recorded_diagnostic_stress_v1.json') and
     r25['source_report_sha256']['v24']==sha(ROOT/'r24/r24_independent_validation_v1.json'),'CROSS_PHASE_SOURCE_LINK')
for k,rel,original in (
 ('r22','r22/r22_independent_validation_v1.json',v22),
 ('r23','r23/r23_independent_validation_v1.json',v23),
 ('r24','r24/r24_independent_validation_v1.json',v24)):
 need(sha(ROOT/('r25/r25_'+k+'_independent_replay.json'))==sha(ROOT/rel),'INDEPENDENT_REPLAY:'+k)
need(v25['verification']=='PASS' and v25['r25_report_sha256']==sha(ROOT/'r25/r25_readiness_report_v1.json') and
     v25['r25_junit_sha256']==sha(ROOT/'r25/r25_frontend_regressions.xml') and v25['regression_tests']==197,'R25_INDEPENDENT')
cases=list(ET.parse(ROOT/'r25/r25_frontend_regressions.xml').getroot().iter('testcase'))
need(len(cases)==197 and len({(x.get('classname'),x.get('name')) for x in cases})==197 and
     not any(c.tag in ('error','failure','skipped') for case in cases for c in case),'JUNIT_197')
need(r25['regression_junit_sha256']==sha(ROOT/'r25/r25_frontend_regressions.xml'),'R25_XML_SHA')
ensure_false(r22,('health_features_frozen','cross_modal_alignment_performed','physical_time_semantics_verified','sensor_extrinsics_verified','real_sensor_factor_execution_authorized','raw_recording_modified','github_modified'),'R22_GATE')
ensure_false(r23,('health_features_selected','statistical_stability_established','cross_modal_pairing_performed','physical_capture_sync_verified','extrinsics_verified','real_sensor_factor_execution_authorized','raw_bag_modified','github_modified'),'R23_GATE')
ensure_false(r24,('recorded_source_files_written','original_recording_modified','health_features_frozen','statistical_stability_established','cross_modal_alignment_performed','physical_synchronization_verified','full_extrinsics_verified','ground_truth_scored','real_sensor_factor_execution_authorized','git_modified'),'R24_GATE')
ensure_false(r25,('recorded_data_source_mutated','raw_sensor_payload_embedded','physical_capture_time_verified','cross_modal_sync_verified','sensor_extrinsics_verified','independent_reference_qualified','health_model_training_authorized','real_sensor_factor_execution_authorized','m2dgr_scoring_authorized','live_simulator_launch_authorized','github_modified'),'R25_GATE')
for d,keys,name in ((r22,('real_pose_factors_generated','health_labels_generated'),'R22'),(r23,('real_pose_factors_generated','health_labels_created'),'R23'),(r24,('real_pose_factors_generated','health_labels'),'R24'),(r25,('scientific_pose_factors','health_labels'),'R25')):ensure_zero(d,keys,name)
for gate in ('real_sensor_factor_execution_authorized','m2dgr_scoring_authorized','health_model_training_authorized','live_simulator_launch_authorized'):
 need(m[gate] is False,'MANIFEST_GATE:'+gate)
for key in ('scientific_pose_factors','health_labels'):need(type(m[key]) is int and m[key]==0,'MANIFEST_COUNT:'+key)
print('R22_R25_ARCHIVE_INDEPENDENT_VERIFIER=PASS')
print('R22_R25_FROZEN_SMALL_FILE_HASHES=25_VERIFIED')
print('R22_R25_AUTHENTIC_TRAIN_SOURCE_BINDING=VERIFIED')
print('R22_R25_INDEPENDENT_REPLAY_HASHES=3_MATCHED')
print('R22_R25_R24_NEGATIVE_CONTROLS=128_PLUS_8_VERIFIED')
print('R22_R25_R25_REGRESSIONS=197_VERIFIED')
print('R22_R25_DOCUMENTATION_COMMIT_SCOPED_SHA=VERIFIED')
print('R22_R25_RAW_BAG_IN_GIT=NO')
print('R22_R25_REAL_SENSOR_FACTOR_ADMISSION=DENIED')
