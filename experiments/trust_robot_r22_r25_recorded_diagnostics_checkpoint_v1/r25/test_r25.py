"""R25 in-memory adversarial tests against baseline reports, no ROS bag access."""
import copy,json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).parent))
from r25_review import review
repo=pathlib.Path(sys.argv[1]);exp=pathlib.Path(sys.argv[2]);arc=repo/'experiments/trust_robot_r17_r20_recorded_input_checkpoint_v1'
paths={
 'r17':arc/'r17/r17_recorded_index.json','r18':arc/'r18/r18_bounded_recorded_samples.json',
 'r19':arc/'r19/r19_recorded_frontend_contract_v1.json',
 'r20':arc/'r20/r20_recorder_readiness_review_v1.json',
 'r22':exp/'trust_robot_r22_train_content_result_v1/r22_recorded_content_diagnostics_v1.json',
 'v22':exp/'trust_robot_r22_train_content_result_v1/r22_independent_validation_v1.json',
 'r23':exp/'trust_robot_r23_coverage_result_v1/r23_train_coverage_diagnostics_v1.json',
 'v23':exp/'trust_robot_r23_coverage_result_v1/r23_independent_validation_v1.json',
 'r24':exp/'trust_robot_r24_diagnostic_stress_result_v1/r24_recorded_diagnostic_stress_v1.json',
 'v24':exp/'trust_robot_r24_diagnostic_stress_result_v1/r24_independent_validation_v1.json'}
data={key:json.loads(path.read_text()) for key,path in paths.items()}
assert review(**data)['r23_samples']==32

def rejected(key,action):
    x=copy.deepcopy(data);action(x[key])
    try:review(**x)
    except (ValueError,KeyError,TypeError,AssertionError):return
    raise AssertionError('R25_FALSE_ADMISSION:'+key)

checks=[
 ('r17',lambda x:x.update(chunk_count=1)),
 ('r18',lambda x:x.update(recording_sha256='0'*64)),
 ('r19',lambda x:x.update(trajectory_id='room_01')),
 ('r20',lambda x:x.update(estimator_scoring_authorized=True)),
 ('r22',lambda x:x.update(split='confirmation_test')),
 ('r22',lambda x:x.update(health_features_frozen=True)),
 ('r22',lambda x:x.update(physical_time_semantics_verified=True)),
 ('r22',lambda x:x['signals']['/camera/imu'].pop()),
 ('v22',lambda x:x.update(verification='FAIL')),
 ('r23',lambda x:x.update(random_sampling_claimed=True)),
 ('r23',lambda x:x.update(real_pose_factors_generated=1)),
 ('r23',lambda x:x['per_topic']['/velodyne_points']['observations'][0]['source'].update(serialized_message_sha256='0'*64)),
 ('v23',lambda x:x.update(independently_relocated_serialized_messages=31)),
 ('r24',lambda x:x.update(health_labels=1)),
 ('r24',lambda x:x.update(physical_synchronization_verified=True)),
 ('r24',lambda x:x.update(message_integrity_and_provenance_challenges_rejected=127)),
 ('r24',lambda x:x.update(semantic_payload_challenges_rejected=7)),
 ('v24',lambda x:x.update(verification='FAIL')),
]
for key,mutator in checks:rejected(key,mutator)
print('R25_SOURCE_AST=PASS')
print('R25_NEGATIVE_PROMOTION_AND_COVERAGE_CONTROLS=18_REJECTED')
