"""TRAIN-only clock and reference physical source-intake boundary. Never qualify real pose."""
import hashlib,json,pathlib,sys
BASE='58e23861811e51c5d00f00f5d22e5cb561c4b43a'
BAG='ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1'
SCHEMA='TRUST_ROBOT_R53_TRAIN_TIMING_AND_REFERENCE_SOURCE_ADMISSION_BOUNDARY_V1'
TOPICS=('/camera/color/image_raw/compressed','/camera/imu','/handsfree/imu','/velodyne_points')
FRAMES=('camera_color_optical_frame','camera_imu_optical_frame','base_link','velodyne')
KIND=('camera_color','camera_imu','handsfree_imu','velodyne_lidar','mocap_reference')
GENERAL=('source_document_uri','source_sha256','original_publisher_and_version',
 'device_model_and_serial_or_export_identifier','capture_event_definition',
 'header_stamp_timebase_and_epoch','clock_mapping_method_and_parameters',
 'clock_offset_and_drift_uncertainty','independent_validation_source_sha256',
 'room_02_applicability_evidence_sha256')
REFERENCE_EXTRA=('mocap_export_file_sha256','mocap_tracked_body_origin_definition',
 'mocap_to_lidar_transform_and_direction','reference_timestamp_export_semantics',
 'invalid_rotation_resolution_evidence_sha256')
GATES=('camera_imu_extrinsics_physically_verified','camera_intrinsics_physically_verified',
 'camera_lidar_extrinsics_physically_verified','cross_sensor_synchronization_physically_verified',
 'health_training_authorized','m2dgr_ate_rpe_authorized','metric_visual_pose_authorized',
 'mocap_body_to_lidar_physically_verified','raw_reference_available_locally',
 'real_sensor_factors_authorized','reference_capture_clock_physically_verified')
NO=('physical_clock_qualified','reference_timing_qualified','mocap_reference_qualified',
 'calibration_values_promoted','fixed_offset_selected','clock_drift_selected',
 'pose_factors_authorized','health_training_authorized','ate_rpe_authorized',
 'raw_bag_opened','confirmation_test_accessed','github_modified')
ZERO=('real_pose_factors','health_labels','ate_rpe_scores','new_external_source_files')

def need(ok,reason):
 if not ok:raise ValueError('R53_DENIED:'+reason)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def make_receipts():
 return {'schema':'TRUST_ROBOT_R53_UNFILLED_PHYSICAL_SOURCE_RECEIPTS_V1',
  'trajectory_id':'room_02','split':'train','source_data_present':False,
  'receipts':{kind:{'status':'NO_PHYSICAL_SOURCE_RECEIVED','fields':{
    key:None for key in (GENERAL+(REFERENCE_EXTRA if kind=='mocap_reference' else ()))},
    'independently_validated':False,'physical_measurement_qualified':False}
    for kind in KIND}}

def policy(report,receipts):
 need(report.get('schema')==SCHEMA and report.get('trajectory_id')=='room_02' and report.get('split')=='train' and report.get('github_parent')==BASE and report.get('bag_sha256')==BAG,'SCOPE')
 need(report.get('receipt_policy')=='SOURCE_INTAKE_ONLY_ZERO_PHYSICAL_ADMISSION' and report.get('admission_decision')=='DENIED_UNFILLED_SOURCE_RECEIPTS','DECISION')
 need(report.get('topic_frame_pairs')==[{'topic':a,'frame_id':b} for a,b in zip(TOPICS,FRAMES)],'STREAM_FRAMES')
 need(report.get('frozen_observed_timestamp_count')==48 and report.get('hypothetical_nearest_header_distances')==224 and report.get('hypothetical_record_header_residuals')==144,'PRIOR_SCENARIOS')
 need(report.get('camera_imu_negative_record_minus_header_count')==9 and report.get('reference_invalid_rotation_count')==90,'COUNTEREXAMPLES')
 need(report.get('physical_offset_seconds') is None and report.get('clock_drift_model') is None and report.get('temporal_association_tolerance_seconds') is None,'NO_SYNCHRONIZATION_FIT')
 need(report.get('source_status_by_gate')=={k:'NOT_QUALIFIED' for k in GATES},'ELEVEN_UNQUALIFIED')
 need(report.get('frozen_clock_domain_count')==4 and report.get('original_r43_receipts_unchanged') is True,'FROZEN_SOURCE_SCOPE')
 need(report.get('receipt_schema_sha256')==hashlib.sha256(json.dumps(receipts,sort_keys=True,indent=2,allow_nan=False).encode()+b'\n').hexdigest(),'RECEIPT_DIGEST')
 need(receipts==make_receipts(),'EMPTY_RECEIPTS')
 need(all(report.get(k) is False for k in NO),'NO_PHYSICAL_ADMISSION')
 need(all(type(report.get(k)) is int and report[k]==0 for k in ZERO),'NO_SCIENTIFIC_OUTPUT')
 need(report.get('next_phase')=='R54_AUTHOR_SOURCE_ACQUISITION_AND_PROVENANCE_REQUEST_PACKET','NEXT')

