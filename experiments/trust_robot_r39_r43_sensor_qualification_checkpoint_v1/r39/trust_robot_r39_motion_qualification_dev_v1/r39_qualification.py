"""R39 evidence-derived qualification plan. No raw bag, pose factors or test split."""
import hashlib, json, math, pathlib, statistics, sys

BASE='df78336320b3b026e448a09d39dfc571f922ae00'
BAG='ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1'
STREAMS=('/camera/imu','/handsfree/imu')
FRAMES={'/camera/imu':'camera_imu_optical_frame','/handsfree/imu':'base_link'}

PINS={
 'lidar_pairs':('C/r29/r29_lidar_multipair_diagnostics_v1.json','5af225ff0ac9225fb16828a6ffacda4e1efcaddc69564f363095d8fe1071402b'),
 'lidar_geometry':('C/r30/r30_geometry_confidence_limits_v1.json','373fe8993ccf6afa82bed9fd8f5197954e4b5412bc69d9558914dd08195d8f7d'),
 'camera_pairs':('D/r33/trust_robot_r33_camera_multipair_result_v1/r33_camera_multipair_pixel_diagnostics_v1.json','1e74e18205b8429d88632826f1f3c30055165352228a19aefa1064432b2853b1'),
 'imu_intervals':('D/r34/trust_robot_r34_imu_short_interval_result_v1/r34_imu_short_interval_diagnostics_v1.json','778c223c6c034343413ff848db6276aecdd730390311f178cb918b94ee10064e'),
 'imu_variation':('D/r35/trust_robot_r35_imu_variation_frame_result_v1/r35_imu_variation_frame_v1.json','a0fbf5931833dfecb609f82e27fdd13fa2fc4dbfead8dbb106a99af162698e1e'),
 'gyro_windows':('D/r36/trust_robot_r36_gyro_windows_result_v1/r36_gyro_window_candidates_v1.json','c025f71eeb8a8467c0ca86cbec079d1bf0d977841d25140750d813d89a54714a'),
 'readiness':('D/r37/trust_robot_r37_checkpoint_readiness_result_v1/r37_readiness_report_v1.json','185c91251dbe9342023155f24db4ba4800b32489a3d1f9af956188f7f5bccc4a'),
}

GATES=(
 'physical_capture_time_verified',
 'camera_intrinsics_qualified',
 'lidar_extrinsics_qualified',
 'imu_bias_noise_and_gravity_qualified',
 'cross_modal_alignment_qualified',
 'independent_reference_trajectory_qualified',
 'measurement_covariance_calibrated',
 'metric_camera_scale_qualified',
 'real_pose_factors_authorized',
 'health_model_training_authorized',
 'm2dgr_scoring_authorized',
 'confirmation_test_accessed',
 'statistical_stability_established',
 'raw_bag_reopened',
 'github_modified'
)
ZERO=('scientific_pose_factors','health_labels','ate_rpe_scores')

def need(ok,why):
 if not ok: raise ValueError('R39_DENIED:'+why)

def sha(b): return hashlib.sha256(b).hexdigest()

def load(p): return json.loads(pathlib.Path(p).read_text())

def triple(a):
 need(len(a)>0 and all(type(x) in (int,float) and math.isfinite(x) for x in a),'NONFINITE_DATA')
 return {'min':float(min(a)),'median':float(statistics.median(a)),'max':float(max(a))}

def paths(c,d):
 return {k:((c if rel.startswith('C/') else d)/rel[2:],expected) for k,(rel,expected) in PINS.items()}

def inputs(c,d):
 files=paths(c,d)
 raw={}
 for name,(p,expected) in files.items():
  need(p.is_file() and not p.is_symlink() and p.stat().st_nlink==1 and p.stat().st_size<4000000,'SOURCE_FILE:'+name)
  need(sha(p.read_bytes())==expected,'SOURCE_SHA:'+name)
  raw[name]=load(p)
 for name,r in raw.items():
  need(r['trajectory_id']=='room_02' and r['split']=='train','TRAIN:'+name)
  need(r.get('authenticated_bag_sha256',r.get('bag_sha256'))==BAG,'BAG:'+name)
 for name in ('lidar_pairs','lidar_geometry','camera_pairs','imu_intervals','imu_variation','gyro_windows'):
  need(raw[name]['real_pose_factors_generated']==0 and raw[name]['health_labels_generated']==0 and raw[name]['real_sensor_factor_execution_authorized'] is False,'FACTOR_DENIED:'+name)
 need(raw['readiness']['scientific_pose_factors']==0 and raw['readiness']['readiness_decision'].startswith('READY_FOR_SHA_PINNED_'),'ARCHIVAL_ONLY')
 return raw

