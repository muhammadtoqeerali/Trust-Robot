import ast,copy,pathlib,sys
import r52_clock_sensitivity as e
root=pathlib.Path(sys.argv[1]);files=list(root.glob('*.py'))
assert len(files)==3
for file in files:ast.parse(file.read_text(),filename=str(file))
def counts(n):return {'count':n,'min':0,'median':0,'max':0}
report={'schema':e.SCHEMA,'trajectory_id':'room_02','split':'train','github_parent':e.BASE,'bag_sha256':e.BAG,'measurement_class':'COUNTERFACTUAL_HEADER_COORDINATE_SENSITIVITY_NOT_PHYSICAL_CLOCK_FIT','samples_per_stream':16,'authentic_frozen_messages':48,'hypothetical_camera_header_shifts_ms':list(e.SHIFTS),'hypothetical_single_stream_header_shifts_ms':list(e.LOCAL),'sparse_cross_stream_scenarios':{},'record_header_sign_scenarios':{},'four_streams_fixed_physical_offset_unverified':True,'physical_offset_selected':None,'association_tolerance_selected':None,'clock_drift_model_selected':None,'reference_mocap_invalid_rotation_records':90,'reference_temporal_association_authorized':False,'author_td_zero_is_physical_time_sync':False,'scientific_gates':{k:False for k in e.GATES},**{k:0 for k in e.ZERO},'next_phase':'R53_TRAIN_SENSOR_TIMING_RECEIPT_ADMISSION_BOUNDARY'}
for topic in e.TOPICS[1:]:
 report['sparse_cross_stream_scenarios'][topic]=[{'hypothetical_camera_header_shift_ms':shift,'sparse_nearest_header_distance_ms':counts(16),'physical_clock_offset_estimate':None,'association_tolerance':None,'scenario_only_not_clock_fit':True} for shift in e.SHIFTS]
for topic in e.TOPICS:
 report['record_header_sign_scenarios'][topic]=[{'hypothetical_header_shift_ms':shift,'negative_residual_count':9 if topic=='/camera/imu' else 0,'zero_residual_count':0,'positive_residual_count':7 if topic=='/camera/imu' else 16,'record_minus_header_ms':counts(16),'transport_latency_measurement':False} for shift in e.LOCAL]
e.policy(report)
rejected=0

def check(bad,label):
 global rejected
 try:e.policy(bad)
 except ValueError:rejected+=1
 else:raise AssertionError('PROMOTION_ACCEPTED:'+label)
for gate in e.GATES:
 bad=copy.deepcopy(report);bad['scientific_gates'][gate]=True;check(bad,gate)
for key in e.ZERO:
 bad=copy.deepcopy(report);bad[key]=1;check(bad,key)
for key,val in (('trajectory_id','room_03'),('split','confirmation_test'),('github_parent','0'*40),('measurement_class','CALIBRATED_CLOCK'),('authentic_frozen_messages',47),('reference_temporal_association_authorized',True),('physical_offset_selected',0),('association_tolerance_selected',0.01)):
 bad=copy.deepcopy(report);bad[key]=val;check(bad,key)
for kind in ('wrong_shift','selected_offset','selected_tolerance','transport_delay','no_negatives'):
 bad=copy.deepcopy(report)
 if kind=='wrong_shift':bad['hypothetical_camera_header_shifts_ms']=[0]
 elif kind=='selected_offset':bad['sparse_cross_stream_scenarios']['/camera/imu'][0]['physical_clock_offset_estimate']=0
 elif kind=='selected_tolerance':bad['sparse_cross_stream_scenarios']['/camera/imu'][0]['association_tolerance']=5
 elif kind=='transport_delay':bad['record_header_sign_scenarios']['/camera/imu'][1]['transport_latency_measurement']=True
 else:bad['record_header_sign_scenarios']['/camera/imu'][1]['negative_residual_count']=0;bad['record_header_sign_scenarios']['/camera/imu'][1]['positive_residual_count']=16
 check(bad,kind)
assert rejected==30
print('R52_PYTHON_AST=3_PASS')
print('R52_NEGATIVE_SCIENCE_CLOCK_SCENARIO_CONTROLS=30_REJECTED')
