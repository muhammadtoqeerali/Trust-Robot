"""R25: fail-closed review of frozen R22-R24 recorded TRAIN diagnostics.
Never opens the rosbag, scores ground truth, or emits localization factors.
"""
import hashlib, json, math, pathlib, sys, xml.etree.ElementTree as ET

TOPICS=('/camera/color/image_raw/compressed','/camera/imu','/handsfree/imu','/velodyne_points')
BASE='76685f1a6a97fb8e0750224bb927f1b094e63203'
BAG='ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1'

def need(cond,label):
    if not cond:raise ValueError('R25_REVIEW_DENIED:'+label)
def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(pathlib.Path(path).read_text(encoding='utf-8'))
def gates(record,keys):
    for key in keys:need(record.get(key) is False,'GATE:'+key)
def zero(record,keys):
    for key in keys:need(type(record.get(key)) is int and record[key]==0,'ZERO:'+key)

def review(r17,r18,r19,r20,r22,v22,r23,v23,r24,v24):
    need(r17['schema']=='TRUST_ROBOT_R17_ROS1_INDEX_READONLY_V1'
         and r18['schema']=='TRUST_ROBOT_R18_BOUNDED_ROS1_RECORDED_MESSAGES_V1'
         and r19['schema']=='TRUST_ROBOT_R19_RECORDED_FRONTEND_PROVENANCE_V1'
         and r20['schema']=='TRUST_ROBOT_R20_RECORDER_BOUNDARY_REVIEW_V1','UPSTREAM_SCHEMA')
    need(r22['schema']=='TRUST_ROBOT_R22_TRAIN_ONLY_SIGNAL_DIAGNOSTICS_V1'
         and v22['schema']=='TRUST_ROBOT_R22_INDEPENDENT_CONTENT_VALIDATION_V1'
         and r23['schema']=='TRUST_ROBOT_R23_INDEX_STRATIFIED_TRAIN_DIAGNOSTICS_V1'
         and v23['schema']=='TRUST_ROBOT_R23_INDEPENDENT_STRATIFIED_CONTENT_VERIFY_V1'
         and r24['schema']=='TRUST_ROBOT_R24_TRAIN_RECORDED_DIAGNOSTIC_STRESS_V1'
         and v24['schema']=='TRUST_ROBOT_R24_INDEPENDENT_DIAGNOSTIC_STRESS_CHECK_V1','PHASE_SCHEMA')
    need(all(x.get('trajectory_id')=='room_02' for x in (r17,r18,r19,r20,r22,r23,r24)),'TRAJECTORY')
    need(all(x.get('split')=='train' for x in (r18,r19,r20,r22,r23,r24)),'TRAIN_ONLY')
    need(r17['file_sha256']==r18['recording_sha256']==r19['bag_sha256']==
         r20['authenticated_bag_sha256']==r22['bag_sha256']==r23['bag_sha256']==r24['bag_sha256']==BAG,'BAG_CHAIN')
    need(r22['github_baseline']==r23['git_baseline']==BASE and
         r20['parent_git_commit']=='0dddf4eda57cd629db4c5ee63cdbf645b17fb31d','GIT_SCOPE')
    gates(r20,('estimator_scoring_authorized','real_sensor_factor_execution_authorized',
               'health_model_training_authorized','ground_truth_scored',
               'cross_modal_sync_verified','full_sensor_extrinsics_verified'))
    need(r20['readiness_decision']=='RECORDED_OBSERVATION_PROVENANCE_ONLY'
         and r20['regression_tests_passed']==197,'R20_BASELINE')
    need(r22['sample_count']==8 and r22['sensor_stream_count']==4 and
         len(r22['signals'])==4 and set(r22['signals'])==set(TOPICS),'R22_COUNTS')
    need(v22['verification']=='PASS' and v22['real_message_samples_recomputed']==8 and
         v22['four_modal_streams_rechecked']==4 and v22['train_only'] is True,'R22_INDEPENDENT')
    need(r23['selected_per_topic']==8 and r23['sampled_message_count']==32 and
         r23['required_topics']==4 and r23['inspected_unique_chunk_count']==30 and
         set(r23['per_topic'])==set(TOPICS),'R23_COUNTS')
    need(v23['verification']=='PASS' and v23['independently_relocated_serialized_messages']==32 and
         v23['numeric_diagnostics_recomputed']==32 and
         v23['sampling_schedule_rebuilt_from_real_bag_index'] is True,'R23_INDEPENDENT')
    need(r24['original_selected_messages']==32 and r24['original_chunks_read']==30 and
         r24['message_integrity_and_provenance_challenges_rejected']==128 and
         r24['semantic_payload_challenges_rejected']==8 and
         r24['lidar_nonfinite_descriptive_only_cases']==2 and
         r24['lidar_nonfinite_frontend_rejections']==2,'R24_COUNTS')
    need(v24['verification']=='PASS' and v24['recorded_messages_independently_relocated']==32 and
         v24['integrity_mutations_independently_recounted']==128 and
         v24['semantic_challenge_outcome_types_checked']==8,'R24_INDEPENDENT')
    need(r23['indexed_required_stream_messages']==26149 and
         r17['chunk_count']==5182 and r17['connection_count']==15 and
         sum(r17['required_stream_counts'].values())==26149,'R17_COUNTS')
    need(r24['scope']=='IN_MEMORY_FAIL_CLOSED_DIAGNOSTIC_CHALLENGES_ONLY' and
         r24['changes_applied_to_memory_copies_only'] is True,'MEMORY_ONLY')
    need(r22['scope']=='DESCRIPTIVE_TWO_SAMPLE_TRAIN_ONLY_CANDIDATES_NOT_SELECTED_FEATURES'
         and r23['diagnostic_scope']=='BOUNDED_DESCRIPTIVE_COVERAGE_ONLY_NOT_A_HEALTH_STABILITY_OR_ACCURACY_CLAIM','DESCRIPTIVE')
    for topic in TOPICS:
        need(len(r22['signals'][topic])==2,'R22_EACH_TOPIC')
        row=r23['per_topic'][topic]
        need(row['selected_message_count']==8 and len(row['observations'])==8 and
             row['index_record_count']==r17['required_stream_counts'][topic] and
             row['qualitative_stability_inference_authorized'] is False,'R23_EACH_TOPIC')
        need(math.isclose(row['selected_message_percent_of_full_topic'],800.0/r17['required_stream_counts'][topic],rel_tol=1e-12),'COVERAGE')
        older=r22['signals'][topic][0]['source']; newer=row['observations'][0]['source']
        for k in ('chunk_offset','connection_id','bag_record_time_ns','serialized_message_sha256','serialized_message_bytes'):
            need(older[k]==newer[k],'R22_R23_FIRST_MESSAGE:'+k)
    gates(r22,('health_features_frozen','cross_modal_alignment_performed','physical_time_semantics_verified',
               'sensor_extrinsics_verified','independent_ground_truth_scored','real_sensor_factor_execution_authorized',
               'raw_recording_modified','github_modified','real_lidar_scan_registration_executed',
               'camera_odometry_executed','imu_preintegration_executed'))
    gates(r23,('health_features_selected','statistical_stability_established','random_sampling_claimed',
               'cross_modal_pairing_performed','physical_capture_sync_verified','extrinsics_verified',
               'reference_ground_truth_scored','real_sensor_factor_execution_authorized','raw_bag_modified','github_modified'))
    gates(r24,('recorded_source_files_written','original_recording_modified','health_thresholds_selected',
               'health_features_frozen','statistical_stability_established','cross_modal_alignment_performed',
               'physical_synchronization_verified','full_extrinsics_verified','ground_truth_scored',
               'camera_odometry_executed','lidar_registration_executed','imu_preintegration_executed',
               'real_sensor_factor_execution_authorized','git_modified'))
    zero(r22,('new_sensor_measurements','health_labels_generated','real_pose_factors_generated'))
    zero(r23,('health_labels_created','real_pose_factors_generated'))
    zero(r24,('health_labels','real_pose_factors_generated'))
    zero(r20,('new_real_pose_factors','new_sensor_acquisitions','health_labels'))
    need(v22['cross_modal_association_performed'] is False and v22['pose_factors_admitted']==0
         and v23['cross_modal_time_association'] is False and v23['pose_factors_admitted']==0
         and v24['cross_modal_alignment'] is False and v24['real_pose_factors']==0,'VALIDATOR_GATES')
    return {'topics':list(TOPICS),'indexed_required_messages':26149,'source_chunks':5182,
            'r22_samples':8,'r23_samples':32,'r23_distinct_chunks':30,
            'integrity_mutations_rejected':128,'semantic_mutations_rejected':8,
            'nonfinite_lidar_frontend_denials':2,'recorded_pose_factors':0,'health_labels':0}

