"""Independent replay of timestamp arithmetic using R33/R34 frozen source reports."""
import hashlib,json,pathlib,statistics,sys

def need(ok,k):
 if not ok:raise ValueError('R51_INDEPENDENT_DENIED:'+k)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def eq(a,b):return abs(a-b)<1e-9

def run(cam_p,imu_p,report_p,plan_p,out_p):
 report=read(report_p);camera=read(cam_p);imu=read(imu_p)
 need(report['source_sha256']['r33_camera']==sha(cam_p) and report['source_sha256']['r34_imu']==sha(imu_p),'SOURCE_HASH')
 topics=(('/camera/color/image_raw/compressed',[m for p in camera['pairs'] for m in p['frames']]),('/camera/imu',[m for p in imu['streams']['/camera/imu'] for m in p['messages']]),('/handsfree/imu',[m for p in imu['streams']['/handsfree/imu'] for m in p['messages']]))
 for topic,samples in topics:
  need(len(samples)==16,'SAMPLE_COUNT')
  differences=[(m['bag_record_time_ns']-m['header_stamp_ns'])/1000000 for m in samples]
  x=report['streams'][topic];k=x['record_minus_header_ms']
  need(k['count']==16 and eq(k['min'],min(differences)) and eq(k['median'],statistics.median(differences)) and eq(k['max'],max(differences)),'TIME_RESIDUAL:'+topic)
  need((x['negative_residual_count'],x['zero_residual_count'],x['positive_residual_count'])==(sum(v<0 for v in differences),sum(v==0 for v in differences),sum(v>0 for v in differences)),'RESIDUAL_SIGNS')
  pairs=(camera['pairs'] if topic==topics[0][0] else imu['streams'][topic]);fld='frames' if topic==topics[0][0] else 'messages'
  gaps=[(p[fld][1]['header_stamp_ns']-p[fld][0]['header_stamp_ns'])/1000000 for p in pairs]
  g=x['within_pair_header_gap_ms']
  need(g['count']==8 and eq(g['min'],min(gaps)) and eq(g['max'],max(gaps)) and eq(g['median'],statistics.median(gaps)),'PAIR_GAP')
 cam_heads=[m['header_stamp_ns'] for m in topics[0][1]]
 for topic,samples in topics[1:]:
  heads=[m['header_stamp_ns'] for m in samples]
  gaps=[min(abs(c-i) for i in heads)/1000000 for c in cam_heads]
  d=report['sparse_cross_stream_header_distances'][topic]
  measured=d['sampled_camera_to_nearest_sampled_imu_header_distance_ms']
  need(measured['count']==16 and eq(measured['min'],min(gaps)) and eq(measured['median'],statistics.median(gaps)) and eq(measured['max'],max(gaps)),'SPARSE_NEAREST')
  need(d['physical_clock_offset_candidate'] is None and d['not_a_synchronization_measurement'] is True,'NO_SYNC_ESTIMATE')
 need(report['streams']['/camera/imu']['negative_residual_count']>0,'NEGATIVE_CAMERA_IMU')
 need(len(report['scientific_gates'])==14 and all(v is False for v in report['scientific_gates'].values()),'CLOSED_GATES')
 need(all(report[k]==0 for k in ('real_pose_factors','health_labels','ate_rpe_scores')),'NO_SCIENCE')
 need(report['reference_timing_policy']=='UNVERIFIED_NO_ASSOCIATION_TOLERANCE' and report['mocap_invalid_rotation_records']==90,'REFERENCE')
 need(report['scientific_gates']['raw_bag_opened'] is False and report['scientific_gates']['confirmation_test_accessed'] is False,'HOLDOUT')
 need('not measured hardware' in plan_p.read_text().lower() and 'R52' in plan_p.read_text() and 'negative' in plan_p.read_text().lower(),'LIMITATION_PLAN')
 proof={'schema':'TRUST_ROBOT_R51_INDEPENDENT_CLOCK_EVIDENCE_VALIDATION_V1','source_report_sha256':sha(report_p),'plan_sha256':sha(plan_p),'authentic_frozen_sample_timestamps_recomputed':48,'independently_replayed_streams':3,'sparse_nearest_header_groups_recomputed':2,'physical_clock_or_reference_timing_admitted':False,'real_sensor_factors_authorized':False,'confirmation_test_used':False,'raw_bag_opened':False,'github_modified':False}
 with out_p.open('x') as h:json.dump(proof,h,sort_keys=True,indent=2);h.write('\n')
 print('R51_INDEPENDENT_48_RECORD_HEADER_PAIRS=EXACT_RECOMPUTE')
 print('R51_INDEPENDENT_ALL_STREAM_LAG_STATS_AND_SAMPLE_GAPS=MATCH')
 print('R51_INDEPENDENT_SPARSE_HEADER_DISTANCES=NOT_CLOCK_OFFSET')
 print('R51_INDEPENDENT_VALIDATION=PASS')

if __name__=='__main__':run(*(pathlib.Path(x) for x in sys.argv[1:6]))