def evaluate(raw):
 lp=raw['lidar_pairs']
 lg=raw['lidar_geometry']
 cp=raw['camera_pairs']
 im=raw['imu_intervals']
 iv=raw['imu_variation']
 gw=raw['gyro_windows']

 need(lp['pair_count']==lg['pair_count']==cp['pair_count']==8,'PAIRS')
 need(im['serialized_imu_messages_inspected']==32 and gw['source_message_count']==48,'IMU_MESSAGES')
 need(lg['r29_sha256']==PINS['lidar_pairs'][1],'LIDAR_CHAIN')
 need(im['source_report_sha256']['r33']==PINS['camera_pairs'][1],'CAMERA_TO_IMU_CHAIN')
 need(iv['r34_source_report_sha256']==PINS['imu_intervals'][1] and gw['source_report_sha256']['r35']==PINS['imu_variation'][1],'IMU_CHAIN')

 improvements=[]
 closures_m=[]
 closures_deg=[]
 ratios=[]

 for i,(p,q) in enumerate(zip(lp['pairs'],lg['pairs'])):
  need(p['pair_index']==q['pair_index']==i,'LIDAR_ORDER')
  need(q['source_message_sha256']==[x['serialized_message_sha256'] for x in p['scans']],'SCAN_BIND')
  reg=p['registration']
  before=reg['identity_nearest_neighbor_rmse_m']
  after=reg['candidate_nearest_neighbor_rmse_m']
  need(before>0 and after>=0 and math.isfinite(after) and reg['candidate_registered_as_factor'] is False,'LIDAR_NONFACTOR')
  improvements.append(float(before-after))
  closures_m.append(float(q['inverse_consistency']['roundtrip_translation_m']))
  closures_deg.append(float(q['inverse_consistency']['roundtrip_rotation_deg']))
  ratios.append(float(min(g['smallest_over_largest_eigenvalue'] for g in q['geometry'])))

 need(len(improvements)==8 and all(x>0 for x in improvements),'LIDAR_RESIDUAL_RESULT')

 camera_pixels=[]
 camera_tracks=[]

 for i,p in enumerate(cp['pairs']):
  need(p['pair_index']==i and len(p['frames'])==2 and p['metric_pose_qualified'] is False,'CAMERA_ORDER')
  m=p['pixel_motion']
  need(m['camera_pose_factor'] is None and m['metric_translation_m'] is None,'CAMERA_NO_POSE')
  need(m['initial_corner_count']>0 and 0<=m['forward_backward_consistent_count']<=m['initial_corner_count'],'CAMERA_TRACKS')
  need(m['median_displacement_px'] is not None and math.isfinite(m['median_displacement_px']),'CAMERA_PX')
  camera_pixels.append(float(m['median_displacement_px']))
  camera_tracks.append(float(m['forward_backward_consistent_count']/m['initial_corner_count']))

 imu={}

 for topic in STREAMS:
  need(iv['streams'][topic]['recorded_frame_id']==FRAMES[topic],'IMU_FRAME')
  need(len(im['streams'][topic])==len(iv['streams'][topic]['intervals'])==len(gw['streams'][topic])==8,'IMU_COUNTS')

  times=[float(x['observed_header_dt_ms_not_capture_clock_proof']) for x in iv['streams'][topic]['intervals']]
  gaps=[float(v*1e-6) for w in gw['streams'][topic] for v in w['gyro_numerics']['header_gaps_ns']]
  angles=[float(w['gyro_numerics']['two_step_composed_rotation_angle_rad_diagnostic']) for w in gw['streams'][topic]]

  for w in gw['streams'][topic]:
   need(w['physically_qualified_rotation'] is False and w['gyro_numerics']['factor'] is None,'IMU_NO_POSE')

  imu[topic]={
    'recorded_frame':FRAMES[topic],
    'two_sample_header_gap_ms':triple(times),
    'three_sample_header_gap_ms':triple(gaps),
    'three_sample_numeric_rotation_angle_rad':triple(angles),
    'recorded_orientation_unknown_count_of_16':iv['streams'][topic]['summary']['orientation_covariance_unknown_samples'],
    'capture_time_physically_verified':False,
    'inertial_pose_qualified':False,
  }

 need(imu[STREAMS[0]]['recorded_orientation_unknown_count_of_16']==16 and imu[STREAMS[1]]['recorded_orientation_unknown_count_of_16']==0,'ORIENTATION_DISTINCTION')

 return {
  'lidar':{
   'adjacent_train_pairs':8,
   'distinct_scans':16,
   'rmse_reduction_m':triple(improvements),
   'inverse_roundtrip_translation_m':triple(closures_m),
   'inverse_roundtrip_rotation_deg':triple(closures_deg),
   'minimum_eigenvalue_ratio_over_pairs':triple(ratios),
   'independent_pose_accuracy_known':False
  },
  'camera':{
   'train_pairs':8,
   'distinct_frames':16,
   'median_pixel_displacement_px':triple(camera_pixels),
   'tracked_feature_fraction':triple(camera_tracks),
   'metric_camera_pose_known':False
  },
  'imu':imu,
 }

