"""Independent R25 gate verifier; no import of R25 engine, no bag decoding."""
import hashlib,json,pathlib,sys,xml.etree.ElementTree as ET

def need(v,n):
    if not v:raise ValueError('R25_INDEPENDENT_DENIED:'+n)
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_text())
def run(repo,exp,report,validation,xml):
    archive=repo/'experiments/trust_robot_r17_r20_recorded_input_checkpoint_v1'
    p22=exp/'trust_robot_r22_train_content_result_v1/r22_recorded_content_diagnostics_v1.json'
    v22=exp/'trust_robot_r22_train_content_result_v1/r22_independent_validation_v1.json'
    p23=exp/'trust_robot_r23_coverage_result_v1/r23_train_coverage_diagnostics_v1.json'
    v23=exp/'trust_robot_r23_coverage_result_v1/r23_independent_validation_v1.json'
    p24=exp/'trust_robot_r24_diagnostic_stress_result_v1/r24_recorded_diagnostic_stress_v1.json'
    v24=exp/'trust_robot_r24_diagnostic_stress_result_v1/r24_independent_validation_v1.json'
    paths={'r17':archive/'r17/r17_recorded_index.json','r18':archive/'r18/r18_bounded_recorded_samples.json',
           'r19':archive/'r19/r19_recorded_frontend_contract_v1.json','r20':archive/'r20/r20_recorder_readiness_review_v1.json',
           'r22':p22,'v22':v22,'r23':p23,'v23':v23,'r24':p24,'v24':v24}
    data={k:read(p) for k,p in paths.items()}
    result=read(report)
    need(result['schema']=='TRUST_ROBOT_R25_RECORDED_FRONTEND_CHECKPOINT_READINESS_V1'
         and result['trajectory_id']=='room_02' and result['split']=='train','SCOPE')
    need(result['parent_git_commit']=='76685f1a6a97fb8e0750224bb927f1b094e63203','COMMIT_BASE')
    need(result['source_report_sha256']=={k:sha(p) for k,p in paths.items()},'TEN_BOUND_REPORT_HASHES')
    need(result['r21_checkpoint_manifest_sha256']==sha(archive/'checkpoint_manifest_v1.json'),'ARCHIVE_PIN')
    need(result['authenticated_bag_sha256']=='ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1','BAG_PIN')
    need(data['r24']['r23_report_sha256']==sha(p23) and data['v24']['report_sha256']==sha(p24) and
         data['v23']['report_sha256']==sha(p23) and data['v22']['source_report_sha256']==sha(p22),'CHAIN')
    names=('/camera/color/image_raw/compressed','/camera/imu','/handsfree/imu','/velodyne_points')
    counts=data['r17']['required_stream_counts']
    need(set(counts)==set(names) and sum(counts.values())==26149,'RECORDING_COUNTS')
    need(set(data['r23']['per_topic'])==set(names) and sum(len(data['r23']['per_topic'][n]['observations']) for n in names)==32,'SAMPLES')
    need(set(data['r22']['signals'])==set(names) and sum(len(data['r22']['signals'][n]) for n in names)==8,'R22_SAMPLES')
    for name in names:
        a=data['r22']['signals'][name][0]['source'];b=data['r23']['per_topic'][name]['observations'][0]['source']
        need(a['serialized_message_sha256']==b['serialized_message_sha256'] and a['chunk_offset']==b['chunk_offset'],'FIRST_MESSAGE')
    need(data['r24']['message_integrity_and_provenance_challenges_rejected']==128
         and data['r24']['semantic_payload_challenges_rejected']==8
         and data['r24']['lidar_nonfinite_frontend_rejections']==2,'CHALLENGES')
    need(data['v22']['verification']=='PASS' and data['v23']['verification']=='PASS' and data['v24']['verification']=='PASS','VALIDATION')
    cases=list(ET.parse(xml).getroot().iter('testcase'))
    need(len(cases)==197 and not any(ch.tag in ('failure','skipped','error') for c in cases for ch in c),'JUNIT')
    need(result['regression_junit_sha256']==sha(xml) and result['targeted_frontend_regressions_passed']==197,'JUNIT_HASH')
    need(result['counts']=={'topics':list(names),'indexed_required_messages':26149,'source_chunks':5182,
          'r22_samples':8,'r23_samples':32,'r23_distinct_chunks':30,'integrity_mutations_rejected':128,
          'semantic_mutations_rejected':8,'nonfinite_lidar_frontend_denials':2,'recorded_pose_factors':0,'health_labels':0},'COUNT_DIGEST')
    for key in ('recorded_data_source_mutated','raw_sensor_payload_embedded','physical_capture_time_verified',
                'cross_modal_sync_verified','sensor_extrinsics_verified','independent_reference_qualified',
                'health_model_training_authorized','real_sensor_factor_execution_authorized',
                'm2dgr_scoring_authorized','live_simulator_launch_authorized','github_modified'):
        need(result.get(key) is False,'SCIENCE_GATE_'+key)
    need(result['scientific_pose_factors']==0 and result['health_labels']==0 and
         result['descriptive_sample_coverage_not_statistically_qualified'] is True and
         result['readiness_decision']=='READY_FOR_SHA_PINNED_R22_R25_NONFACTOR_GIT_ARCHIVAL','DECISION')
    output={'schema':'TRUST_ROBOT_R25_INDEPENDENT_CHECKPOINT_READINESS_VERIFICATION_V1',
        'r25_report_sha256':sha(report),'r25_junit_sha256':sha(xml),
        'upstream_sha_bound_reports':10,'verified_recorded_message_scope':32,
        'regression_tests':197,'readiness':'NONFACTOR_ARCHIVE_ONLY',
        'recording_opened_by_r25_independent_verifier':False,
        'real_pose_factors_generated':0,'health_labels':0,'verification':'PASS'}
    with validation.open('x',encoding='utf-8') as f:json.dump(output,f,indent=2,sort_keys=True);f.write('\n')
    print('R25_INDEPENDENT_SOURCE_BINDINGS=10_VERIFIED')
    print('R25_INDEPENDENT_JUNIT=197_VERIFIED')
    print('R25_INDEPENDENT_SCIENTIFIC_BOUNDARY=PASS')
    print('R25_INDEPENDENT_VALIDATION=PASS')
if __name__=='__main__':run(*map(pathlib.Path,sys.argv[1:6]))
