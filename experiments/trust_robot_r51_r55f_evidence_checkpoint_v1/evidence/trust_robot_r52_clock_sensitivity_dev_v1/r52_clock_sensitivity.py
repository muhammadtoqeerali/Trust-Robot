"""R52: counterfactual timestamp-coordinate sensitivity, never offset fitting."""
import hashlib,json,pathlib,statistics,subprocess,sys
BASE='58e23861811e51c5d00f00f5d22e5cb561c4b43a'
BAG='ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1'
SCHEMA='TRUST_ROBOT_R52_TRAIN_CLOCK_PROVENANCE_SENSITIVITY_V1'
TOPICS=('/camera/color/image_raw/compressed','/camera/imu','/handsfree/imu')
FRAMES=('camera_color_optical_frame','camera_imu_optical_frame','base_link')
SHIFTS=(-20,-5,-1,0,1,5,20)
LOCAL=(-1,0,1)
GATES=('sensor_common_physical_clock_verified','header_stamp_is_capture_event_verified',
 'bag_minus_header_is_transport_latency_verified','interstream_fixed_offset_qualified',
 'clock_drift_qualified','reference_physical_timestamp_verified',
 'mocap_body_alignment_qualified','reference_temporal_association_qualified',
 'qualified_sensor_factors_authorized','health_training_authorized',
 'ate_rpe_scoring_authorized','confirmation_test_accessed','raw_bag_opened','github_modified')
ZERO=('real_pose_factors','health_labels','ate_rpe_scores')

def need(ok,reason):
 if not ok:raise ValueError('R52_DENIED:'+reason)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def summary(v):
 need(len(v)>0,'EMPTY_STATISTIC')
 return {'count':len(v),'min':min(v),'median':statistics.median(v),'max':max(v)}
def observations(camera,imu):
 result={TOPICS[0]:[m for p in camera['pairs'] for m in p['frames']]}
 for t in TOPICS[1:]:result[t]=[m for p in imu['streams'][t] for m in p['messages']]
 for t,frame in zip(TOPICS,FRAMES):
  need(len(result[t])==16,'AUTHENTIC_COUNT:'+t)
  need(all(m['frame_id']==frame and type(m['header_stamp_ns']) is int and type(m['bag_record_time_ns']) is int for m in result[t]),'AUTHENTIC_FRAME_AND_STAMP:'+t)
  need(len({m['serialized_message_sha256'] for m in result[t]})==16,'AUTHENTIC_UNIQUENESS:'+t)
 return result

def calculate(camera,imu):
 source=observations(camera,imu)
 camera_h=[m['header_stamp_ns'] for m in source[TOPICS[0]]]
 cases={}
 for topic in TOPICS[1:]:
  imu_h=[m['header_stamp_ns'] for m in source[topic]]
  entries=[]
  for shift in SHIFTS:
   shifted=(x+shift*1000000 for x in camera_h)
   dist_ns=[min(abs(c-h) for h in imu_h) for c in shifted]
   need(len(dist_ns)==16,'SHIFT_COUNT')
   entries.append({'hypothetical_camera_header_shift_ms':shift,
       'sparse_nearest_header_distance_ms':summary([v/1000000 for v in dist_ns]),
       'physical_clock_offset_estimate':None,'association_tolerance':None,
       'scenario_only_not_clock_fit':True})
  cases[topic]=entries
 signs={}
 for topic in TOPICS:
  samples=source[topic]
  rows=[]
  for ms in LOCAL:
   residuals=[m['bag_record_time_ns']-m['header_stamp_ns']-ms*1000000 for m in samples]
   rows.append({'hypothetical_header_shift_ms':ms,
       'negative_residual_count':sum(x<0 for x in residuals),
       'zero_residual_count':sum(x==0 for x in residuals),
       'positive_residual_count':sum(x>0 for x in residuals),
       'record_minus_header_ms':summary([v/1000000 for v in residuals]),
       'transport_latency_measurement':False})
  signs[topic]=rows
 return cases,signs

