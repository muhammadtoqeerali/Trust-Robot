"""Independent SHA-bound R20 checkpoint readiness recomputation."""
import hashlib,json,pathlib,sys,xml.etree.ElementTree as ET
from trust_robot.camera_imu_observation_adapter import validate_receipt_payload

def need(ok,why):
 if not ok:raise ValueError('R20_INDEPENDENT_DENIED:'+why)
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(pathlib.Path(p).read_text())
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def check(manifest,r17,r18,r19,engine,tests,junitfile,report,verifier,out):
 a,b,c,d=(load(x) for x in (r17,r18,r19,report))
 manifest_data=load(manifest)
 chosen=[x for x in manifest_data['records'] if x['trajectory_id']=='room_02']
 need(len(chosen)==1 and chosen[0]['split']=='train','FROZEN_TRAIN')
 expect=[x['sha256'] for x in chosen[0]['calibration_artifacts'] if x.get('source_path')=='raw/rosbags/room_02.bag']
 need(len(expect)==1 and a['file_sha256']==b['recording_sha256']==c['bag_sha256']==d['authenticated_bag_sha256']==expect[0],'SOURCE_DIGEST')
 need(d['schema']=='TRUST_ROBOT_R20_RECORDER_BOUNDARY_REVIEW_V1' and d['trajectory_id']=='room_02' and d['split']=='train','REPORT_IDENTITY')
 need(d['source_manifest_sha256']==sha(manifest) and d['source_report_sha256']=={'r17':sha(r17),'r18':sha(r18),'r19':sha(r19)},'UPSTREAM_PIN')
 need(d['source_code_sha256']=={'review_engine':sha(engine),'negative_tests':sha(tests)} and d['regression_junit_sha256']==sha(junitfile),'REVIEW_SOURCE_PIN')
 need(b['r17_report_sha256']==c['r17_report_sha256']==sha(r17) and c['r18_report_sha256']==sha(r18),'HISTORICAL_LINEAGE')
 keys=('/camera/color/image_raw/compressed','/camera/imu','/handsfree/imu','/velodyne_points')
 need(set(b['samples'])==set(keys) and all(len(b['samples'][x])==2 for x in keys),'SOURCE_SAMPLE_INVENTORY')
 need(d['review_counts']['recorded_messages']==sum(a['required_stream_counts'][t] for t in keys)==26149,'RECORDED_MESSAGE_COUNTS')
 need(d['review_counts']['bounded_samples']==8 and d['review_counts']['camera_imu_receipts']==6 and d['review_counts']['lidar_nonfactor_receipts']==2,'REVIEW_COUNTS')
 i=0;seen=set()
 for topic in keys:
  for n,s in enumerate(b['samples'][topic]):
   ident=(s['chunk_offset'],s['connection_id'],s['bag_record_time_ns'],s['serialized_message_sha256'])
   need(ident not in seen,'UNIQUE_SAMPLED_RECORD')
   seen.add(ident)
   if topic!='/velodyne_points':
    item=c['camera_imu_existing_adapter_receipts'][topic][n];p=item['receipt']
    validate_receipt_payload(p)
    need(p['split_role']=='train' and p['trajectory_or_session_id']=='room_02' and p['source_stream_id']==topic,'ADAPTER_SOURCE')
    need(p['serialized_payload_sha256']==s['serialized_message_sha256'] and p['serialized_payload_size_bytes']==s['serialized_message_bytes'] and p['header_stamp_ns']==s['header_stamp_ns'],'RAW_MESSAGE_BINDING')
    need(item['receipt_content_sha256']==hashlib.sha256(canon(p)).hexdigest(),'RECEIPT_HASH')
    need(p['timing_semantics']['shared_clock_domain_verified'] is False and p['health_boundary']['health_label_assigned'] is False,'RECEIPT_SCIENCE')
   else:
    item=c['lidar_nonfactor_observation_receipts'][n]
    need(item['source']['serialized_message_sha256']==s['serialized_message_sha256'] and item['point_payload_sha256']==s['point_payload_sha256'],'LIDAR_PROVENANCE')
    need(item['frontend_layout_candidate_compatible'] is True and item['registration_executed'] is False and item['relative_pose_computed'] is False,'LIDAR_NONFACTOR')
   i+=1
 need(i==8,'EIGHT_SAMPLES')
 cases=list(ET.parse(junitfile).getroot().iter('testcase'))
 need(len(cases)==d['regression_tests_passed'] and len(cases)>=8 and not any(ch.tag in ('failure','error','skipped') for tc in cases for ch in tc),'REGRESSION_JUNIT')
 need(d['readiness_decision']=='RECORDED_OBSERVATION_PROVENANCE_ONLY' and d['next_action']=='GUARDED_R17_R20_OFFLINE_CHECKPOINT_ARCHIVAL','SCOPE')
 for field in ('real_sensor_factor_execution_authorized','camera_relative_motion_factor_qualified',
              'lidar_relative_motion_factor_qualified','cross_modal_sync_verified','physical_capture_time_verified',
              'full_sensor_extrinsics_verified','independent_reference_association_verified',
              'estimator_scoring_authorized','health_model_training_authorized','live_simulator_launch_authorized',
              'ground_truth_scored','raw_sensor_payloads_embedded_in_report','github_modified'):
  need(d[field] is False,'GATE_'+field)
 for field in ('new_sensor_acquisitions','new_real_pose_factors','health_labels'):
  need(type(d[field]) is int and d[field]==0,'ZERO_'+field)
 result={'schema':'TRUST_ROBOT_R20_INDEPENDENT_VERIFICATION_V1',
         'parent_git_commit':'0dddf4eda57cd629db4c5ee63cdbf645b17fb31d',
         'review_report_sha256':sha(report),'review_verifier_sha256':sha(verifier),
         'regression_junit_sha256':sha(junitfile),
         'sampled_record_hashes_verified':8,'existing_camera_imu_receipts_verified':6,
         'lidar_nonfactor_receipts_verified':2,'targeted_regression_tests_verified':len(cases),
         'scientific_real_factor_admission':False,'m2dgr_scoring_authorized':False,
         'archive_readiness':'OFFLINE_NONFACTOR_EVIDENCE_ONLY'}
 with pathlib.Path(out).open('x') as f:
  json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
 print('R20_INDEPENDENT_SOURCE_LINKS=8_VERIFIED')
 print('R20_INDEPENDENT_RECEIPTS=6_PLUS_2_VERIFIED')
 print('R20_INDEPENDENT_REGRESSION_JUNIT='+str(len(cases))+'_VERIFIED')
 print('R20_INDEPENDENT_VALIDATION=PASS')

if __name__=='__main__':check(*map(pathlib.Path,sys.argv[1:11]))
