"""R51: descriptive ROS record/header residuals, not physical clock calibration."""
import hashlib,json,pathlib,statistics,subprocess,sys
BASE='58e23861811e51c5d00f00f5d22e5cb561c4b43a'
BAG='ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1'
SPLIT='017a388ef1ce4ad30812669632a022ca37c084871bc949693fd9c0541014238f'
SCHEMA='TRUST_ROBOT_R51_TRAIN_RECORD_HEADER_CLOCK_EVIDENCE_V1'
TOPICS=('/camera/color/image_raw/compressed','/camera/imu','/handsfree/imu')
FRAMES=('camera_color_optical_frame','camera_imu_optical_frame','base_link')
BLOCKED=(
 'sensor_common_physical_clock_verified','header_stamp_is_capture_event_verified',
 'bag_minus_header_is_transport_latency_verified','interstream_fixed_offset_qualified',
 'clock_drift_qualified','reference_physical_timestamp_verified',
 'mocap_body_alignment_qualified','reference_temporal_association_qualified',
 'qualified_sensor_factors_authorized','health_training_authorized',
 'ate_rpe_scoring_authorized','confirmation_test_accessed',
 'raw_bag_opened','github_modified'
)
ZERO=('real_pose_factors','health_labels','ate_rpe_scores')

def need(x,k):
 if not x:raise ValueError('R51_DENIED:'+k)
def sha(blob):return hashlib.sha256(blob).hexdigest()
def load(p):return json.loads(pathlib.Path(p).read_bytes())
def stats(values):
 need(len(values)>0 and all(type(x) in (int,float) for x in values),'NONFINITE_STATS')
 return {'count':len(values),'min':min(values),'median':statistics.median(values),'max':max(values)}

def extract(camera,imu):
 records={name:[] for name in TOPICS}
 for i,p in enumerate(camera['pairs']):
  need(p['pair_index']==i and len(p['frames'])==2,'CAMERA_PAIRS')
  need(p['metric_pose_qualified'] is False,'CAMERA_NONFACTOR')
  for m in p['frames']:
   need(m['connection_id']==4 and m['frame_id']==FRAMES[0] and (m['width'],m['height'])==(640,480),'CAMERA_FRAME')
   records[TOPICS[0]].append(m)
 for topic,connection,frame in ((TOPICS[1],0,FRAMES[1]),(TOPICS[2],1,FRAMES[2])):
  need(len(imu['streams'][topic])==8,'IMU_PAIRS:'+topic)
  for i,p in enumerate(imu['streams'][topic]):
   need(p['pair_index']==i and len(p['messages'])==2,'IMU_PAIR_ORDER')
   need(p['diagnostic']['position_estimate'] is None and p['diagnostic']['preintegration_factor'] is None,'IMU_NO_POSE')
   for m in p['messages']:
    need(m['connection_id']==connection and m['frame_id']==frame,'IMU_SOURCE_FRAME')
    records[topic].append(m)
 for topic,messages in records.items():
  need(len(messages)==16 and len(set(m['serialized_message_sha256'] for m in messages))==16,'UNIQUE_AUTHENTIC_SAMPLES:'+topic)
  for m in messages:
   need(type(m['bag_record_time_ns']) is int and type(m['header_stamp_ns']) is int and m['header_stamp_ns']>0 and m['bag_record_time_ns']>0,'CLOCK_COORDINATES')
 return records