STEPS=[
 ('R40',
  'Inspect native calibration, camera intrinsics/distortion, LiDAR-IMU-camera extrinsics, TF frames, clock sources and independent TRAIN references; log exact provenance and missing items without promoting filename matches',
  'Create asset inventory and explicit unverified-calibration ledger on TRAIN-only data'),
 ('R41',
  'Establish separate message-header vs acquisition-clock semantics and estimate inter-stream offset/drift using TRAIN only; verify capture-time basis independently',
  'Document time-domain conversion, residual statistics, sensitivity and rejection criteria before motion factors'),
 ('R42',
  'Verify camera intrinsics and distortion; develop outlier-robust image correspondence/epipolar geometry and an independent metric scale source',
  'Evaluate relative geometry without asserting metric motion until scale and external reference pass'),
 ('R43',
  'Develop LiDAR correspondence robustness, initialization and degeneracy rejection across multiple TRAIN trajectories, with independent registration reference and covariance diagnostics',
  'Predeclare factor rejection criteria using calibration/validation only'),
 ('R44',
  'Estimate gyro/accelerometer bias and noise, gravitational frame conventions and IMU extrinsics; compare calibrated inertial windows against independently verified references',
  'Only then implement covariance-aware preintegration with numerical and physical checks'),
 ('R45',
  'Qualify independent timestamp-associated SE3 reference, coordinate transforms, validation-calibrated factor covariance and frozen estimator variants',
  'Begin limited TRAIN/validation real-backbone trial only after prior gates; leave confirmation_test held out'),
]

def safety(result):
 need(result.get('schema')=='TRUST_ROBOT_R39_TRAIN_RECORDED_SENSOR_QUALIFICATION_PLAN_V1' and result.get('trajectory_id')=='room_02' and result.get('split')=='train' and result.get('github_baseline')==BASE,'SCOPE')
 need(result.get('authenticated_bag_sha256')==BAG and result.get('decision')=='DIAGNOSTICS_VERIFIED_QUALIFIED_REAL_FACTORS_BLOCKED','DECISION')
 need(result.get('source_sha256')=={k:v[1] for k,v in PINS.items()},'SOURCES')
 need(all(result.get(k) is False for k in GATES),'SCIENTIFIC_PROMOTION')
 need(all(type(result.get(k)) is int and result[k]==0 for k in ZERO),'NONZERO_SCIENTIFIC_RESULT')
 need(result.get('next_phase')=='R40_CALIBRATION_CLOCK_REFERENCE_ASSET_INVENTORY' and len(result.get('work_sequence',[]))==len(STEPS),'NEXT_PLAN')
 need(result.get('metrics',{}).get('lidar',{}).get('adjacent_train_pairs')==8 and result.get('metrics',{}).get('camera',{}).get('train_pairs')==8 and set(result.get('metrics',{}).get('imu',{}))==set(STREAMS),'METRICS')
 need(all(x.get('status')=='NOT_QUALIFIED' for x in result.get('qualification_gates',{}).values()),'QUALIFICATION_FLAGS')