def policy(r):
 need(r.get('schema')==SCHEMA and r.get('trajectory_id')=='room_02' and r.get('split')=='train' and r.get('github_parent')==BASE and r.get('bag_sha256')==BAG,'SOURCE_SCOPE')
 need(r.get('measurement_class')=='COUNTERFACTUAL_HEADER_COORDINATE_SENSITIVITY_NOT_PHYSICAL_CLOCK_FIT','INTERPRETATION')
 need(r.get('samples_per_stream')==16 and r.get('authentic_frozen_messages')==48,'SAMPLES')
 need(r.get('hypothetical_camera_header_shifts_ms')==list(SHIFTS) and r.get('hypothetical_single_stream_header_shifts_ms')==list(LOCAL),'PREDECLARED_SHIFTS')
 need(set(r.get('sparse_cross_stream_scenarios',{}))==set(TOPICS[1:]) and set(r.get('record_header_sign_scenarios',{}))==set(TOPICS),'STREAM_SET')
 for topic in TOPICS[1:]:
  rows=r['sparse_cross_stream_scenarios'][topic]
  need(len(rows)==7 and [x.get('hypothetical_camera_header_shift_ms') for x in rows]==list(SHIFTS),'CROSS_SHIFT_LIST')
  need(all(x.get('physical_clock_offset_estimate') is None and x.get('association_tolerance') is None and x.get('scenario_only_not_clock_fit') is True and x.get('sparse_nearest_header_distance_ms',{}).get('count')==16 for x in rows),'NO_SYNCHRONIZATION_PROMOTION')
 for topic in TOPICS:
  rows=r['record_header_sign_scenarios'][topic]
  need(len(rows)==3 and [x.get('hypothetical_header_shift_ms') for x in rows]==list(LOCAL),'LOCAL_SHIFT_LIST')
  need(all(x.get('transport_latency_measurement') is False and x.get('record_minus_header_ms',{}).get('count')==16 and sum(x.get(k,-1) for k in ('negative_residual_count','zero_residual_count','positive_residual_count'))==16 for x in rows),'NO_TRANSPORT_PROMOTION')
 need(r['record_header_sign_scenarios'][TOPICS[1]][1]['negative_residual_count']==9,'NEGATIVE_RESIDUAL_PRESERVED')
 need(r.get('four_streams_fixed_physical_offset_unverified') is True and r.get('physical_offset_selected') is None and r.get('association_tolerance_selected') is None and r.get('clock_drift_model_selected') is None,'NO_OFFSET_FIT')
 need(r.get('reference_mocap_invalid_rotation_records')==90 and r.get('reference_temporal_association_authorized') is False and r.get('author_td_zero_is_physical_time_sync') is False,'REFERENCE_BOUNDARY')
 need(set(r.get('scientific_gates',{}))==set(GATES) and all(v is False for v in r['scientific_gates'].values()),'CLOSED_GATES')
 need(all(type(r.get(k)) is int and r[k]==0 for k in ZERO),'ZERO_SCIENTIFIC_OUTPUTS')
 need(r.get('next_phase')=='R53_TRAIN_SENSOR_TIMING_RECEIPT_ADMISSION_BOUNDARY','NEXT')

