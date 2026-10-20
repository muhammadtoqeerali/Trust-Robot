"""R43: source-acquisition contract, not calibration execution or scoring."""
import hashlib,json,pathlib,subprocess,sys

BASE='df78336320b3b026e448a09d39dfc571f922ae00'
BAG='ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1'
REF='79d2c6d9132ce3cf87bb87445729302cd73709a59344a3dfacc5d7788937589d'
SPLIT='017a388ef1ce4ad30812669632a022ca37c084871bc949693fd9c0541014238f'
MANIFESTS=(
 'm2dgr_trajectory_manifest_v1_split_freeze_v1.json',
 'm2dgr_calibration_evidence_v1.json',
 'm2dgr_reference_physical_semantics_evidence_v1.json',
 'm2dgr_gt_recording_stream_provenance_evidence_v1.json',
 'm2dgr_reference_quality_index_v1.json',
 'm2dgr_platform_geometry_evidence_v1.json',
 'm2dgr_synchronization_evidence_v1.json',
 'm2dgr_camera_imu_synchronization_evidence_v1.json',
 'm2dgr_lidar_imu_synchronization_evidence_v1.json',
 'm2dgr_reference_temporal_association_evidence_v1.json',
)
# Each acceptance item requires actual, independently auditable physical evidence.
# A software contract, calibration filename, or platform drawing cannot fill these fields.
SPEC={
 'camera_intrinsics_physically_verified':('camera_calibration','camera_model','image_size_px','K_3x3','distortion_model_and_coefficients','capture_resolution_receipt','independent_reprojection_check'),
 'camera_lidar_extrinsics_physically_verified':('cross_sensor_geometry','source_frame','target_frame','T_target_source_SE3','translation_units_m','calibration_method','independent_transform_residuals'),
 'camera_imu_extrinsics_physically_verified':('cross_sensor_geometry','source_frame','target_frame','T_target_source_SE3','translation_units_m','rotation_direction','independent_validation'),
 'mocap_body_to_lidar_physically_verified':('tracked_body_origin','tracked_markers_and_body_frame','target_lidar_frame','T_lidar_mocap_body_SE3','translation_units_m','author_or_measurement_receipt','independent_geometry_check'),
 'reference_capture_clock_physically_verified':('reference_timing','reference_event_definition','timestamp_epoch_and_unit','export_timebase_mapping','offset_sign_convention','per_sequence_or_global_scope','independent_clock_check'),
 'cross_sensor_synchronization_physically_verified':('sensor_clock_mapping','all_sensor_clock_domains','physical_event_definitions','offset_and_drift_models','offset_sign_convention','lidar_scan_effective_time','independent_validation'),
 'raw_reference_available_locally':('raw_reference_receipt','room_02_source_uri','license_and_provenance','raw_bytes_sha256','file_format_and_timestamp_units','90_invalid_rotation_handling','independent_content_check'),
 'metric_visual_pose_authorized':('dependent_decision','qualified_camera_intrinsics','qualified_camera_extrinsics','independent_metric_scale','nondegenerate_correspondences','independent_pose_reference','uncertainty_check'),
 'real_sensor_factors_authorized':('dependent_decision','qualified_native_sensor_models','qualified_physical_clock','qualified_noise_covariances','independent_consistency_tests','train_validation_predeclared_gates','explicit_safety_approval'),
 'health_training_authorized':('dependent_decision','supervised_health_labels_provenance','TRAIN_only_fit','validation_only_model_selection','label_leakage_audit','heldout_isolation_test','explicit_scientific_approval'),
 'm2dgr_ate_rpe_authorized':('dependent_decision','qualified_SE3_reference','mocap_to_estimator_transform','physical_time_association','invalid_rotation_mask','predeclared_metric_tolerance','heldout_sealed_scoring_plan'),
}
CLOSED=('physical_calibration_admitted','reference_scoring_authorized','real_sensor_factors_authorized','health_training_authorized','m2dgr_ate_rpe_authorized','confirmation_test_accessed','raw_bag_opened','github_modified')
ZERO=('qualified_pose_factors','health_labels','ate_rpe_scores','external_sources_acquired')

def need(ok,reason):
 if not ok:raise ValueError('R43_DENIED:'+reason)
def sha(data):return hashlib.sha256(data).hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_text())

