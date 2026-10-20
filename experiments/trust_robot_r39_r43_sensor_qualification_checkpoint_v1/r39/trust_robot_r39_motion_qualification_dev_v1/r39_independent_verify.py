"""Read-only independent statistics and gate verification for R39."""
import hashlib,json,math,pathlib,statistics,sys

def sha(p):
 return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()

def need(ok,why):
 if not ok:
  raise ValueError('R39_INDEPENDENT_DENIED:'+why)

def get(p):
 return json.loads(pathlib.Path(p).read_text())

def close(x,y):
 return isinstance(x,(int,float)) and isinstance(y,(int,float)) and math.isclose(x,y,abs_tol=1e-11,rel_tol=1e-9)

def summary_match(stored,raw):
 expected=(min(raw),statistics.median(raw),max(raw))
 return all(close(stored[k],v) for k,v in zip(('min','median','max'),expected))

def verify(c,d,report_path,plan_path,out):
 r=get(report_path)

 need(
  r['schema']=='TRUST_ROBOT_R39_TRAIN_RECORDED_SENSOR_QUALIFICATION_PLAN_V1'
  and r['split']=='train'
  and r['decision']=='DIAGNOSTICS_VERIFIED_QUALIFIED_REAL_FACTORS_BLOCKED',
  'SCOPE'
 )

 paths={
  'lidar_pairs':c/'r29/r29_lidar_multipair_diagnostics_v1.json',
  'lidar_geometry':c/'r30/r30_geometry_confidence_limits_v1.json',
  'camera_pairs':d/'r33/trust_robot_r33_camera_multipair_result_v1/r33_camera_multipair_pixel_diagnostics_v1.json',
  'imu_intervals':d/'r34/trust_robot_r34_imu_short_interval_result_v1/r34_imu_short_interval_diagnostics_v1.json',
  'imu_variation':d/'r35/trust_robot_r35_imu_variation_frame_result_v1/r35_imu_variation_frame_v1.json',
  'gyro_windows':d/'r36/trust_robot_r36_gyro_windows_result_v1/r36_gyro_window_candidates_v1.json',
  'readiness':d/'r37/trust_robot_r37_checkpoint_readiness_result_v1/r37_readiness_report_v1.json'
 }

 need(set(paths)==set(r['source_sha256']),'PIN_INVENTORY')

 for key,p in paths.items():
  need(
   p.is_file() and not p.is_symlink()
   and sha(p)==r['source_sha256'][key],
   'SHA:'+key
  )

 lp,lg,cp,iv,gw=(
  get(paths[k])
  for k in ('lidar_pairs','lidar_geometry','camera_pairs','imu_variation','gyro_windows')
 )

 red=[
  float(
   x['registration']['identity_nearest_neighbor_rmse_m']
   -x['registration']['candidate_nearest_neighbor_rmse_m']
  )
  for x in lp['pairs']
 ]

 met=r['metrics']

 need(summary_match(met['lidar']['rmse_reduction_m'],red),'LIDAR_RMSE')
 need(summary_match(met['lidar']['inverse_roundtrip_translation_m'],[x['inverse_consistency']['roundtrip_translation_m'] for x in lg['pairs']]),'LIDAR_CLOSURE_M')
 need(summary_match(met['lidar']['inverse_roundtrip_rotation_deg'],[x['inverse_consistency']['roundtrip_rotation_deg'] for x in lg['pairs']]),'LIDAR_CLOSURE_DEG')
 need(summary_match(met['lidar']['minimum_eigenvalue_ratio_over_pairs'],[min(y['smallest_over_largest_eigenvalue'] for y in x['geometry']) for x in lg['pairs']]),'LIDAR_SPECTRUM')

 need(summary_match(met['camera']['median_pixel_displacement_px'],[x['pixel_motion']['median_displacement_px'] for x in cp['pairs']]),'CAMERA_PIXEL')
 need(summary_match(met['camera']['tracked_feature_fraction'],[x['pixel_motion']['forward_backward_consistent_count']/x['pixel_motion']['initial_corner_count'] for x in cp['pairs']]),'CAMERA_FEATURES')

 for topic in ('/camera/imu','/handsfree/imu'):
  observed=met['imu'][topic]
  actual=iv['streams'][topic]['intervals']
  windows=gw['streams'][topic]

  need(summary_match(observed['two_sample_header_gap_ms'],[x['observed_header_dt_ms_not_capture_clock_proof'] for x in actual]),'IMU_DT')
  need(summary_match(observed['three_sample_header_gap_ms'],[float(ns)/1e6 for w in windows for ns in w['gyro_numerics']['header_gaps_ns']]),'GYRO_DT')
  need(summary_match(observed['three_sample_numeric_rotation_angle_rad'],[w['gyro_numerics']['two_step_composed_rotation_angle_rad_diagnostic'] for w in windows]),'GYRO_SO3')
  need(observed['recorded_orientation_unknown_count_of_16']==iv['streams'][topic]['summary']['orientation_covariance_unknown_samples'],'ORIENTATION_SENTINELS')

 need(
  r['next_phase']=='R40_CALIBRATION_CLOCK_REFERENCE_ASSET_INVENTORY'
  and len(r['qualification_gates'])==9
  and all(v['status']=='NOT_QUALIFIED' for v in r['qualification_gates'].values()),
  'PLAN_GATES'
 )

 need(
  all(r.get(k) is False for k in (
   'physical_capture_time_verified',
   'real_pose_factors_authorized',
   'health_model_training_authorized',
   'm2dgr_scoring_authorized',
   'confirmation_test_accessed',
   'raw_bag_reopened',
   'github_modified'
  )),
  'SCIENTIFIC_GATES'
 )

 need(
  all(r[k]==0 and type(r[k]) is int for k in (
   'scientific_pose_factors','health_labels','ate_rpe_scores'
  )),
  'SCIENCE_COUNTS'
 )

 need(
  plan_path.is_file()
  and '# TRUST-ROBOT R39:' in plan_path.read_text()
  and 'R40' in plan_path.read_text()
  and 'NOT QUALIFIED' in plan_path.read_text(),
  'PLAN_DOC'
 )

 result={
  'schema':'TRUST_ROBOT_R39_INDEPENDENT_QUALIFICATION_PLAN_V1',
  'source_report_sha256':sha(report_path),
  'plan_markdown_sha256':sha(plan_path),
  'authenticated_frozen_reports_verified':len(paths),
  'independent_modal_metric_groups_checked':7,
  'scientific_factor_admission':False,
  'confirmation_test_accessed':False,
  'raw_recording_reopened':False
 }

 with out.open('x') as handle:
  json.dump(result,handle,sort_keys=True,indent=2,allow_nan=False)
  handle.write('\n')

 print('R39_INDEPENDENT_7_FROZEN_REPORTS=SHA_VERIFIED')
 print('R39_INDEPENDENT_LIDAR_CAMERA_IMU_METRICS=NUMERIC_MATCH')
 print('R39_INDEPENDENT_SCIENCE_GATES=BLOCKED')
 print('R39_INDEPENDENT_VALIDATION=PASS')

if __name__=='__main__':
 verify(*(pathlib.Path(x) for x in sys.argv[1:6]))