def run(repo,cam_p,imu_p,r51p,v51p,r43p,r47p,splitp,syncp,refp,outp,planp):
 files={'r33_camera':cam_p,'r34_imu':imu_p,'r51_report':r51p,'r51_independent':v51p,'r43_protocol':r43p,'r47_applicability':r47p,'split_manifest':splitp,'sync_manifest':syncp,'ref_temporal_manifest':refp}
 for k,p in files.items():need(p.is_file() and not p.is_symlink() and 0<p.stat().st_size<4000000,'INPUT_FILE:'+k)
 for filename,p in (('m2dgr_trajectory_manifest_v1_split_freeze_v1.json',splitp),('m2dgr_synchronization_evidence_v1.json',syncp),('m2dgr_reference_temporal_association_evidence_v1.json',refp)):
  committed=subprocess.check_output(['git','-C',str(repo),'show',BASE+':manifests/'+filename])
  need(p.read_bytes()==committed,'COMMIT_SCOPED_MANIFEST:'+filename)
 cam,imu,r51,v51,r43,r47,split,sync,reference=map(read,files.values())
 need(r51['schema']=='TRUST_ROBOT_R51_TRAIN_RECORD_HEADER_CLOCK_EVIDENCE_V1' and r51['trajectory_id']=='room_02' and r51['split']=='train' and r51['github_parent']==BASE,'R51_SOURCE')
 need(v51['source_report_sha256']==digest(r51p) and v51['authentic_frozen_sample_timestamps_recomputed']==48 and v51['physical_clock_or_reference_timing_admitted'] is False,'R51_INDEPENDENT')
 need(r51['source_sha256']['r33_camera']==digest(cam_p) and r51['source_sha256']['r34_imu']==digest(imu_p),'R51_FROZEN_LINEAGE')
 need(r51['streams'][TOPICS[1]]['negative_residual_count']==9 and all(r51['streams'][t]['sample_count']==16 for t in TOPICS),'R51_CLOCK_COUNTS')
 need(r43['source_acquisition_status']=='NOT_ACQUIRED' and r43['unresolved_gate_count']==11 and r43['room_02_reference_invalid_rotations']==90,'R43_UNQUALIFIED_REFERENCE')
 need(r47['capture_time_physically_verified'] is False and r47['compatibility']['camera_imu_recorded_frame_id']==FRAMES[1] and r47['compatibility']['handsfree_recorded_frame_id']==FRAMES[2],'R47_FRAME_CONTEXT')
 rows=[x for x in split['records'] if x['trajectory_id']=='room_02']
 need(len(rows)==1 and rows[0]['split']=='train' and sum(x['split']=='confirmation_test' for x in split['records'])==7,'FROZEN_HOLDOUT')
 need(len(rows[0]['synchronization'])==4 and all(x['verification_status']=='unverified' and x['fixed_offset_seconds'] is None and x['tolerance_seconds'] is None for x in rows[0]['synchronization']),'NO_RELEASED_OFFSET')
 need(sync['observations']['bag_record_clock']['transport_latency_separated_from_clock_offset'] is False and sync['observations']['sensor_header_epoch']['verified_common_physical_clock'] is False,'SOURCE_CLOCK_UNVERIFIED')
 interp=reference['observations']['interpretation']
 need(interp['reference_to_estimator_temporal_association_verified'] is False and interp['association_tolerance_supported'] is False and interp['nearest_neighbor_pose_association_authorized'] is False,'FROZEN_MOCAP_POLICY')
 need(cam['pair_count']==8 and imu['serialized_imu_messages_inspected']==32,'AUTHENTIC_SAMPLE_SCOPE')
 cases,signs=calculate(cam,imu)
 for topic in TOPICS[1:]:
  baseline=next(x for x in cases[topic] if x['hypothetical_camera_header_shift_ms']==0)['sparse_nearest_header_distance_ms']
  recorded=r51['sparse_cross_stream_header_distances'][topic]['sampled_camera_to_nearest_sampled_imu_header_distance_ms']
  need(all(abs(baseline[k]-recorded[k])<1e-9 for k in ('min','median','max')),'R51_ZERO_SCENARIO:'+topic)
 for topic in TOPICS:
  baseline=signs[topic][1]
  need(baseline['negative_residual_count']==r51['streams'][topic]['negative_residual_count'],'ZERO_SIGN:'+topic)
  need(abs(baseline['record_minus_header_ms']['median']-r51['streams'][topic]['record_minus_header_ms']['median'])<1e-9,'ZERO_MEDIAN:'+topic)
 report={'schema':SCHEMA,'trajectory_id':'room_02','split':'train','github_parent':BASE,'bag_sha256':BAG,'measurement_class':'COUNTERFACTUAL_HEADER_COORDINATE_SENSITIVITY_NOT_PHYSICAL_CLOCK_FIT','source_sha256':{name:digest(p) for name,p in files.items()},'authentic_frozen_messages':48,'samples_per_stream':16,'hypothetical_camera_header_shifts_ms':list(SHIFTS),'hypothetical_single_stream_header_shifts_ms':list(LOCAL),'sparse_cross_stream_scenarios':cases,'record_header_sign_scenarios':signs,'four_streams_fixed_physical_offset_unverified':True,'physical_offset_selected':None,'association_tolerance_selected':None,'clock_drift_model_selected':None,'reference_mocap_invalid_rotation_records':90,'reference_temporal_association_authorized':False,'author_td_zero_is_physical_time_sync':False,'scientific_gates':{k:False for k in GATES},**{k:0 for k in ZERO},'next_phase':'R53_TRAIN_SENSOR_TIMING_RECEIPT_ADMISSION_BOUNDARY'}
 policy(report)
 with outp.open('x') as h:json.dump(report,h,sort_keys=True,indent=2,allow_nan=False);h.write('\n')
 lines=['# R52 — Clock provenance and hypothetical timestamp sensitivity (TRAIN room_02)','','**All shifted timestamps are manufactured counterfactual coordinates; no offset or tolerance is estimated.** Exactly 48 authentic timestamp receipts from frozen R33/R34 reports; the raw bag and confirmation_test were not opened.','','## Predeclared header-shift scenarios','','The camera header stamps alone are shifted by −20, −5, −1, 0, +1, +5 and +20 ms. For each shift, we recompute the *nearest of only 16 sampled IMU header stamps* per stream; this sparsity creates arbitrary nearest-neighbor selection, not a physical synchronization measurement.','','| Stream | Shift (ms) | Sparse nearest median (ms) | Sparse nearest max (ms) |','|---|---:|---:|---:|']
 for topic in TOPICS[1:]:
  for row in cases[topic]:
   s=row['sparse_nearest_header_distance_ms'];lines.append(f"| `{topic}` | {row['hypothetical_camera_header_shift_ms']} | {s['median']:.6f} | {s['max']:.6f} |")
 lines.extend(['','## Header-vs-record residual thought experiment','','Shifting a given stream header by ±1 ms changes the algebraic `bag_record_stamp − header_stamp`. This is a **coordinate-sensitivity demonstration**, not recorder-latency estimation. The camera IMU has nine negative values at the unshifted baseline.','','| Stream | Header shift (ms) | Negative of 16 | Median record−header (ms) |','|---|---:|---:|---:|'])
 for topic in TOPICS:
  for row in signs[topic]:lines.append(f"| `{topic}` | {row['hypothetical_header_shift_ms']} | {row['negative_residual_count']} | {row['record_minus_header_ms']['median']:.6f} |")
 lines.extend(['','## Scientific boundary','','No physical event timestamps, hardware clock domain/oscillator relations, cross-stream clock offset/drift, mocap tracked-body origin, or mocap reference association tolerances are verified. R43 source receipts remain unfilled and mocap quality records 90 invalid rotations. Application default `td=0` must not be promoted into a clock result.','','No offset, drift, temporal association tolerance, real pose factor, health label or ATE/RPE result is authorized. Confirmation-test trajectories stay sealed.','','## Next R53','','Specify independently auditable capture-event, clock-domain and mocap export source receipts before future physical synchronization or factor admission.',''])
 with planp.open('x') as h:h.write('\n'.join(lines))
 print('R52_FROZEN_AUTHENTIC_MESSAGE_TIMESTAMPS=48')
 print('R52_COUNTERFACTUAL_CAMERA_HEADER_SHIFTS=7_PER_IMU_STREAM')
 print('R52_SPARSE_NEAREST_HEADER_SCENARIOS=224_DESCRIPTIVE_DISTANCES')
 print('R52_RECORD_MINUS_HEADER_SIGN_SCENARIOS=144_DESCRIPTIVE_RESIDUALS')
 print('R52_UNSHIFTED_CAMERA_IMU_NEGATIVE_RESIDUALS=9')
 print('R52_PHYSICAL_CLOCK_OFFSET_AND_ASSOCIATION=NOT_QUALIFIED')
if __name__=='__main__':run(*(pathlib.Path(x) for x in sys.argv[1:13]))