def junit(path):
    root=ET.parse(path).getroot()
    cases=list(root.iter('testcase'))
    need(len(cases)==197 and len({(x.get('classname'),x.get('name')) for x in cases})==197,'JUNIT_197_UNIQUE')
    need(not any(child.tag in ('failure','error','skipped') for c in cases for child in c),'JUNIT_FAILURE')
    return 197

def run(repo,experiments,junit_path,report):
    arc=repo/'experiments/trust_robot_r17_r20_recorded_input_checkpoint_v1'
    src={
      'r17':arc/'r17/r17_recorded_index.json','r18':arc/'r18/r18_bounded_recorded_samples.json',
      'r19':arc/'r19/r19_recorded_frontend_contract_v1.json','r20':arc/'r20/r20_recorder_readiness_review_v1.json',
      'r22':experiments/'trust_robot_r22_train_content_result_v1/r22_recorded_content_diagnostics_v1.json',
      'v22':experiments/'trust_robot_r22_train_content_result_v1/r22_independent_validation_v1.json',
      'r23':experiments/'trust_robot_r23_coverage_result_v1/r23_train_coverage_diagnostics_v1.json',
      'v23':experiments/'trust_robot_r23_coverage_result_v1/r23_independent_validation_v1.json',
      'r24':experiments/'trust_robot_r24_diagnostic_stress_result_v1/r24_recorded_diagnostic_stress_v1.json',
      'v24':experiments/'trust_robot_r24_diagnostic_stress_result_v1/r24_independent_validation_v1.json',
    }
    docs={k:load(p) for k,p in src.items()}
    counts=review(**docs)
    need(docs['r22']['frozen_source_report_sha256']=={k:sha(src[k]) for k in ('r17','r18','r19','r20')},'R22_SOURCE_CHAIN')
    need(docs['r23']['source_hashes']=={'r17_report_sha256':sha(src['r17']),
          'r18_report_sha256':sha(src['r18']),'r22_report_sha256':sha(src['r22'])},'R23_SOURCE_CHAIN')
    need(docs['r24']['r23_report_sha256']==sha(src['r23']),'R24_SOURCE_CHAIN')
    need(docs['v22']['source_report_sha256']==sha(src['r22']) and
         docs['v23']['report_sha256']==sha(src['r23']) and
         docs['v24']['report_sha256']==sha(src['r24']),'INDEPENDENT_REPORT_LINK')
    count=junit(junit_path)
    output={'schema':'TRUST_ROBOT_R25_RECORDED_FRONTEND_CHECKPOINT_READINESS_V1',
      'trajectory_id':'room_02','split':'train','parent_git_commit':BASE,
      'authenticated_bag_sha256':BAG,'source_report_sha256':{k:sha(p) for k,p in src.items()},
      'r21_checkpoint_manifest_sha256':sha(arc/'checkpoint_manifest_v1.json'),
      'counts':counts,'regression_junit_sha256':sha(junit_path),
      'targeted_frontend_regressions_passed':count,
      'readiness_decision':'READY_FOR_SHA_PINNED_R22_R25_NONFACTOR_GIT_ARCHIVAL',
      'descriptive_sample_coverage_not_statistically_qualified':True,
      'recorded_data_source_mutated':False,'raw_sensor_payload_embedded':False,
      'physical_capture_time_verified':False,'cross_modal_sync_verified':False,
      'sensor_extrinsics_verified':False,'independent_reference_qualified':False,
      'health_model_training_authorized':False,'real_sensor_factor_execution_authorized':False,
      'm2dgr_scoring_authorized':False,'live_simulator_launch_authorized':False,
      'scientific_pose_factors':0,'health_labels':0,'github_modified':False}
    with report.open('x',encoding='utf-8') as f:
        json.dump(output,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    print('R25_CROSS_PHASE_REPORT_LINKS=PASS')
    print('R25_RECORDED_TRAIN_SAMPLES=8_PLUS_32_VERIFIED')
    print('R25_SCIENTIFIC_GATE_INVARIANTS=PASS')
    print('R25_TARGETED_FRONTEND_JUNIT=197_VERIFIED')
    print('R25_ARCHIVAL_READINESS=NONFACTOR_ONLY')

if __name__=='__main__':run(*map(pathlib.Path,sys.argv[1:5]))