def calculate(camera,imu):
 records=extract(camera,imu)
 output={}
 for topic,frame in zip(TOPICS,FRAMES):
  messages=records[topic]
  diffs=[m['bag_record_time_ns']-m['header_stamp_ns'] for m in messages]
  hdr=[m['header_stamp_ns'] for m in messages]
  pairs=(camera['pairs'] if topic==TOPICS[0] else imu['streams'][topic])
  gaps=[]
  for p in pairs:
   ms=p['frames'] if topic==TOPICS[0] else p['messages']
   gap=ms[1]['header_stamp_ns']-ms[0]['header_stamp_ns']
   need(gap>0,'NONPOSITIVE_PAIR_INTERVAL')
   gaps.append(gap)
  output[topic]={
   'native_frame':frame,
   'sample_count':16,'sampled_pair_count':8,
   'record_minus_header_ms':stats([x/1e6 for x in diffs]),
   'negative_residual_count':sum(x<0 for x in diffs),
   'zero_residual_count':sum(x==0 for x in diffs),
   'positive_residual_count':sum(x>0 for x in diffs),
   'within_pair_header_gap_ms':stats([x/1e6 for x in gaps]),
   'min_sample_header_ns':min(hdr),'max_sample_header_ns':max(hdr),
   'header_timestamp_is_physical_capture_verified':False,
   'record_minus_header_is_transport_latency_verified':False,
  }
 # Sparse nearest-neighbor sample distances are deliberately not synchronization estimates.
 camera_times=[m['header_stamp_ns'] for m in records[TOPICS[0]]]
 nearest={}
 for topic in TOPICS[1:]:
  imu_times=[m['header_stamp_ns'] for m in records[topic]]
  gaps=[min(abs(t-u) for u in imu_times)/1e6 for t in camera_times]
  nearest[topic]={
   'sampled_camera_to_nearest_sampled_imu_header_distance_ms':stats(gaps),
   'physical_clock_offset_candidate':None,
   'not_a_synchronization_measurement':True
  }
 return output,nearest

def policy(r):
 need(r.get('schema')==SCHEMA and r.get('trajectory_id')=='room_02' and r.get('split')=='train' and r.get('github_parent')==BASE and r.get('bag_sha256')==BAG,'SCOPE')
 need(r.get('measurement_class')=='DESCRIPTIVE_RECORD_AND_HEADER_COORDINATES_NOT_CLOCK_CALIBRATION','SCIENCE_CLASS')
 need(set(r.get('streams',{}))==set(TOPICS) and set(r.get('sparse_cross_stream_header_distances',{}))==set(TOPICS[1:]),'STREAM_INVENTORY')
 for topic,frame in zip(TOPICS,FRAMES):
  s=r['streams'][topic]
  need(s.get('native_frame')==frame and s.get('sample_count')==16 and s.get('sampled_pair_count')==8,'SAMPLE_COUNTS')
  need(s['negative_residual_count']+s['zero_residual_count']+s['positive_residual_count']==16,'RESIDUAL_COUNTS')
  need(s.get('header_timestamp_is_physical_capture_verified') is False and s.get('record_minus_header_is_transport_latency_verified') is False,'CLOCK_NOT_QUALIFIED')
 need(r['streams']['/camera/imu']['negative_residual_count']>0,'NEGATIVE_SAMPLE_PRESERVATION')
 need(r.get('camera_application_td_default_zero') is True and r.get('camera_application_estimate_td_default_zero') is True and r.get('author_defaults_not_capture_clock_proof') is True,'AUTHOR_DEFAULTS')
 need(r.get('reference_timing_policy')=='UNVERIFIED_NO_ASSOCIATION_TOLERANCE' and r.get('mocap_invalid_rotation_records')==90,'REFERENCE_POLICY')
 need(r.get('frozen_four_stream_clock_domains_unverified') is True and r.get('no_fixed_offset_selected_on_train') is True,'FROZEN_CLOCKS')
 need(set(r.get('scientific_gates',{}))==set(BLOCKED) and all(r['scientific_gates'][k] is False for k in BLOCKED),'GATES')
 need(all(type(r.get(k)) is int and r[k]==0 for k in ZERO),'ZERO_SCIENTIFIC_OUTPUTS')
 need(r.get('next_phase')=='R52_TRAIN_CLOCK_PROVENANCE_SENSITIVITY_AND_SOURCE_APPLICATION','NEXT')
 need(all(v['physical_clock_offset_candidate'] is None and v['not_a_synchronization_measurement'] is True for v in r['sparse_cross_stream_header_distances'].values()),'NO_SPARSE_OFFSET_FIT')

