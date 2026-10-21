"""Independent nearest-neighbor replay with sorted bisect (not primary's loops)."""
import bisect,hashlib,json,pathlib,statistics,sys

def need(ok,msg):
 if not ok:raise ValueError('R52_INDEPENDENT_DENIED:'+msg)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_bytes())
def close(a,b):return abs(a-b)<1e-9

def run(cam_p,imu_p,r51_p,v51_p,report_p,plan_p,out_p):
 cam,imu,r51,v51,report=map(load,(cam_p,imu_p,r51_p,v51_p,report_p))
 need(report['source_sha256']['r33_camera']==digest(cam_p) and report['source_sha256']['r34_imu']==digest(imu_p) and report['source_sha256']['r51_report']==digest(r51_p) and report['source_sha256']['r51_independent']==digest(v51_p),'SOURCE_CHAIN')
 need(v51['source_report_sha256']==digest(r51_p) and v51['authentic_frozen_sample_timestamps_recomputed']==48,'PRIOR_INDEPENDENT')
 camera=[m for pair in cam['pairs'] for m in pair['frames']]
 imu_data={k:[m for pair in imu['streams'][k] for m in pair['messages']] for k in ('/camera/imu','/handsfree/imu')}
 observed={'/camera/color/image_raw/compressed':camera,**imu_data}
 need(all(len(x)==16 for x in observed.values()),'MESSAGE_COUNTS')
 # The independent implementation sorts timestamps, bisects, and checks two neighbors.
 for topic,records in imu_data.items():
  ordered=sorted(m['header_stamp_ns'] for m in records)
  rows=report['sparse_cross_stream_scenarios'][topic]
  need(len(rows)==7,'SCENARIO_COUNT')
  for row in rows:
   shift=row['hypothetical_camera_header_shift_ms']*1000000
   distances=[]
   for msg in camera:
    t=msg['header_stamp_ns']+shift
    index=bisect.bisect_left(ordered,t)
    candidates=[]
    if index<len(ordered):candidates.append(abs(ordered[index]-t))
    if index:candidates.append(abs(ordered[index-1]-t))
    need(candidates,'EMPTY_IMU')
    distances.append(min(candidates)/1000000)
   data=row['sparse_nearest_header_distance_ms']
   need(data['count']==16 and close(data['min'],min(distances)) and close(data['median'],statistics.median(distances)) and close(data['max'],max(distances)),'NEAREST_REPLAY:'+topic)
   need(row['physical_clock_offset_estimate'] is None and row['association_tolerance'] is None,'NO_OFFSET_SELECTION')
 for topic,records in observed.items():
  rows=report['record_header_sign_scenarios'][topic]
  need(len(rows)==3,'HEADER_SHIFT_COUNT')
  for row in rows:
   shift_ns=row['hypothetical_header_shift_ms']*1000000
   residual=[m['bag_record_time_ns']-m['header_stamp_ns']-shift_ns for m in records]
   need((row['negative_residual_count'],row['zero_residual_count'],row['positive_residual_count'])==(sum(v<0 for v in residual),sum(v==0 for v in residual),sum(v>0 for v in residual)),'RESIDUAL_SIGN:'+topic)
   data=row['record_minus_header_ms'];res_ms=[x/1000000 for x in residual]
   need(data['count']==16 and close(data['min'],min(res_ms)) and close(data['median'],statistics.median(res_ms)) and close(data['max'],max(res_ms)),'RESIDUAL_STATS:'+topic)
  need(rows[1]['negative_residual_count']==r51['streams'][topic]['negative_residual_count'],'R51_BASELINE_SIGN')
 need(report['record_header_sign_scenarios']['/camera/imu'][1]['negative_residual_count']==9,'CAMERA_IMU_NEGATIVE')
 need(report['physical_offset_selected'] is None and report['clock_drift_model_selected'] is None and report['association_tolerance_selected'] is None,'NO_CLOCK_FIT')
 need(len(report['scientific_gates'])==14 and all(value is False for value in report['scientific_gates'].values()),'CLOSED_GATES')
 need(all(report[k]==0 for k in ('real_pose_factors','health_labels','ate_rpe_scores')),'NO_SCIENTIFIC_OUTPUTS')
 need(report['split']=='train' and report['trajectory_id']=='room_02' and report['reference_temporal_association_authorized'] is False,'SPLIT_AND_REFERENCE')
 plan=plan_p.read_text();need('counterfactual' in plan.lower() and 'R53' in plan and 'not a physical' in plan,'PLAN_GATES')
 proof={'schema':'TRUST_ROBOT_R52_INDEPENDENT_CLOCK_PROVENANCE_SENSITIVITY_V1','source_report_sha256':digest(report_p),'plan_sha256':digest(plan_p),'original_timestamp_receipts_verified':48,'independent_sparse_shift_distances_recomputed':224,'independent_record_header_residuals_recomputed':144,'clock_offset_selected':False,'physical_clock_calibration_authorized':False,'mocap_reference_scoring_authorized':False,'pose_factors_authorized':False,'raw_bag_opened':False,'confirmation_test_accessed':False,'github_modified':False}
 with out_p.open('x') as f:json.dump(proof,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
 print('R52_INDEPENDENT_SPARSE_NEAREST_HEADER_DISTANCES=224_MATCH')
 print('R52_INDEPENDENT_HEADER_RECORD_RESIDUALS=144_MATCH')
 print('R52_INDEPENDENT_NO_CLOCK_OFFSET_SELECTED=VERIFIED')
 print('R52_INDEPENDENT_VALIDATION=PASS')
if __name__=='__main__':run(*(pathlib.Path(x) for x in sys.argv[1:8]))
