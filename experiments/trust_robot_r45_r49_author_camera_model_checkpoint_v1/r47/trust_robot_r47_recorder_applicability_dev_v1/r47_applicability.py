"""Recorded room_02 topic, dimensions, frame and application compatibility; no factors."""
import hashlib,json,math,pathlib,re,sys,statistics

BASE='17536d0e9a03eb4f0b4adfb5056dc7ba63df9921'
BAG='ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1'
BLOBS={
 'calibration_results.txt':'f2b1180f9cdef4e665332a09973f9acba9d9d34e',
 'my_params_camera.yaml':'9c429c28dcfc7bea2e59be5529c79ecf46cdf3c6',
 'my_params_lidar.yaml':'a768b1a8f8baa5649009c941817a51ff3f3e00e9'
}
CLOSED=(
 'physical_intrinsics_qualified','sensor_extrinsics_qualified',
 'camera_to_imu_physical_alignment_qualified','mocap_reference_qualified',
 'capture_time_physically_verified','metric_scale_qualified',
 'covariance_model_calibrated','real_pose_factors_authorized',
 'health_training_authorized','ate_rpe_scoring_authorized',
 'confirmation_test_accessed','github_modified','raw_bag_reopened'
)

def need(condition,msg):
 if not condition:raise ValueError('R47_DENIED:'+msg)
def load(p):return json.loads(pathlib.Path(p).read_text())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def normalize(topic):return '/'+topic.lstrip('/')
def scalar(text,key):
 match=re.findall(r'(?m)^\s*'+re.escape(key)+r':\s*([^#\n]+)',text)
 need(len(match)==1,'SETTING:'+key)
 value=match[0].strip().strip('"')
 try:return float(value)
 except ValueError:return value

def policy(r):
 need(r.get('schema')=='TRUST_ROBOT_R47_TRAIN_AUTHOR_RECORDER_APPLICABILITY_V1' and r.get('trajectory_id')=='room_02' and r.get('split')=='train' and r.get('github_baseline')==BASE and r.get('source_bag_sha256')==BAG,'SOURCE_SCOPE')
 need(r.get('source_git_blobs')==BLOBS and set(r.get('source_sha256',{}))==set(BLOBS) and len(r.get('frozen_recorded_sha256',{}))==3,'INPUT_PINS')
 need(all(r.get(key) is False for key in CLOSED),'SCIENCE_ACCESS')
 need(all(type(r.get(key)) is int and r[key]==0 for key in ('qualified_pose_factors','health_labels','ate_rpe_scores','raw_sensor_messages_redecoded')),'ZERO_FACTORS')
 c=r.get('compatibility',{})
 need(c.get('recorded_color_connection_id')==4 and c.get('recorded_color_topic')=='/camera/color/image_raw/compressed' and c.get('recorded_color_message_type')=='sensor_msgs/CompressedImage','COLOR_CONNECTION')
 need(c.get('camera_config_raw_image_topic')=='/camera/color/image_raw' and c.get('direct_subscriber_topic_and_type_match') is False and c.get('image_transport_decompression_adapter_required') is True,'COMPRESSED_ADAPTER')
 need(c.get('authentic_color_frames_checked')==16 and c.get('authentic_color_pair_count')==8 and c.get('authentic_color_dimensions')==[640,480] and c.get('recorded_color_frame_id')=='camera_color_optical_frame','RECORDING_FRAMES')
 need(c.get('camera_intrinsics_image_size_numerically_compatible') is True and c.get('camera_intrinsics_sensor_identity_physically_qualified') is False,'INTRINSICS_NOT_CALIBRATION')
 need(c.get('camera_yaml_selected_imu_topic')=='/handsfree/imu' and c.get('lidar_yaml_selected_imu_topic_normalized')=='/handsfree/imu' and c.get('camera_imu_separate_topic_present') is True,'IMU_TOPIC_SELECTION')
 need(c.get('handsfree_recorded_frame_id')=='base_link' and c.get('camera_imu_recorded_frame_id')=='camera_imu_optical_frame' and c.get('lidar_point_topic_normalized')=='/velodyne_points' and c.get('lidar_connection_id')==9,'NATIVE_FRAMES')
 need(c.get('camera_imu_noise_selection_matches_handsfree_author_noise') is False and c.get('camera_imu_noise_selection_matches_10x_xsens_author_noise') is True,'NOISE_CONFLICT')
 need(c.get('physical_imu_sample_rate_verified') is False and c.get('physical_interstream_clock_offset_verified') is False,'CLOCK_GATES')
 need(r.get('scientific_decision')=='RECORDING_INTERFACE_COMPATIBILITY_ONLY_NO_PHYSICAL_SENSOR_FACTOR_ADMISSION','DECISION')
 need(r.get('next_phase')=='R48_TRAIN_INTRINSIC_MODEL_NUMERIC_PROJECTION_DIAGNOSTICS','NEXT')

