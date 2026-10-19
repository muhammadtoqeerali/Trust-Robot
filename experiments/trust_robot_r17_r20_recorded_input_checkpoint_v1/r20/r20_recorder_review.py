"""R20: review previously recorded, independently checked sample receipts.

No data admission, no timestamp alignment, no pose estimation or feature training.
"""
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

TOPICS={
 '/camera/color/image_raw/compressed':'sensor_msgs/CompressedImage',
 '/camera/imu':'sensor_msgs/Imu',
 '/handsfree/imu':'sensor_msgs/Imu',
 '/velodyne_points':'sensor_msgs/PointCloud2',
}
FRAMES={
 '/camera/color/image_raw/compressed':'camera_color_optical_frame',
 '/camera/imu':'camera_imu_optical_frame',
 '/handsfree/imu':'base_link',
 '/velodyne_points':'velodyne',
}
EXPECTED_COUNTS={
 '/camera/color/image_raw/compressed':1113,
 '/camera/imu':13858,
 '/handsfree/imu':10426,
 '/velodyne_points':752,
}

def need(ok,why):
 if not ok: raise ValueError('R20_RECORDER_BOUNDARY:'+why)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

def review(a,b,c):
 need(a.get('schema')=='TRUST_ROBOT_R17_ROS1_INDEX_READONLY_V1' and
      b.get('schema')=='TRUST_ROBOT_R18_BOUNDED_ROS1_RECORDED_MESSAGES_V1' and
      c.get('schema')=='TRUST_ROBOT_R19_RECORDED_FRONTEND_PROVENANCE_V1','SCHEMAS')
 need(all(x.get('trajectory_id')=='room_02' and x.get('split')=='train' for x in (a,b,c)),'SPLIT')
 need(a.get('file_sha256')==b.get('recording_sha256')==c.get('bag_sha256') and
      len(a['file_sha256'])==64,'BAG_LINEAGE')
 need(a.get('connection_count')==15 and a.get('chunk_count')==5182 and
      len(a.get('connections',[]))==15 and len(a.get('topic_inventory',{}))==15,'R17_INDEX')
 need(a.get('required_stream_counts')==EXPECTED_COUNTS and
      b.get('sampled_message_count')==8 and b.get('recorded_streams_decoded')==4 and
      type(b.get('sampled_chunks')) is int and 1<=b['sampled_chunks']<=8,'SOURCE_COUNTS')
 need(set(b.get('samples',{}))==set(TOPICS) and
      c.get('camera_imu_receipt_count')==6 and c.get('lidar_observation_count')==2,'RECEIPT_COUNTS')
 need(c.get('message_index_role')=='two_sample_subset_not_full_recording_ordinal','INDEX_SCOPE')
 need(a.get('bag_record_time_is_capture_time_proof') is False,'BAG_RECORD_TIME_SEMANTICS')
 for field in ('bag_record_time_is_capture_time_proof','header_stamp_is_capture_time_proof',
               'cross_stream_alignment_performed','physical_sync_verified','extrinsics_verified',
               'raw_recording_modified','github_modified'):
  need(b.get(field) is False,'R18_GATE_'+field)
 for field in ('encoded_image_pixels_decoded','lidar_xyz_points_materialized',
               'image_odometry_performed','scan_registration_performed','imu_preintegration_performed',
               'bag_record_time_used_as_measurement_time','header_stamp_physical_capture_semantics_verified',
               'cross_modal_temporal_association_performed','physical_sync_verified','full_extrinsics_verified',
               'real_sensor_factor_execution_authorized','health_model_training_authorized',
               'ground_truth_scored','raw_recording_modified','github_modified'):
  need(c.get(field) is False,'R19_GATE_'+field)
 need(all(x.get('real_pose_factors_generated')==0 and x.get('health_labels')==0 for x in (b,c)),'NO_FACTORS_LABELS')
 indexed={x['id']:x for x in a['connections']}
 need(len(indexed)==15,'CONNECTION_DUPLICATE')
 receipts=c.get('camera_imu_existing_adapter_receipts')
 need(isinstance(receipts,dict) and set(receipts)==set(TOPICS)-{'/velodyne_points'},'CAMERA_IMU_TOPICS')
 observed=set();links=0
 for topic,items in b['samples'].items():
  need(len(items)==2 and items[0]['chunk_offset']!=items[1]['chunk_offset'],'SAMPLE_CHUNKS')
  for i,s in enumerate(items):
   need(s.get('frame_id')==FRAMES[topic] and s.get('connection_id') in indexed and
        indexed[s['connection_id']]['topic']==topic and
        indexed[s['connection_id']]['message_type']==TOPICS[topic],'RECORDED_SOURCE')
   need(type(s.get('serialized_message_bytes')) is int and s['serialized_message_bytes']>16 and
        type(s.get('serialized_message_sha256')) is str and
        len(s['serialized_message_sha256'])==64,'RECORDED_MESSAGE_HASH')
   ident=(s['chunk_offset'],s['connection_id'],s['bag_record_time_ns'],s['serialized_message_sha256'])
   need(ident not in observed,'DUPLICATE_RECORDED_MESSAGE')
   observed.add(ident)
   if topic!='/velodyne_points':
    row=receipts[topic][i]; r=row['receipt']; source=row['source']
    need(r['schema']=='TRUST_ROBOT_PHASE5_CAMERA_IMU_RAW_OBSERVATION_RECEIPT_V1' and
         r['trajectory_or_session_id']=='room_02' and r['split_role']=='train' and
         r['source_stream_id']==topic and r['message_type']==TOPICS[topic] and
         r['message_index']==i and row['message_index_scope']=='two_sample_subset_not_full_recording_ordinal','ADAPTER_IDENTITY')
    need(r['serialized_payload_sha256']==s['serialized_message_sha256'] and
         r['serialized_payload_size_bytes']==s['serialized_message_bytes'] and
         r['header_stamp_ns']==s['header_stamp_ns'] and
         r['bag_record_time_ns']==s['bag_record_time_ns'],'ADAPTER_MESSAGE_BINDING')
    need(source['frame_id']==s['frame_id'] and source['sample_subset_index']==i and
         (source['chunk_offset'],source['connection_id'],source['bag_record_time_ns'],source['serialized_message_sha256'])==ident,'ADAPTER_LOCATION')
    need(row['receipt_content_sha256']==hashlib.sha256(canon(r)).hexdigest(),'RECEIPT_CANONICAL_SHA')
    need(r['timing_semantics']['bag_record_time_role']=='transport_or_container_time_only' and
         r['timing_semantics']['shared_clock_domain_verified'] is False and
         r['health_boundary']['health_label_assigned'] is False,'ADAPTER_SCIENCE')
   else:
    row=c['lidar_nonfactor_observation_receipts'][i];source=row['source']
    need((source['chunk_offset'],source['connection_id'],source['bag_record_time_ns'],source['serialized_message_sha256'])==ident and
         source['sample_subset_index']==i,'LIDAR_PROVENANCE')
    need(row['point_count']==s['point_count'] and row['point_step']==s['point_step'] and
         row['point_payload_sha256']==s['point_payload_sha256'] and
         row['point_payload_bytes']==s['point_payload_bytes'] and
         row['point_fields']==s['point_fields'],'LIDAR_LAYOUT')
    need(row['frontend_layout_candidate_compatible'] is True and
         all(row[k] is False for k in ('registration_executed','relative_pose_computed','factor_execution_authorized')),'LIDAR_NONFACTOR')
   links+=1
 need(links==8 and len(observed)==8,'EIGHT_SOURCE_LINKS')
 need(c['selected_chunk_offsets']==sorted({s['chunk_offset'] for group in b['samples'].values() for s in group}),'CHUNK_LIST')
 return {'sensor_topics':4,'recorded_messages':sum(EXPECTED_COUNTS.values()),
         'bounded_samples':8,'camera_imu_receipts':6,'lidar_nonfactor_receipts':2,
         'r17_chunk_count':5182,'recorded_lidar_registrations':0,'real_pose_factors':0,'health_labels':0}

