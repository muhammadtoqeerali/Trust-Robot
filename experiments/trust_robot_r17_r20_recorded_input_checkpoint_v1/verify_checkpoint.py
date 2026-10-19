"""Independent, no-raw-bag R17-R20 SHA-pinned recorded-input archive verifier."""
import ast, hashlib, json, pathlib, subprocess, xml.etree.ElementTree as ET
ROOT=pathlib.Path(__file__).resolve().parent
REPO=ROOT.parents[1]
BASE='0dddf4eda57cd629db4c5ee63cdbf645b17fb31d'
BAG='ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1'
TOPICS={
 '/camera/color/image_raw/compressed':1113,
 '/camera/imu':13858,
 '/handsfree/imu':10426,
 '/velodyne_points':752,
}
PINNED={
 'r17/r17_recorded_index.json':'4e904e29f507519e4447642edec55954b672aae2c305ff513bd6aa857c92a5af',
 'r18/r18_bounded_recorded_samples.json':'68accc1d4ab7b4c131bd60767be249054ba2469fad266292f615b6619d969bfa',
 'r19/r19_recorded_frontend_contract_v1.json':'2b64ddc82600c0051a72e7f31eb2e66e2ab5a8a26980c2d7b53bb9c51eeea557',
 'r20/r20_recorder_readiness_review_v1.json':'116d6323a2e32109f8ae1ce6be7e9cf4e6622438293ae3c2a59dbc9affaa667e',
 'r20/r20_independent_validation_v1.json':'07ae29b60b1e3f60a2080d424dc5dfa4279b3bf19fb40a365a3dec2ea578319e',
 'r20/r20_frontend_regressions.xml':'e98d9cd2d5f8ee66e8dee9903489de7304f76a8d224b646f473d0d7c0fd2b00e',
 'r18/r18_decode_original_failed_v1.py.saved':'1ccd923c1559b77d4cbbba0f9b2799353904e78597c44f950247929f7a4e8874',
 'r18/r18_verify_original_failed_v1.py.saved':'ccee5d064e24e9daf4d1c080ad2257d8d1e95594426f7947751acf2cbb4054f6',
 'r18/r18_op7_patch_v1.py':'a421083456327f10c9c13526f27a8599154130f628e91153827ebe60e90fc5f8',
}
def need(ok,why):
 if not ok:raise ValueError('R17_R20_CHECKPOINT_FAIL:'+why)
def digest(blob):return hashlib.sha256(blob).hexdigest()
def sha(path):
 path=pathlib.Path(path)
 need(path.is_file() and not path.is_symlink() and path.stat().st_nlink==1 and 0<path.stat().st_size<=3_000_000,'UNSAFE_FILE:'+str(path))
 return digest(path.read_bytes())
