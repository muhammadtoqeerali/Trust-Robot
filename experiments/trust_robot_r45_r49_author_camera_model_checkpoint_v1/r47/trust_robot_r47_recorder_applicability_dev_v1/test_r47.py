import ast,copy,pathlib,sys
import r47_applicability as m
root=pathlib.Path(sys.argv[1]);scripts=list(root.glob('*.py'))
assert len(scripts)==3
for path in scripts:ast.parse(path.read_text(),filename=str(path))
compat={'recorded_color_connection_id':4,'recorded_color_topic':'/camera/color/image_raw/compressed','recorded_color_message_type':'sensor_msgs/CompressedImage','camera_config_raw_image_topic':'/camera/color/image_raw','direct_subscriber_topic_and_type_match':False,'image_transport_decompression_adapter_required':True,'authentic_color_frames_checked':16,'authentic_color_pair_count':8,'authentic_color_dimensions':[640,480],'recorded_color_frame_id':'camera_color_optical_frame','camera_intrinsics_image_size_numerically_compatible':True,'camera_intrinsics_sensor_identity_physically_qualified':False,'camera_yaml_selected_imu_topic':'/handsfree/imu','lidar_yaml_selected_imu_topic_normalized':'/handsfree/imu','camera_imu_separate_topic_present':True,'handsfree_recorded_frame_id':'base_link','camera_imu_recorded_frame_id':'camera_imu_optical_frame','lidar_point_topic_normalized':'/velodyne_points','lidar_connection_id':9,'camera_imu_noise_selection_matches_handsfree_author_noise':False,'camera_imu_noise_selection_matches_10x_xsens_author_noise':True,'physical_imu_sample_rate_verified':False,'physical_interstream_clock_offset_verified':False}
r={'schema':'TRUST_ROBOT_R47_TRAIN_AUTHOR_RECORDER_APPLICABILITY_V1','trajectory_id':'room_02','split':'train','github_baseline':m.BASE,'source_bag_sha256':m.BAG,'source_git_blobs':m.BLOBS,'source_sha256':{k:'a'*64 for k in m.BLOBS},'frozen_recorded_sha256':{'r33':'a'*64,'r34':'b'*64,'r35':'c'*64},'compatibility':compat,'scientific_decision':'RECORDING_INTERFACE_COMPATIBILITY_ONLY_NO_PHYSICAL_SENSOR_FACTOR_ADMISSION','next_phase':'R48_TRAIN_INTRINSIC_MODEL_NUMERIC_PROJECTION_DIAGNOSTICS','qualified_pose_factors':0,'health_labels':0,'ate_rpe_scores':0,'raw_sensor_messages_redecoded':0,**{k:False for k in m.CLOSED}}
m.policy(r)
rejected=0
for key in m.CLOSED:
 x=copy.deepcopy(r);x[key]=True
 try:m.policy(x)
 except ValueError:rejected+=1
 else:raise AssertionError('GATE:'+key)
for key in ('qualified_pose_factors','health_labels','ate_rpe_scores','raw_sensor_messages_redecoded'):
 x=copy.deepcopy(r);x[key]=1
 try:m.policy(x)
 except ValueError:rejected+=1
 else:raise AssertionError('COUNT:'+key)
for key,val in (('split','confirmation_test'),('github_baseline','0'*40),('source_git_blobs',{}),('scientific_decision','SCORING'),('next_phase','SKIP')):
 x=copy.deepcopy(r);x[key]=val
 try:m.policy(x)
 except ValueError:rejected+=1
 else:raise AssertionError('SOURCE:'+key)
for key,value in (('recorded_color_topic','/camera/color/image_raw'),('image_transport_decompression_adapter_required',False),('camera_yaml_selected_imu_topic','/camera/imu'),('handsfree_recorded_frame_id','camera_imu_optical_frame'),('camera_intrinsics_sensor_identity_physically_qualified',True),('camera_imu_noise_selection_matches_handsfree_author_noise',True)):
 x=copy.deepcopy(r);x['compatibility'][key]=value
 try:m.policy(x)
 except ValueError:rejected+=1
 else:raise AssertionError('COMPAT:'+key)
assert rejected==28
print('R47_PYTHON_AST=3_PASS')
print('R47_NEGATIVE_SCIENCE_AND_INTERFACE_CONTROLS=28_REJECTED')
