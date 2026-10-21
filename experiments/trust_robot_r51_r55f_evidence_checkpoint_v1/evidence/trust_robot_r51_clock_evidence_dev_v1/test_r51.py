import ast,copy,pathlib,sys
import r51_clock_evidence as e
root=pathlib.Path(sys.argv[1]);sources=list(root.glob('*.py'))
assert len(sources)==3
for p in sources:ast.parse(p.read_text(),filename=str(p))
mock={'schema':e.SCHEMA,'trajectory_id':'room_02','split':'train','github_parent':e.BASE,'bag_sha256':e.BAG,'measurement_class':'DESCRIPTIVE_RECORD_AND_HEADER_COORDINATES_NOT_CLOCK_CALIBRATION','streams':{},'sparse_cross_stream_header_distances':{},'camera_application_td_default_zero':True,'camera_application_estimate_td_default_zero':True,'author_defaults_not_capture_clock_proof':True,'reference_timing_policy':'UNVERIFIED_NO_ASSOCIATION_TOLERANCE','mocap_invalid_rotation_records':90,'frozen_four_stream_clock_domains_unverified':True,'no_fixed_offset_selected_on_train':True,'scientific_gates':{k:False for k in e.BLOCKED},**{k:0 for k in e.ZERO},'next_phase':'R52_TRAIN_CLOCK_PROVENANCE_SENSITIVITY_AND_SOURCE_APPLICATION'}
for topic,frame in zip(e.TOPICS,e.FRAMES):
 mock['streams'][topic]={'native_frame':frame,'sample_count':16,'sampled_pair_count':8,'negative_residual_count':1 if topic=='/camera/imu' else 0,'zero_residual_count':0,'positive_residual_count':15 if topic=='/camera/imu' else 16,'header_timestamp_is_physical_capture_verified':False,'record_minus_header_is_transport_latency_verified':False}
for topic in e.TOPICS[1:]:mock['sparse_cross_stream_header_distances'][topic]={'physical_clock_offset_candidate':None,'not_a_synchronization_measurement':True}
e.policy(mock)
count=0
for key in e.BLOCKED:
 bad=copy.deepcopy(mock);bad['scientific_gates'][key]=True
 try:e.policy(bad)
 except ValueError:count+=1
 else:raise AssertionError('GATE_PROMOTION:'+key)
for key in e.ZERO:
 bad=copy.deepcopy(mock);bad[key]=1
 try:e.policy(bad)
 except ValueError:count+=1
 else:raise AssertionError('OUTPUT_PROMOTION:'+key)
for key,val in [('split','confirmation_test'),('trajectory_id','room_03'),('github_parent','0'*40),('measurement_class','PHYSICAL_CLOCK_CALIBRATED'),('no_fixed_offset_selected_on_train',False),('reference_timing_policy','ALLOW_ATE_RPE'),('camera_application_td_default_zero',False),('mocap_invalid_rotation_records',0)]:
 bad=copy.deepcopy(mock);bad[key]=val
 try:e.policy(bad)
 except ValueError:count+=1
 else:raise AssertionError('SOURCE_PROMOTION:'+key)
for change in ('physical_capture','transport_delay','no_negatives','clock_fit','invalid_frame'):
 bad=copy.deepcopy(mock)
 if change=='physical_capture':bad['streams'][e.TOPICS[0]]['header_timestamp_is_physical_capture_verified']=True
 elif change=='transport_delay':bad['streams'][e.TOPICS[1]]['record_minus_header_is_transport_latency_verified']=True
 elif change=='no_negatives':bad['streams'][e.TOPICS[1]]['negative_residual_count']=0;bad['streams'][e.TOPICS[1]]['positive_residual_count']=16
 elif change=='clock_fit':bad['sparse_cross_stream_header_distances'][e.TOPICS[1]]['physical_clock_offset_candidate']=0
 else:bad['streams'][e.TOPICS[1]]['native_frame']='base_link'
 try:e.policy(bad)
 except ValueError:count+=1
 else:raise AssertionError('TIME_PROMOTION:'+change)
assert count==30
print('R51_PYTHON_AST=3_PASS')
print('R51_NEGATIVE_SCIENCE_CLOCK_REFERENCE_CONTROLS=30_REJECTED')