def build(repo,splitp,r43p,empty43p,r51p,v51p,r52p,v52p,reportp,receiptsp,planp):
 sources={'split':splitp,'r43_protocol':r43p,'r43_unfilled':empty43p,
 'r51_diagnostics':r51p,'r51_independent':v51p,'r52_sensitivity':r52p,'r52_independent':v52p}
 for k,p in sources.items():
  need(p.is_file() and not p.is_symlink() and 0<p.stat().st_size<4000000,'SOURCE:'+k)
 split,r43,empty43,r51,v51,r52,v52=map(read,sources.values())
 need(digest(splitp)=='017a388ef1ce4ad30812669632a022ca37c084871bc949693fd9c0541014238f','FROZEN_SPLIT_SHA')
 need(splitp.read_bytes()==__import__('subprocess').check_output(['git','-C',str(repo),'show',BASE+':manifests/m2dgr_trajectory_manifest_v1_split_freeze_v1.json']),'GIT_FROZEN_SPLIT')
 room=[x for x in split['records'] if x['trajectory_id']=='room_02']
 need(len(room)==1 and room[0]['split']=='train' and sum(x['split']=='confirmation_test' for x in split['records'])==7,'HOLDOUT_SEALED')
 streams=room[0]['streams']; sync=room[0]['synchronization']
 need(len(streams)==len(sync)==4 and [(s['stream_id'],s['frame_id']) for s in streams]==list(zip(TOPICS,FRAMES)),'STREAMS')
 need(all(s['verification_status']=='unverified' and s['fixed_offset_seconds'] is None and s['tolerance_seconds'] is None for s in sync),'CLOCKS_NOT_QUALIFIED')
 need(r43['unresolved_gate_count']==11 and r43['room_02_reference_invalid_rotations']==90 and r43['source_acquisition_status']=='NOT_ACQUIRED' and set(r43['requests'])==set(GATES),'R43_SOURCE_GATES')
 need(empty43['source_data_present'] is False and set(empty43['gate_receipts'])==set(GATES),'R43_UNFILLED_GATE_RECEIPTS')
 for v in empty43['gate_receipts'].values():
  need(v['status']=='NO_SOURCE_RECEIVED' and v['source_uri'] is None and v['source_sha256'] is None and v['physical_qualification_authorized'] is False and all(x is None for x in v['required_fields'].values()),'R43_EMPTY_GATE')
 need(r51['schema']=='TRUST_ROBOT_R51_TRAIN_RECORD_HEADER_CLOCK_EVIDENCE_V1' and r51['frozen_four_stream_clock_domains_unverified'] is True and r51['streams']['/camera/imu']['negative_residual_count']==9,'R51_CLOCK')
 need(v51['source_report_sha256']==digest(r51p) and v51['authentic_frozen_sample_timestamps_recomputed']==48,'R51_VALIDATION')
 need(r52['schema']=='TRUST_ROBOT_R52_TRAIN_CLOCK_PROVENANCE_SENSITIVITY_V1' and r52['authentic_frozen_messages']==48 and r52['samples_per_stream']==16,'R52_SCOPE')
 need(r52['physical_offset_selected'] is None and r52['clock_drift_model_selected'] is None and r52['association_tolerance_selected'] is None,'R52_NO_CLOCK_FIT')
 need(r52['source_sha256']['r51_report']==digest(r51p) and r52['source_sha256']['r51_independent']==digest(v51p),'R52_SOURCE_LINEAGE')
 need(v52['source_report_sha256']==digest(r52p) and v52['independent_sparse_shift_distances_recomputed']==224 and v52['independent_record_header_residuals_recomputed']==144 and v52['clock_offset_selected'] is False,'R52_VALIDATION')
 need(r52['reference_mocap_invalid_rotation_records']==90 and r52['reference_temporal_association_authorized'] is False and len(r52['scientific_gates'])==14 and all(v is False for v in r52['scientific_gates'].values()),'R52_SCIENCE')
 receipts=make_receipts()
 with receiptsp.open('x') as h:json.dump(receipts,h,sort_keys=True,indent=2,allow_nan=False);h.write('\n')
 report={'schema':SCHEMA,'trajectory_id':'room_02','split':'train','github_parent':BASE,'bag_sha256':BAG,
  'receipt_policy':'SOURCE_INTAKE_ONLY_ZERO_PHYSICAL_ADMISSION','admission_decision':'DENIED_UNFILLED_SOURCE_RECEIPTS',
  'source_sha256':{k:digest(v) for k,v in sources.items()},
  'receipt_schema_sha256':digest(receiptsp),'topic_frame_pairs':[{'topic':a,'frame_id':b} for a,b in zip(TOPICS,FRAMES)],
  'frozen_observed_timestamp_count':48,'hypothetical_nearest_header_distances':224,
  'hypothetical_record_header_residuals':144,'camera_imu_negative_record_minus_header_count':9,
  'reference_invalid_rotation_count':90,'physical_offset_seconds':None,'clock_drift_model':None,
  'temporal_association_tolerance_seconds':None,'source_status_by_gate':{k:'NOT_QUALIFIED' for k in GATES},
  'frozen_clock_domain_count':4,'original_r43_receipts_unchanged':True,
  **{k:False for k in NO},**{k:0 for k in ZERO},
  'next_phase':'R54_AUTHOR_SOURCE_ACQUISITION_AND_PROVENANCE_REQUEST_PACKET'}
 policy(report,receipts)
 with reportp.open('x') as h:json.dump(report,h,sort_keys=True,indent=2,allow_nan=False);h.write('\n')
 lines=['# R53: Author-source timing and reference intake boundary (TRAIN `room_02`)','','**No evidence has been received or physically qualified in R53.** All five new receipts and all eleven original R43 gate receipts remain empty.','','## Exact recorder streams needing source documentation','']
 for topic,frame in zip(TOPICS,FRAMES):lines.append(f'- `{topic}`: recorded `frame_id={frame}`; explain hardware event represented by its ROS header timestamp, timebase, device/firmware and mapping to other streams')
 lines.extend(['','## Questions and evidence to obtain from the M2DGR authors','','1. Which exact serial number, firmware, device calibration generation and recording configuration apply to `room_02`? Does the published calibration table cover those devices?','2. For each of the four sensor topics, which physical event is stamped (exposure start/mid/end, IMU sample, LiDAR scan start/end) and which clock/timebase generates the ROS header stamp?','3. Was any clock-to-host or intersensor offset/drift correction performed during recording/export? Request calibration method, values, intervals and uncertainty; identify any per-trajectory exceptions.','4. Which ground-truth/mocap export file corresponds to `room_02`? Request original source checksum, units, coordinate conventions, tracked body and physical tracking-marker origin.','5. How was reference time linked to the sensor clocks? Request export-stage conversion details and independent timing validation, not only a statement that timestamps were calibrated.','6. Supply a traceable rigid transform (direction and units) from mocap tracked body to LiDAR and a documented resolution of the 90 invalid rotation entries.','7. Supply independent verification data and uncertainty bounds before setting any association tolerance, fitting a real pose factor or scoring ATE/RPE.','','## Fail-closed admission sequence','','Verify author authenticity and SHA256 of each new file, independently validate frame and clock semantics and room_02 applicability, review uncertainty and dataset splits, and then propose gate-by-gate qualification **only in a new review phase**. Never edit the frozen R43 receipts or the 22/7/7 split manifest.','','Current camera color, camera IMU and HandsFree observations comprise only 48 sparse previously decoded records; the 224 nearest-header distances and 144 residuals are explicitly counterfactual diagnostics. Nine camera-IMU record-minus-header residuals are negative. They do not establish transport latency, fixed physical clock offset or calibration.','','No Git modification, original bag reopening, confirmation-test access, real pose factor, health training or scoring is authorized.','','## Next R54','','Prepare the source request packet and a bounded intake/response tracker; progress substantive measurement only after independently verifiable external evidence is received.',''])
 with planp.open('x') as h:h.write('\n'.join(lines))
 print('R53_FROZEN_TIMING_RECEIPTS=48_SOURCE_BOUND')
 print('R53_FROZEN_COUNTERFACTUAL_DISTANCES=224_AND_RESIDUALS=144')
 print('R53_SENSOR_CLOCK_DOMAINS=4_UNVERIFIED')
 print('R53_UNFILLED_PHYSICAL_SOURCE_RECEIPTS=5_EXPLICITLY_NULL')
 print('R53_ORIGINAL_R43_GATE_RECEIPTS=11_STILL_EMPTY')
 print('R53_REFERENCE_INVALID_ROTATIONS=90_UNRESOLVED')
 print('R53_REAL_SENSOR_FACTOR_AND_SCORING_ADMISSION=DENIED')
if __name__=='__main__':build(*(pathlib.Path(x) for x in sys.argv[1:12]))
