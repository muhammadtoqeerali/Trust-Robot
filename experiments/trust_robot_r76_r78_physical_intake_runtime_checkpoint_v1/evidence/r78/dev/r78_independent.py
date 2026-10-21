"""Independent verification of the R78 serialized runtime-denial boundary."""
import hashlib,json,pathlib,sys
repo,d76,o76,d77,o77,out=map(pathlib.Path,sys.argv[1:])
p=out/'r78_runtime_boundary_decision_v1.json'
report=json.loads(p.read_text())
r77=json.loads((o77/'r77_intake_sensor_factor_boundary_v1.json').read_text())
r76=json.loads((o76/'r76_source_intake_contract_v1.json').read_text())
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert report['schema']=='TRUST_ROBOT_R78_RECORDED_FACTOR_RUNTIME_BOUNDARY_V1'
assert report['status']=='PASS_SOFTWARE_ONLY'
assert report['git_parent_commit']=='c1f59bb5e38bdfece14798031c0d911441b28de8'
assert report['trajectory_id']=='room_02' and report['split']=='train'
assert report['claims_evaluated']==sorted(r77['candidate_claim_names'])==sorted(r76['historical_r43_gates'])
assert report['candidate_shapes_tested']==report['apparently_filled_author_like_cases_denied']==11
assert report['historical_timing_receipts']==len(r76['historical_r53_receipts'])==5
assert report['existing_sensor_factor_gates_tested']==2
assert report['source_code_sha256']=={
 'r76_intake.py':sha(d76/'r76_intake.py'),
 'r77_bridge.py':sha(d77/'r77_bridge.py')}
assert report['prior_private_report_sha256']=={
 'r76_source_intake_contract_v1.json':sha(o76/'r76_source_intake_contract_v1.json'),
 'r76_independent_validation_v1.json':sha(o76/'r76_independent_validation_v1.json'),
 'r77_intake_sensor_factor_boundary_v1.json':sha(o77/'r77_intake_sensor_factor_boundary_v1.json'),
 'r77_independent_validation_v1.json':sha(o77/'r77_independent_validation_v1.json'),
}
assert report['scientific_gates_closed']==11
assert report['physically_qualified_sources']==report['runtime_authorizations']==0
for key in ('raw_gt_or_rosbag_opened','confirmation_test_accessed','real_pose_factors_authorized','health_training_authorized','ate_rpe_authorized','git_modified'):
 assert report[key] is False,key
for phrase in ('/home/kios/','/mnt/hdd16T/','"evidence_fields"','"source_reference"','"source_sha256"'):
 assert phrase not in p.read_text(),phrase
receipt={
 'schema':'TRUST_ROBOT_R78_INDEPENDENT_RUNTIME_BOUNDARY_VALIDATION_V1',
 'status':'PASS','primary_sha256':sha(p),
 'r76_r77_source_lineage_verified':True,
 'physical_qualification_granted':False,
 'real_sensor_factor_authorized':False,
 'health_training_authorized':False,
 'confirmation_test_accessed':False,
 'scientific_gates_closed':11,
}
with (out/'r78_independent_validation_v1.json').open('x',encoding='utf-8') as f:
 json.dump(receipt,f,indent=2,sort_keys=True)
 f.write('\n')
print('R78_INDEPENDENT_R76_R77_LINEAGE=PASS')
print('R78_INDEPENDENT_SCIENCE_AND_SANITIZATION=PASS')