def policy(result,receipts):
 need(result.get('schema')=='TRUST_ROBOT_R43_SOURCE_ACQUISITION_GATE_PROTOCOL_V1' and result.get('trajectory_id')=='room_02' and result.get('split')=='train' and result.get('github_baseline')==BASE and result.get('bag_sha256')==BAG,'SOURCE_SCOPE')
 need(result.get('raw_reference_provenance_sha256')==REF and result.get('split_manifest_sha256')==SPLIT,'FROZEN_RECEIPTS')
 need(set(result.get('frozen_manifest_sha256',{}))==set(MANIFESTS) and len(result['frozen_manifest_sha256'])==10,'MANIFEST_INVENTORY')
 need(result.get('unresolved_gate_count')==11 and set(result.get('requests',{}))==set(SPEC),'GATE_SET')
 need(all(result.get(k) is False for k in CLOSED),'NO_ACCESS_OR_ADMISSION')
 need(all(type(result.get(k)) is int and result[k]==0 for k in ZERO),'NO_SCIENCE_COUNTS')
 need(result.get('next_phase')=='R44_GUARDED_R39_R43_CHECKPOINT','NEXT')
 need(result.get('source_acquisition_status')=='NOT_ACQUIRED','NO_FAKE_SOURCE')
 need(receipts.get('schema')=='TRUST_ROBOT_R43_EMPTY_EVIDENCE_RECEIPTS_V1' and receipts.get('intended_split')=='train' and set(receipts.get('gate_receipts',{}))==set(SPEC),'RECEIPTS')
 for key,spec in SPEC.items():
  q=result['requests'][key]
  need(q.get('status')=='NOT_QUALIFIED' and q.get('required_evidence_fields')==list(spec[1:]) and q.get('source_class')==spec[0] and q.get('physical_validation_completed') is False,'REQUEST:'+key)
  evidence=receipts['gate_receipts'][key]
  need(evidence.get('status')=='NO_SOURCE_RECEIVED' and evidence.get('source_uri') is None and evidence.get('source_sha256') is None and evidence.get('independent_validation_sha256') is None and evidence.get('physical_qualification_authorized') is False and set(evidence.get('required_fields',{}))==set(spec[1:]) and all(value is None for value in evidence['required_fields'].values()),'EMPTY_RECEIPT:'+key)
 need(result.get('existing_d435i_relative_rotation_content_support') is True and result.get('full_extrinsic_from_partial_rotation') is False,'PARTIAL_ROTATION')
 need(result.get('room_02_reference_invalid_rotations')==90 and result.get('reference_to_lidar_transform_known') is False,'MOCAP_SCOPE')