def data(rel):return json.loads((ROOT/rel).read_text(encoding='utf-8'))
def receipt_links(a,b,c):
 seen=set(); count=0
 for topic,n in TOPICS.items():
  samples=b['samples'][topic]
  need(len(samples)==2,'SAMPLE_LENGTH:'+topic)
  for index,s in enumerate(samples):
   ident=(s['chunk_offset'],s['connection_id'],s['bag_record_time_ns'],s['serialized_message_sha256'])
   need(ident not in seen,'DUPLICATE_SAMPLE')
   seen.add(ident)
   need(type(s['serialized_message_bytes']) is int and s['serialized_message_bytes']>16 and len(s['serialized_message_sha256'])==64,'SAMPLE_SHA')
   if topic!='/velodyne_points':
    item=c['camera_imu_existing_adapter_receipts'][topic][index];r=item['receipt']
    need(r['source_stream_id']==topic and r['split_role']=='train' and r['trajectory_or_session_id']=='room_02','CAMERA_IMU_RECEIPT_ID')
    need(r['serialized_payload_sha256']==s['serialized_message_sha256'] and r['serialized_payload_size_bytes']==s['serialized_message_bytes'] and r['bag_record_time_ns']==s['bag_record_time_ns'] and r['header_stamp_ns']==s['header_stamp_ns'],'RECEIPT_SOURCE')
    need(r['timing_semantics']['shared_clock_domain_verified'] is False and r['health_boundary']['health_label_assigned'] is False,'RECEIPT_GATE')
    need(item['receipt_content_sha256']==digest(json.dumps(r,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()),'RECEIPT_HASH')
   else:
    item=c['lidar_nonfactor_observation_receipts'][index]
    need(item['source']['serialized_message_sha256']==s['serialized_message_sha256'] and item['point_payload_sha256']==s['point_payload_sha256'],'LIDAR_SHA')
    need(item['frontend_layout_candidate_compatible'] is True and item['registration_executed'] is False and item['relative_pose_computed'] is False and item['factor_execution_authorized'] is False,'LIDAR_NONFACTOR')
   count+=1
 need(count==8 and len(seen)==8,'SOURCE_SAMPLE_COUNT')

m=data('checkpoint_manifest_v1.json')
need(m['schema']=='TRUST_ROBOT_R17_R20_RECORDED_NONFACTOR_CHECKPOINT_V1' and m['parent_commit']==BASE and m['branch']=='kios-isaacsim-v15-integration','MANIFEST_ID')
need(m['authenticated_bag_sha256']==BAG and m['bag_archived'] is False and m['frozen_split']=='train','AUTHENTICATED_SOURCE')
need(set(m['phase_files'])=={'r17','r18','r19','r20'} and set(m['frozen_sha256'])==set().union(*(set(v) for v in m['phase_files'].values())),'PHASE_SET')
need(len(m['frozen_sha256'])==21,'FROZEN_FILE_COUNT')
need(set(PINNED).issubset(m['frozen_sha256']) and all(m['frozen_sha256'][k]==v for k,v in PINNED.items()),'INDEPENDENT_PIN_LIST')
need(set(m['file_sha256'])==set(m['frozen_sha256'])|{'README.md'},'FILE_INVENTORY')
actual={x.relative_to(ROOT).as_posix() for x in ROOT.rglob('*') if x.is_file()}
need(actual==set(m['file_sha256'])|{'checkpoint_manifest_v1.json','verify_checkpoint.py'},'EXACT_ARCHIVE_INVENTORY')
need(not any(x.is_symlink() for x in ROOT.rglob('*')),'SYMLINK')
for rel,wanted in m['file_sha256'].items():
 pure=pathlib.PurePosixPath(rel)
 need(not pure.is_absolute() and '..' not in pure.parts and pure.suffix in ('.py','.json','.xml','.md','.saved'),'FILE_TYPE')
 need(sha(ROOT/rel)==wanted,'SHA:'+rel)
 if rel.endswith('.py') or rel.endswith('.py.saved'):ast.parse((ROOT/rel).read_text())
 if rel.endswith('.json'):data(rel)
 if rel.endswith('.xml'):ET.parse(ROOT/rel)
need(all(m['file_sha256'][p]==h for p,h in m['frozen_sha256'].items()),'MANIFEST_SHA_CROSSCHECK')
expected_docs={'AGENTS.md','docs/TRUST_ROBOT_PROJECT_STATE.md','docs/audits/trust_robot/TRUST_ROBOT_KIOS_R17_R20_RECORDED_INPUT_V1.md'}
need(set(m['documentation_sha256'])==expected_docs,'DOC_SET')
manifest_rel=(ROOT/'checkpoint_manifest_v1.json').relative_to(REPO).as_posix()
commit=subprocess.check_output(['git','-C',str(REPO),'rev-list','-1','HEAD','--',manifest_rel],text=True).strip()
if commit:need(subprocess.check_output(['git','-C',str(REPO),'rev-parse',commit+'^'],text=True).strip()==BASE,'PARENT_COMMIT')
for rel,expected in m['documentation_sha256'].items():
 blob=(subprocess.check_output(['git','-C',str(REPO),'show',commit+':'+rel]) if commit else (REPO/rel).read_bytes())
 need(digest(blob)==expected,'DOC_HASH:'+rel)
a,b,c,d,v=[data(x) for x in (
 'r17/r17_recorded_index.json','r18/r18_bounded_recorded_samples.json',
 'r19/r19_recorded_frontend_contract_v1.json','r20/r20_recorder_readiness_review_v1.json',
 'r20/r20_independent_validation_v1.json')]
need([x['trajectory_id'] for x in (a,b,c,d)]==['room_02']*4 and [x['split'] for x in (a,b,c,d)]==['train']*4,'FROZEN_TRAIN')
need(a['file_sha256']==b['recording_sha256']==c['bag_sha256']==d['authenticated_bag_sha256']==BAG,'BAG_LINEAGE')
need(a['connection_count']==15 and a['chunk_count']==5182 and len(a['topic_inventory'])==15 and a['required_stream_counts']==TOPICS,'ROS1_COUNTS')
need(b['r17_report_sha256']==c['r17_report_sha256']==sha(ROOT/'r17/r17_recorded_index.json'),'R17_REPORT_LINEAGE')
need(c['r18_report_sha256']==sha(ROOT/'r18/r18_bounded_recorded_samples.json'),'R18_REPORT_LINEAGE')
need(b['recorded_streams_decoded']==4 and b['sampled_message_count']==8 and b['sampled_chunks']==4 and set(b['samples'])==set(TOPICS),'BOUND_SAMPLES')
need(c['camera_imu_receipt_count']==6 and c['lidar_observation_count']==2,'CONTRACT_COUNTS')
receipt_links(a,b,c)
need(d['source_report_sha256']=={'r17':sha(ROOT/'r17/r17_recorded_index.json'), 'r18':sha(ROOT/'r18/r18_bounded_recorded_samples.json'), 'r19':sha(ROOT/'r19/r19_recorded_frontend_contract_v1.json')},'R20_LINEAGE')
need(d['source_code_sha256']=={'review_engine':sha(ROOT/'r20/r20_recorder_review.py'),'negative_tests':sha(ROOT/'r20/test_r20_negative.py')},'R20_SOURCE')
need(d['regression_junit_sha256']==sha(ROOT/'r20/r20_frontend_regressions.xml'),'R20_JUNIT_PIN')
cases=list(ET.parse(ROOT/'r20/r20_frontend_regressions.xml').getroot().iter('testcase'))
need(len(cases)==197 and len({(x.get('classname'),x.get('name')) for x in cases})==197 and not any(ch.tag in ('failure','error','skipped') for x in cases for ch in x),'JUNIT_197')
need(d['regression_tests_passed']==197 and d['review_counts']=={'sensor_topics':4,'recorded_messages':26149,'bounded_samples':8,'camera_imu_receipts':6,'lidar_nonfactor_receipts':2,'r17_chunk_count':5182,'recorded_lidar_registrations':0,'real_pose_factors':0,'health_labels':0},'R20_REVIEW')
need(v['review_report_sha256']==sha(ROOT/'r20/r20_recorder_readiness_review_v1.json') and v['review_verifier_sha256']==sha(ROOT/'r20/r20_independent_verify.py') and v['regression_junit_sha256']==sha(ROOT/'r20/r20_frontend_regressions.xml'),'INDEPENDENT_R20_PIN')
need(v['sampled_record_hashes_verified']==8 and v['existing_camera_imu_receipts_verified']==6 and v['lidar_nonfactor_receipts_verified']==2 and v['targeted_regression_tests_verified']==197,'R20_VALIDATION_COUNT')
need(d['readiness_decision']=='RECORDED_OBSERVATION_PROVENANCE_ONLY' and v['archive_readiness']=='OFFLINE_NONFACTOR_EVIDENCE_ONLY','READINESS_SCOPE')
for k in ('real_sensor_factor_execution_authorized','camera_relative_motion_factor_qualified','lidar_relative_motion_factor_qualified','cross_modal_sync_verified','physical_capture_time_verified','full_sensor_extrinsics_verified','independent_reference_association_verified','estimator_scoring_authorized','health_model_training_authorized','live_simulator_launch_authorized','ground_truth_scored','raw_sensor_payloads_embedded_in_report','github_modified'):
 need(d[k] is False,'SCIENTIFIC_GATE:'+k)
for k in ('new_sensor_acquisitions','new_real_pose_factors','health_labels'):
 need(type(d[k]) is int and d[k]==0,'SCIENTIFIC_COUNT:'+k)
for k in ('real_sensor_factor_execution_authorized','m2dgr_scoring_authorized','health_model_training_authorized','live_simulator_launch_authorized'):
 need(m[k] is False,'CHECKPOINT_GATE:'+k)
print('R17_R20_ARCHIVE_STANDALONE_INDEPENDENT_VERIFIER=PASS')
print('R17_R20_FROZEN_SMALL_FILE_HASHES='+str(len(m['frozen_sha256']))+'_VERIFIED')
print('R17_R20_R18_FAILED_AND_REPAIRED_SOURCES=PRESERVED')
print('R17_R20_RECORDING_MESSAGE_RECEIPT_CHAIN=8_VERIFIED')
print('R17_R20_FRONTEND_REGRESSIONS=197_VERIFIED')
print('R17_R20_DOCUMENTATION_COMMIT_SCOPED_SHA=VERIFIED')
print('R17_R20_RAW_BAG_IN_GIT=NO')
print('R17_R20_REAL_SENSOR_FACTOR_ADMISSION=DENIED')
