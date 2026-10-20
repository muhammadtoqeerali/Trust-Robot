"""Re-evaluate recorded topics and frame dimensions independently of primary engine."""
import hashlib,json,pathlib,re,statistics,sys

def fail(condition,reason):
 if not condition:raise ValueError('R47_INDEPENDENT_DENIED:'+reason)
def get(p):return json.loads(pathlib.Path(p).read_bytes())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def setting(text,key):
 r=re.findall(r'(?m)^\s*'+re.escape(key)+r':\s*([^#\n]+)',text)
 fail(len(r)==1,'KEY:'+key)
 return r[0].strip().strip('"')
def run(cam,imu,frames,connections,r46,v46,src,report,plan,result):
 x=get(report);c=get(cam);i=get(imu);f=get(frames);k=get(connections);q=get(r46);v=get(v46)
 fail(x['schema']=='TRUST_ROBOT_R47_TRAIN_AUTHOR_RECORDER_APPLICABILITY_V1' and x['split']=='train' and x['trajectory_id']=='room_02','SCOPE')
 fail(v['source_report_sha256']==sha(r46) and q['source_git_blobs']==x['source_git_blobs'],'R46_BIND')
 for n,blob in q['source_git_blobs'].items():
  p=src/n; raw=p.read_bytes()
  sha1=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
  fail(sha1==blob and hashlib.sha256(raw).hexdigest()==q['source_sha256'][n],'SOURCE:'+n)
 config=(src/'my_params_camera.yaml').read_text();lid=(src/'my_params_lidar.yaml').read_text()
 indexed={x['topic']:x for x in k['connections']}
 fail(len(indexed)==15,'CONNECTIONS')
 rawtopic=setting(config,'image_topic')
 fail(rawtopic not in indexed and rawtopic+'/compressed' in indexed and indexed[rawtopic+'/compressed']['message_type']=='sensor_msgs/CompressedImage','TRANSPORT')
 color=[im for p in c['pairs'] for im in p['frames']]
 fail(len(color)==16 and all(im['connection_id']==indexed[rawtopic+'/compressed']['connection_id'] and (im['width'],im['height'])==(640,480) and im['frame_id']=='camera_color_optical_frame' for im in color),'FRAMES')
 fail((int(setting(config,'image_width')),int(setting(config,'image_height')))==(640,480),'CAMERA_DIMS')
 hf='/'+setting(lid,'imuTopic').lstrip('/')
 cameraimu=setting(config,'imu_topic')
 fail(hf==cameraimu=='/handsfree/imu' and '/camera/imu' in indexed and indexed[hf]['message_type']=='sensor_msgs/Imu','IMU')
 fail('/'+setting(lid,'pointCloudTopic').lstrip('/')=='/velodyne_points' and indexed['/velodyne_points']['connection_id']==9,'LIDAR')
 for topic,native in (('/camera/imu','camera_imu_optical_frame'),('/handsfree/imu','base_link')):
  fail(f['streams'][topic]['recorded_frame_id']==native and len(i['streams'][topic])==8,'IMU_FRAME')
  dt=[p['observed_header_gap_ns']/1e6 for p in i['streams'][topic]]
  key='camera_imu_observed_header_gap_ms' if topic=='/camera/imu' else 'handsfree_observed_header_gap_ms'
  fail(abs(statistics.median(dt)-x['compatibility'][key]['median'])<1e-10,'IMU_DT')
 fail(all(x['frozen_recorded_sha256'][n]==sha(p) for n,p in (('r33',cam),('r34',imu),('r35',frames))),'PINS')
 fail(x['r42_report_sha256']==sha(connections) and x['r46_report_sha256']==sha(r46) and x['r46_independent_sha256']==sha(v46),'PINS_2')
 fail(x['compatibility']['image_transport_decompression_adapter_required'] is True and x['compatibility']['physical_interstream_clock_offset_verified'] is False and x['compatibility']['camera_intrinsics_sensor_identity_physically_qualified'] is False,'SCIENCE')
 fail(all(x[key] is False for key in ('raw_bag_reopened','github_modified','confirmation_test_accessed','real_pose_factors_authorized','health_training_authorized','ate_rpe_scoring_authorized')),'HOLDOUT')
 fail('R48' in plan.read_text() and 'adapter' in plan.read_text().lower() and 'remain closed' in plan.read_text(),'PLAN')
 result_data={'schema':'TRUST_ROBOT_R47_INDEPENDENT_RECORDER_APPLICABILITY_V1','source_report_sha256':sha(report),'plan_sha256':sha(plan),'verified_color_frames':16,'verified_connection_topics':15,'verified_imu_native_frame_streams':2,'author_git_blob_sources_revalidated':3,'compressed_image_adapter_required':True,'physical_calibration_qualified':False,'real_pose_factors_authorized':False,'confirmation_test_used':False,'github_modified':False}
 with result.open('x') as h:json.dump(result_data,h,indent=2,sort_keys=True,allow_nan=False);h.write('\n')
 print('R47_INDEPENDENT_COLOR_TOPIC_AND_16_FRAME_DIMENSIONS=MATCH')
 print('R47_INDEPENDENT_CAMERA_HANDSFREE_IMU_AND_LIDAR_TOPICS=MATCH')
 print('R47_INDEPENDENT_GIT_BLOB_SOURCE_AND_SCIENCE_GATES=PASS')
 print('R47_INDEPENDENT_VALIDATION=PASS')
if __name__=='__main__':run(*(pathlib.Path(p) for p in sys.argv[1:11]))