def build(repo,r39p,r40p,r41p,r42p,v42p,out,template,plan):
 previous={k:read(p) for k,p in (('r39',r39p),('r40',r40p),('r41',r41p),('r42',r42p),('r42_independent',v42p))}
 need(previous['r39']['decision']=='DIAGNOSTICS_VERIFIED_QUALIFIED_REAL_FACTORS_BLOCKED','R39')
 need(previous['r40']['raw_bag_opened'] is False and previous['r41']['raw_bag_opened'] is False,'R40_R41')
 need(previous['r41']['matching_frozen_reference_payload_count']==0 and len(previous['r41']['room_02_reference_file_candidates'])==0,'REFERENCE_ABSENCE')
 need(previous['r42']['schema']=='TRUST_ROBOT_R42_TRAIN_ROS_CONNECTION_CALIBRATION_GAP_V1' and previous['r42']['connection_count']==15 and previous['r42']['sensor_messages_decoded']==0,'R42_SOURCE')
 need(previous['r42']['camera_info_topic_count']==previous['r42']['tf_topic_count']==previous['r42']['mocap_or_pose_reference_topic_count']==0,'R42_TOPICS')
 need(previous['r42']['source_sha256']['r41']==sha(r41p.read_bytes()),'R41_R42_CHAIN')
 need(previous['r42_independent']['source_report_sha256']==sha(r42p.read_bytes()),'R42_INDEPENDENT')
 need(set(previous['r42']['unresolved_requirements'])==set(SPEC) and all(v=='NOT_PHYSICALLY_QUALIFIED' for v in previous['r42']['unresolved_requirements'].values()),'R42_11_GATES')
 files={};snap={}
 for filename in MANIFESTS:
  p=repo/'manifests'/filename
  need(p.is_file() and not p.is_symlink() and 0<p.stat().st_size<1500000,'SOURCE_FILE:'+filename)
  raw=p.read_bytes()
  committed=subprocess.check_output(['git','-C',str(repo),'show',BASE+':manifests/'+filename])
  need(raw==committed,'COMMIT_MANIFEST:'+filename)
  files[filename]=sha(raw);snap[filename]=json.loads(raw)
 need(files[MANIFESTS[0]]==SPLIT,'FROZEN_SPLIT')
 room=[row for row in snap[MANIFESTS[0]]['records'] if row['trajectory_id']=='room_02']
 need(len(room)==1 and room[0]['split']=='train','ROOM_ONLY')
 need(sum(x['split']=='confirmation_test' for x in snap[MANIFESTS[0]]['records'])==7,'HOLDOUT_COHORT')
 calib=snap['m2dgr_calibration_evidence_v1.json']['interpretation']
 phys=snap['m2dgr_reference_physical_semantics_evidence_v1.json']['interpretation']
 gt=snap['m2dgr_gt_recording_stream_provenance_evidence_v1.json']['interpretation']
 need(calib['d435i_imu_relative_rotation_has_independent_released_sensor_content_support'] is True and calib['d435i_imu_relative_rotation_support_is_full_extrinsic_verification'] is False and calib['camera_intrinsics_verified'] is False and calib['dataset_calibration_verified'] is False,'CALIBRATION_GATES')
 need(phys['mocap_reference_body_origin_verified'] is False and phys['mocap_to_lidar_transform_verified'] is False and phys['reference_timestamp_physical_measurement_event_verified'] is False,'REFERENCE_SEMANTICS')
 need(gt['timestamp_calibration_value_verified'] is False and gt['reference_timestamp_timebase_export_semantics_verified'] is False,'REFERENCE_TIMING')
 q=[a for a in snap['m2dgr_reference_quality_index_v1.json']['artifacts'] if a['trajectory_id']=='room_02']
 need(len(q)==1 and q[0]['reference_source']=='mocap' and q[0]['raw_reference_sha256']==REF and q[0]['rotation_invalid_count']==90,'MOCAP_QUALITY')
 requests={key:{'status':'NOT_QUALIFIED','source_class':spec[0],'required_evidence_fields':list(spec[1:]),'physical_validation_completed':False} for key,spec in SPEC.items()}
 receipt={'schema':'TRUST_ROBOT_R43_EMPTY_EVIDENCE_RECEIPTS_V1','intended_split':'train','source_data_present':False,'gate_receipts':{key:{'status':'NO_SOURCE_RECEIVED','source_uri':None,'source_sha256':None,'independent_validation_sha256':None,'physical_qualification_authorized':False,'required_fields':{f:None for f in spec[1:]}} for key,spec in SPEC.items()}}
 result={'schema':'TRUST_ROBOT_R43_SOURCE_ACQUISITION_GATE_PROTOCOL_V1','trajectory_id':'room_02','split':'train','github_baseline':BASE,'bag_sha256':BAG,'raw_reference_provenance_sha256':REF,'split_manifest_sha256':SPLIT,'frozen_manifest_sha256':files,'upstream_report_sha256':{k:sha(p.read_bytes()) for k,p in (('r39',r39p),('r40',r40p),('r41',r41p),('r42',r42p),('r42_independent',v42p))},'requests':requests,'unresolved_gate_count':len(requests),'room_02_reference_invalid_rotations':90,'existing_d435i_relative_rotation_content_support':True,'full_extrinsic_from_partial_rotation':False,'reference_to_lidar_transform_known':False,'source_acquisition_status':'NOT_ACQUIRED','scientific_interpretation':'author_provenance_and_partial_sensor_content_support_do_not_complete_physical_calibration','next_phase':'R44_GUARDED_R39_R43_CHECKPOINT',**{k:False for k in CLOSED},**{k:0 for k in ZERO}}
 policy(result,receipt)
 with out.open('x') as h:json.dump(result,h,indent=2,sort_keys=True,allow_nan=False);h.write('\n')
 with template.open('x') as h:json.dump(receipt,h,indent=2,sort_keys=True,allow_nan=False);h.write('\n')
 lines=['# R43 — Physical calibration and mocap source-acquisition protocol','','**Status: no new physical evidence acquired; all 11 gates remain NOT QUALIFIED.**','','The frozen room_02 mocap reference receipt has SHA256 `'+REF+'`, with 90 invalid rotation records. The locally bounded R41 search found no matching room_02 reference file. R42 inspected 15 ROS1 connection headers and found no CameraInfo, TF, or mocap reference topics.','','Existing published/released D435i IMU relative-rotation content support is retained, but **does not** establish a full 6DoF extrinsic or physical timing.','','## Evidence requirements and future acceptance','']
 for key,spec in SPEC.items():
  lines.append('- **'+key+' — NOT QUALIFIED.** Required: '+', '.join(spec[1:])+'.')
 lines+=['','## Receipt intake and split discipline','','Use `r43_unfilled_source_receipts_v1.json` as an **unfilled schema template only**. An independent future qualification phase must bind any legitimately received source to a SHA256, actual provenance and physical validation; do not change any status field in this frozen report.','', 'Collect physical metadata from the dataset author, device manufacturer, original calibration runs, or independently measured equipment. Require native coordinate-frame definitions, transform direction, metres, sensor timebase and sign conventions, per-sequence applicability, and withheld independent checks.','', 'Do not fit reference-to-sensor transforms, time offsets, thresholds or noise models on confirmation_test; use TRAIN for development, validation_calibration for predeclared decisions, and retain confirmation_test sealed until scientific gates permit scoring.','','## Next','', 'R44: SHA-pinned audit/archive of R39–R43 with standalone independent verifier and guarded GitHub push. No sensor factors, health labels or ATE/RPE scoring.','']
 with plan.open('x') as h:h.write('\n'.join(lines))
 print('R43_FROZEN_REPOSITORY_MANIFESTS=10_GIT_VERIFIED')
 print('R43_R42_UNRESOLVED_CALIBRATION_AND_ADMISSION_GATES=11')
 print('R43_UNFILLED_SOURCE_RECEIPTS=11_EXPLICITLY_NULL')
 print('R43_MOCAP_REFERENCE_INVALID_ROTATION_RECORDS=90')
 print('R43_NEW_PHYSICAL_SOURCES_ACQUIRED=0')
 print('R43_REAL_SENSOR_FACTORS_HEALTH_SCORING=DENIED')

if __name__=='__main__':build(*(pathlib.Path(p) for p in sys.argv[1:10]))