def markdown(result):
 m=result['metrics']
 f=lambda n:format(n,'.6f')

 s=[
  '# TRUST-ROBOT R39: Recorded sensor-motion qualification plan',
  '',
  'Based only on frozen TRAIN `room_02` engineering evidence. **Do not treat any item below as calibrated pose accuracy.**',
  '',
  '## Measured engineering evidence',
  '',
  '| Stream | Observed diagnostic | Qualification |',
  '|---|---|---|',
  f"| LiDAR | 8 adjacent scan pairs; median NN RMSE reduction {f(m['lidar']['rmse_reduction_m']['median'])} m; maximum forward/reverse round-trip discrepancy {f(m['lidar']['inverse_roundtrip_translation_m']['max'])} m, {f(m['lidar']['inverse_roundtrip_rotation_deg']['max'])} deg | Not independently pose-scored |",
  f"| Camera | 8 frame pairs, 16 frames; median-of-pairs pixel displacement {f(m['camera']['median_pixel_displacement_px']['median'])} px; minimum tracked fraction {f(m['camera']['tracked_feature_fraction']['min'])} | Not a metric camera pose |",
  f"| Camera IMU | Native frame `{m['imu']['/camera/imu']['recorded_frame']}`; header interval median {f(m['imu']['/camera/imu']['two_sample_header_gap_ms']['median'])} ms; orientation-unknown 16/16 | Capture clock and calibration unverified |",
  f"| HandsFree IMU | Native frame `{m['imu']['/handsfree/imu']['recorded_frame']}`; header interval median {f(m['imu']['/handsfree/imu']['two_sample_header_gap_ms']['median'])} ms; orientation-unknown 0/16 | Capture clock and calibration unverified |",
  '',
  '## Blocking scientific qualifications',
  ''
 ]

 for key in result['qualification_gates']:
  s.append('- **'+key.replace('_',' ')+': NOT QUALIFIED.**')

 s.extend(['','## Prioritized next implementation phases',''])

 for task in result['work_sequence']:
  s.append(f"- **{task['phase']}:** {task['task']}. **Acceptance evidence:** {task['expected_evidence']}.")

 s.extend([
  '',
  '## Safety and split restrictions',
  '',
  'The original 15 GB bag was not reopened in R39. TRAIN and calibration may support engineering and model selection; the original confirmation-test split must remain untouched. No real factors, health labels/model training, ATE/RPE scoring, or robot safety claims are authorized.',
  ''
 ])

 return '\n'.join(s)

def run(c,d,out,md):
 raw=inputs(c,d)
 metrics=evaluate(raw)

 gates={
  k:{
   'status':'NOT_QUALIFIED',
   'evidence':'No frozen physically validated calibration/reference receipt'
  }
  for k in (
   'physical_capture_clock',
   'camera_intrinsics_distortion',
   'camera_metric_scale',
   'lidar_registration_accuracy_and_covariance',
   'imu_bias_noise_gravity',
   'cross_sensor_extrinsics',
   'independent_SE3_reference',
   'validation_calibrated_factor_covariance',
   'health_label_supervision'
  )
 }

 result={
  'schema':'TRUST_ROBOT_R39_TRAIN_RECORDED_SENSOR_QUALIFICATION_PLAN_V1',
  'trajectory_id':'room_02',
  'split':'train',
  'github_baseline':BASE,
  'authenticated_bag_sha256':BAG,
  'source_sha256':{k:v[1] for k,v in PINS.items()},
  'decision':'DIAGNOSTICS_VERIFIED_QUALIFIED_REAL_FACTORS_BLOCKED',
  'metrics':metrics,
  'qualification_gates':gates,
  'next_phase':'R40_CALIBRATION_CLOCK_REFERENCE_ASSET_INVENTORY',
  'work_sequence':[
   {'phase':n,'task':task,'expected_evidence':ev}
   for n,task,ev in STEPS
  ],
  'scientific_pose_factors':0,
  'health_labels':0,
  'ate_rpe_scores':0,
  **{k:False for k in GATES}
 }

 safety(result)

 with out.open('x') as handle:
  json.dump(result,handle,indent=2,sort_keys=True,allow_nan=False)
  handle.write('\n')

 with md.open('x') as handle:
  handle.write(markdown(result))

 print('R39_LIDAR_MAX_ROUNDTRIP_TRANSLATION_M=%.6f'%metrics['lidar']['inverse_roundtrip_translation_m']['max'])
 print('R39_LIDAR_MAX_ROUNDTRIP_ROTATION_DEG=%.6f'%metrics['lidar']['inverse_roundtrip_rotation_deg']['max'])
 print('R39_CAMERA_MAX_PAIR_PIXEL_DISPLACEMENT=%.6f'%metrics['camera']['median_pixel_displacement_px']['max'])
 print('R39_IMU_NATIVE_FRAMES_AND_ORIENTATION_SENTINELS=KEPT_SEPARATE')
 print('R39_UNQUALIFIED_GATES=%d'%len(gates))
 print('R39_ACTIONABLE_FUTURE_PHASES=%d'%len(STEPS))

if __name__=='__main__':
 run(*(pathlib.Path(p) for p in sys.argv[1:5]))