def junit(path):
 cases=list(ET.parse(path).getroot().iter('testcase'))
 need(len(cases)>=8,'REGRESSION_TEST_MINIMUM')
 need(len({(x.get('classname'),x.get('name')) for x in cases})==len(cases),'REGRESSION_DUPLICATES')
 need(not any(y.tag in ('failure','error','skipped') for x in cases for y in x),'REGRESSION_FAILURE')
 return len(cases)

def main(repo,manifest,r17,r18,r19,junitfile,engine,tests,out):
 a,b,c=load(r17),load(r18),load(r19)
 m=load(manifest)
 frozen=[r for r in m['records'] if r['trajectory_id']=='room_02']
 need(len(frozen)==1 and frozen[0]['split']=='train','FROZEN_TRAIN')
 bags=[x for x in frozen[0]['calibration_artifacts'] if x.get('source_path')=='raw/rosbags/room_02.bag']
 need(len(bags)==1 and bags[0]['sha256']==a['file_sha256'],'FROZEN_SOURCE_SHA')
 need(b.get('r17_report_sha256')==sha(r17) and c.get('r17_report_sha256')==sha(r17) and
      c.get('r18_report_sha256')==sha(r18),'REPORT_CHAIN')
 
 result=review(a,b,c)
 count=junit(junitfile)
 report={
 'schema':'TRUST_ROBOT_R20_RECORDER_BOUNDARY_REVIEW_V1',
 'parent_git_commit':'0dddf4eda57cd629db4c5ee63cdbf645b17fb31d',
 'trajectory_id':'room_02','split':'train','authenticated_bag_sha256':a['file_sha256'],
 'source_manifest_sha256':sha(manifest),
 'source_report_sha256':{'r17':sha(r17),'r18':sha(r18),'r19':sha(r19)},
 'source_code_sha256':{'review_engine':sha(engine),'negative_tests':sha(tests)},
 'regression_junit_sha256':sha(junitfile),'regression_tests_passed':count,
 'review_counts':result,
 'readiness_decision':'RECORDED_OBSERVATION_PROVENANCE_ONLY',
 'next_action':'GUARDED_R17_R20_OFFLINE_CHECKPOINT_ARCHIVAL',
 'real_sensor_factor_execution_authorized':False,
 'camera_relative_motion_factor_qualified':False,
 'lidar_relative_motion_factor_qualified':False,
 'cross_modal_sync_verified':False,'physical_capture_time_verified':False,
 'full_sensor_extrinsics_verified':False,'independent_reference_association_verified':False,
 'estimator_scoring_authorized':False,'health_model_training_authorized':False,
 'live_simulator_launch_authorized':False,'ground_truth_scored':False,
 'raw_sensor_payloads_embedded_in_report':False,'github_modified':False,
 'new_sensor_acquisitions':0,'new_real_pose_factors':0,'health_labels':0,
 }
 with Path(out).open('x',encoding='utf-8') as file:
  json.dump(report,file,sort_keys=True,indent=2,allow_nan=False);file.write('\n')
 print('R20_AUTHENTIC_RECORDED_MESSAGES='+str(result['recorded_messages']))
 print('R20_BOUNDED_PROVENANCE_SAMPLES=8')
 print('R20_CAMERA_IMU_CONTRACT_RECEIPTS=6')
 print('R20_LIDAR_LAYOUT_NONFACTOR_RECEIPTS=2')
 print('R20_TARGETED_FRONTEND_REGRESSIONS='+str(count)+'_PASSED')
 print('R20_READINESS=RECORDED_OBSERVATION_PROVENANCE_ONLY')

if __name__=='__main__':main(*map(Path,sys.argv[1:10]))