def build(camfile,imufile,framesfile,connfile,r46file,v46file,sourcedir,report,plan):
 ca=load(camfile);im=load(imufile);fr=load(framesfile);co=load(connfile);r46=load(r46file);v46=load(v46file)
 need(ca['trajectory_id']==im['trajectory_id']==fr['trajectory_id']==co['trajectory_id']=='room_02' and all(x['split']=='train' for x in (ca,im,fr,co)),'TRAIN')
 need(ca['authenticated_bag_sha256']==im['authenticated_bag_sha256']==fr['authenticated_bag_sha256']==co['source_bag_sha256']==BAG,'SOURCE_BAG')
 need(r46['schema']=='TRUST_ROBOT_R46_GIT_BLOB_AUTHOR_CALIBRATION_CONTENT_AUDIT_V1' and r46['source_git_blobs']==BLOBS and r46['physical_calibration_qualified'] is False,'R46_SCOPE')
 need(v46['source_report_sha256']==sha(r46file) and v46['author_git_blob_files_verified']==3 and v46['physical_calibration_authorized'] is False,'R46_INDEPENDENT')
 source={}
 for name,blob in BLOBS.items():
  p=sourcedir/name
  need(p.is_file() and not p.is_symlink() and p.stat().st_nlink==1 and p.stat().st_size<20000,'SOURCE_FILE:'+name)
  raw=p.read_bytes()
  git=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
  need(git==blob and hashlib.sha256(raw).hexdigest()==r46['source_sha256'][name],'SOURCE_GIT_SHA:'+name)
  source[name]=raw.decode('utf-8')
 camyaml=source['my_params_camera.yaml'];lidyaml=source['my_params_lidar.yaml']
 indexed={x['topic']:x for x in co['connections']}
 need(len(co['connections'])==15 and len(indexed)==15,'CONNECTIONS')
 camera_topic=scalar(camyaml,'image_topic');imu_cam=scalar(camyaml,'imu_topic');imu_lid=normalize(scalar(lidyaml,'imuTopic'));lidar_topic=normalize(scalar(lidyaml,'pointCloudTopic'))
 need(camera_topic=='/camera/color/image_raw' and camera_topic+'/compressed' in indexed,'COMPRESSED_TOPIC_NOT_RAW')
 color=indexed[camera_topic+'/compressed']
 need(color['connection_id']==4 and color['message_type']=='sensor_msgs/CompressedImage','CAMERA_TYPE')
 need(imu_cam==imu_lid=='/handsfree/imu' and '/camera/imu' in indexed,'DUAL_IMU')
 need(indexed['/handsfree/imu']['connection_id']==1 and indexed['/camera/imu']['connection_id']==0 and indexed[lidar_topic]['connection_id']==9 and indexed[lidar_topic]['message_type']=='sensor_msgs/PointCloud2','INDEXED_STREAMS')
 need(ca['pair_count']==len(ca['pairs'])==8 and len(ca['pairs'][0]['frames'])==2,'CAMERA_COUNT')
 all_frames=[f for pair in ca['pairs'] for f in pair['frames']]
 need(len(all_frames)==16 and len({f['serialized_message_sha256'] for f in all_frames})==16,'DISTINCT_JPEG')
 need(all([f['width'],f['height']]==[640,480] and f['connection_id']==4 and f['frame_id']=='camera_color_optical_frame' for f in all_frames),'RECORDED_CAMERA_FRAME')
 need([int(scalar(camyaml,'image_width')),int(scalar(camyaml,'image_height'))]==[640,480],'CONFIG_IMAGE_SIZE')
 need(r46['comparisons']['realsense_resolution']==[640,480] and r46['comparisons']['realsense_intrinsics_numeric_agreement'] is True and r46['comparisons']['camera_noise_matches_xsens_scaled_10x'] is True and r46['comparisons']['handsfree_noise_lidar_config_equal'] is True,'R46_CONSTRAINTS')
 need(set(im['streams'])==set(fr['streams'])=={'/handsfree/imu','/camera/imu'},'IMU_TOPIC_PAIR')
 frame_map={'/handsfree/imu':'base_link','/camera/imu':'camera_imu_optical_frame'}
 for topic in frame_map:
  need(len(im['streams'][topic])==8 and fr['streams'][topic]['recorded_frame_id']==frame_map[topic],'IMU_NATIVE_FRAME')
  need(all(len(p['messages'])==2 and all(m['frame_id']==frame_map[topic] for m in p['messages']) for p in im['streams'][topic]),'IMU_FRAME_CHECK')
  need(all(p['observed_header_gap_ns']>0 for p in im['streams'][topic]),'IMU_DT')
 intervals={k:[p['observed_header_gap_ns']/1e6 for p in im['streams'][k]] for k in frame_map}
 compat={
  'recorded_color_connection_id':color['connection_id'],
  'recorded_color_topic':color['topic'],
  'recorded_color_message_type':color['message_type'],
  'camera_config_raw_image_topic':camera_topic,
  'direct_subscriber_topic_and_type_match':False,
  'image_transport_decompression_adapter_required':True,
  'authentic_color_frames_checked':16,
  'authentic_color_pair_count':8,
  'authentic_color_dimensions':[640,480],
  'recorded_color_frame_id':'camera_color_optical_frame',
  'camera_intrinsics_image_size_numerically_compatible':True,
  'camera_intrinsics_sensor_identity_physically_qualified':False,
  'camera_yaml_selected_imu_topic':imu_cam,
  'lidar_yaml_selected_imu_topic_normalized':imu_lid,
  'camera_imu_separate_topic_present':True,
  'handsfree_recorded_frame_id':'base_link',
  'camera_imu_recorded_frame_id':'camera_imu_optical_frame',
  'lidar_point_topic_normalized':lidar_topic,
  'lidar_connection_id':9,
  'camera_imu_noise_selection_matches_handsfree_author_noise':False,
  'camera_imu_noise_selection_matches_10x_xsens_author_noise':True,
  'handsfree_observed_header_gap_ms':{'min':min(intervals['/handsfree/imu']),'median':statistics.median(intervals['/handsfree/imu']),'max':max(intervals['/handsfree/imu'])},
  'camera_imu_observed_header_gap_ms':{'min':min(intervals['/camera/imu']),'median':statistics.median(intervals['/camera/imu']),'max':max(intervals['/camera/imu'])},
  'physical_imu_sample_rate_verified':False,
  'physical_interstream_clock_offset_verified':False
 }
 result={'schema':'TRUST_ROBOT_R47_TRAIN_AUTHOR_RECORDER_APPLICABILITY_V1','trajectory_id':'room_02','split':'train','github_baseline':BASE,'source_bag_sha256':BAG,'source_git_blobs':BLOBS,'source_sha256':r46['source_sha256'],'frozen_recorded_sha256':{'r33':sha(camfile),'r34':sha(imufile),'r35':sha(framesfile)},'r42_report_sha256':sha(connfile),'r46_report_sha256':sha(r46file),'r46_independent_sha256':sha(v46file),'compatibility':compat,'scientific_decision':'RECORDING_INTERFACE_COMPATIBILITY_ONLY_NO_PHYSICAL_SENSOR_FACTOR_ADMISSION','qualified_pose_factors':0,'health_labels':0,'ate_rpe_scores':0,'raw_sensor_messages_redecoded':0,'next_phase':'R48_TRAIN_INTRINSIC_MODEL_NUMERIC_PROJECTION_DIAGNOSTICS',**{k:False for k in CLOSED}}
 policy(result)
 with report.open('x') as f:json.dump(result,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
 lines=['# R47 — Author parameters vs recorded room_02 interfaces','','Evidence derives only from pinned R33/R34/R35/R42 and exact Git-blob-matched R46 author files. No additional ROS bag messages were decoded.','','## Verified recorded compatibility','', '- Camera: 16 authentic color frames are 640×480, frame `camera_color_optical_frame`, ROS connection #4.', '- Camera YAML selects `/camera/color/image_raw`, but the bag contains only `/camera/color/image_raw/compressed` as `sensor_msgs/CompressedImage`; a transport/decompression adapter is required for a raw-image subscriber.', '- Published camera intrinsics dimensions are numerically compatible, but matching dimensions do not independently prove physical calibration or device serial applicability.', '- Camera and LiDAR application configurations both select HandsFree IMU topic (`/handsfree/imu` after normalizing the LiDAR relative name). Recorded HandsFree frame is `base_link`.', '- A distinct `/camera/imu` also exists with recorded frame `camera_imu_optical_frame`; **do not substitute the streams or frames**.', '- LiDAR YAML `velodyne_points` normalizes to recorded `/velodyne_points`, ROS connection #9.', '- The camera application IMU noise settings match 10× published Xsens values, not the published HandsFree noise values; do not interpret as independently estimated noise.', '- Short header-gap diagnostics: HandsFree median %.6f ms; camera IMU median %.6f ms. They do not establish physical sample rates, clock offset or synchronization.'%(compat['handsfree_observed_header_gap_ms']['median'],compat['camera_imu_observed_header_gap_ms']['median']),'','## Scientific restrictions','','All camera geometry, complete extrinsics, physical timing, noise covariance, mocap reference, metric scale and pose-factor gates remain closed. No independent calibration or ATE/RPE scoring performed.','','## R48','',"Perform bounded numerical projection/undistortion consistency diagnostics using the author's Git-verified camera model and TRAIN-only recorded image dimensions. Maintain explicit no-ground-truth and no-pose-factor gates."]
 with plan.open('x') as f:f.write('\n'.join(lines)+'\n')
 print('R47_RECORDER_COLOR_FRAMES=16_640x480')
 print('R47_COLOR_TOPIC=COMPRESSED_NOT_RAW_ADAPTER_REQUIRED')
 print('R47_CAMERA_AND_LIDAR_APPLICATION_IMU=HANDSFREE')
 print('R47_SECOND_CAMERA_IMU=SEPARATE_NATIVE_FRAME')
 print('R47_LIDAR_TOPIC_NAME=RESOLVES_TO_RECORDED')
 print('R47_PHYSICAL_CALIBRATION_AND_CLOCK=NOT_QUALIFIED')

if __name__=='__main__':build(*(pathlib.Path(x) for x in sys.argv[1:10]))