def run(repo,cam_p,imu_p,frame_p,r43_p,r46_p,r47_p,split_p,sync_p,ref_p,out_p,plan_p):
 files={'r33_camera':cam_p,'r34_imu':imu_p,'r35_frame':frame_p,'r43_receipts':r43_p,'r46_author':r46_p,'r47_recorder':r47_p,'split':split_p,'synchronization':sync_p,'reference_temporal_association':ref_p}
 for name,p in files.items():
  need(p.is_file() and not p.is_symlink() and 0<p.stat().st_size<4000000,'SOURCE_FILE:'+name)
 for name,p in (('m2dgr_trajectory_manifest_v1_split_freeze_v1.json',split_p),('m2dgr_synchronization_evidence_v1.json',sync_p),('m2dgr_reference_temporal_association_evidence_v1.json',ref_p)):
  frozen=subprocess.check_output(['git','-C',str(repo),'show',BASE+':manifests/'+name])
  need(frozen==p.read_bytes(),'FROZEN_MANIFEST:'+name)
 camera,imu,fr,r43,r46,r47,split,sync,ref=map(load,files.values())
 need(sha(split_p.read_bytes())==SPLIT,'FROZEN_SPLIT_SHA')
 room=[x for x in split['records'] if x['trajectory_id']=='room_02']
 need(len(room)==1 and room[0]['split']=='train' and sum(x['split']=='confirmation_test' for x in split['records'])==7,'TRAIN_COHORT')
 need(len(room[0]['streams'])==4 and all(x['verification_status']=='unverified' and x['fixed_offset_seconds'] is None and x['tolerance_seconds'] is None for x in room[0]['synchronization']),'FOUR_UNQUALIFIED_CLOCKS')
 need(r43['unresolved_gate_count']==11 and r43['room_02_reference_invalid_rotations']==90 and r43['source_acquisition_status']=='NOT_ACQUIRED','R43_REFERENCE')
 need(r46['comparisons']['td_is_default_not_physical_clock_proof'] is True and r46['physical_calibration_qualified'] is False,'AUTHOR_DEFAULT')
 need(r47['compatibility']['recorded_color_frame_id']==FRAMES[0] and r47['compatibility']['camera_imu_recorded_frame_id']==FRAMES[1] and r47['compatibility']['handsfree_recorded_frame_id']==FRAMES[2] and r47['capture_time_physically_verified'] is False,'RECORDER_FRAME')
 need(fr['streams'][TOPICS[1]]['summary']['orientation_covariance_unknown_samples']==16 and fr['streams'][TOPICS[2]]['summary']['orientation_covariance_unknown_samples']==0,'ORIENTATION_FRAME_DIFFERENCE')
 need(sync['observations']['bag_record_clock']['transport_latency_separated_from_clock_offset'] is False and sync['observations']['sensor_header_epoch']['verified_common_physical_clock'] is False,'PRIOR_SYNC_BLOCK')
 interpretation=ref['observations']['interpretation']
 need(interpretation['reference_to_estimator_temporal_association_verified'] is False and interpretation['association_tolerance_supported'] is False and interpretation['nearest_neighbor_pose_association_authorized'] is False,'FROZEN_REFERENCE_TIMING')
 need(camera['pair_count']==8 and imu['serialized_imu_messages_inspected']==32,'FROZEN_SAMPLE_COUNT')
 stats_by_topic,sparse=calculate(camera,imu)
 report={
  'schema':SCHEMA,'trajectory_id':'room_02','split':'train','github_parent':BASE,'bag_sha256':BAG,
  'measurement_class':'DESCRIPTIVE_RECORD_AND_HEADER_COORDINATES_NOT_CLOCK_CALIBRATION',
  'source_sha256':{k:sha(p.read_bytes()) for k,p in files.items()},
  'streams':stats_by_topic,'sparse_cross_stream_header_distances':sparse,
  'camera_application_td_default_zero':True,
  'camera_application_estimate_td_default_zero':True,
  'author_defaults_not_capture_clock_proof':True,
  'reference_timing_policy':'UNVERIFIED_NO_ASSOCIATION_TOLERANCE',
  'mocap_invalid_rotation_records':90,
  'frozen_four_stream_clock_domains_unverified':True,
  'no_fixed_offset_selected_on_train':True,
  'scientific_gates':{k:False for k in BLOCKED},
  **{k:0 for k in ZERO},
  'next_phase':'R52_TRAIN_CLOCK_PROVENANCE_SENSITIVITY_AND_SOURCE_APPLICATION'
 }
 policy(report)
 with out_p.open('x') as h:json.dump(report,h,sort_keys=True,indent=2,allow_nan=False);h.write('\n')
 lines=['# R51 — TRAIN room_02 sampled timestamp and reference-evidence audit','',
 'These are header and bag-record **timestamp coordinate differences**, not measured hardware clock offsets or verified nonnegative transport latencies. Only previously decoded frozen TRAIN samples were accessed; no ROS bag bytes were reopened.','',
 '## Sampled record-time minus header-time residuals (milliseconds)','',
 '| Stream | N | Median | Min | Max | Negative residuals |','|---|---:|---:|---:|---:|---:|']
 for topic in TOPICS:
  s=stats_by_topic[topic];x=s['record_minus_header_ms']
  lines.append(f"| `{topic}` | {x['count']} | {x['median']:.6f} | {x['min']:.6f} | {x['max']:.6f} | {s['negative_residual_count']} |")
 lines.extend(['','The camera-IMU sample includes negative bag-minus-header residuals. A nonnegative transport-delay interpretation therefore fails without verified physical clock domains, event semantics and recorder mapping.','',
 '## Sparse camera-to-IMU header distances','',
 'The following are **nearest distances between only 16 preselected camera stamps and 16 sparse IMU stamps per topic**. Do not use these to estimate a fixed clock offset, fit drift, or choose temporal association tolerance.',''])
 for topic in TOPICS[1:]:
  d=sparse[topic]['sampled_camera_to_nearest_sampled_imu_header_distance_ms']
  lines.append(f"- `{topic}`: median {d['median']:.6f} ms; range {d['min']:.6f}–{d['max']:.6f} ms (sparse samples only)")
 lines.extend(['','## Author and frozen reference semantics','',
 '- Published camera application has `td=0` and `estimate_td=0`; these are settings, **not capture-clock calibration**.',
 '- Original frozen TRAIN manifest lists four **unverified** sensor clock domains and supplies no fixed physical offset or tolerance.',
 '- Frozen reference-temporal evidence does not authorize nearest-neighbor evaluation association, a fixed mocap offset or interpolation.',
 '- Mocap index reports 90 invalid rotation records, and its body origin and timestamp event still require physical qualification.',
 '- Camera color, camera IMU and HandsFree IMU are distinct native sensor-frame receipts.',
 '', '## Next R52','',
 'If source timing metadata is obtained, qualify measurement-event definitions and independent clock mappings before calibration-driven factor fusion. Existing numerical camera and IMU diagnostics remain engineering-only.','',
 'No confirmation-test data, real pose factors, health labels, ATE/RPE, Git changes or autonomous robot actions are authorized.',''])
 with plan_p.open('x') as h:h.write('\n'.join(lines))
 print('R51_AUTHENTIC_SAMPLED_RECORD_HEADER_PAIRS=48_FROM_FROZEN_REPORTS')
 for topic,tag in ((TOPICS[0],'CAMERA_COLOR'),(TOPICS[1],'CAMERA_IMU'),(TOPICS[2],'HANDSFREE_IMU')):
  x=stats_by_topic[topic]
  print('R51_'+tag+'_BAG_MINUS_HEADER_MEDIAN_MS=%.6f'%x['record_minus_header_ms']['median'])
  print('R51_'+tag+'_NEGATIVE_RESIDUAL_SAMPLES=%d'%x['negative_residual_count'])
 print('R51_SPARSE_CROSS_STREAM_NEAREST_HEADERS=DESCRIPTIVE_NOT_SYNC')
 print('R51_PHYSICAL_CLOCK_REFERENCE_AND_REAL_FACTORS=NOT_QUALIFIED')

if __name__=='__main__':run(*(pathlib.Path(p) for p in sys.argv[1:13]))
