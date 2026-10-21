import hashlib
import json
import pathlib
import sys

out, gt, r43p, r53p, qualityp = map(
    pathlib.Path,sys.argv[1:]
)

report=json.loads((out/'r68_physical_gate_reconciliation_v1.json').read_text())
r43=json.loads(r43p.read_text())
r53=json.loads(r53p.read_text())
quality=json.loads(qualityp.read_text())

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

assert report['schema']=='TRUST_ROBOT_R68_RECOVERED_GT_PHYSICAL_GATE_RECONCILIATION_V1'
assert report['gt_sha256']==sha(gt)
assert report['historical_quality_sha256']==sha(qualityp)
assert report['source_receipt_sha256']['r43']==sha(r43p)
assert report['source_receipt_sha256']['r53']==sha(r53p)
assert report['source_receipt_sha256']['r67_quality']==sha(qualityp)

assert len(r43['gate_receipts'])==report['historical_r43_closed_gate_count']==11
assert len(r53['receipts'])==report['historical_r53_unfilled_sensor_receipts']==5

assert quality['sample_count']==report['reference_sample_count']==3831
assert quality['rotation_validity']['invalid_count']==report['invalid_rotation_count']==90
assert quality['rotation_validity']['valid_count']==report['valid_rotation_count']==3741
assert len(quality['rotation_validity']['invalid_sample_runs'])==61

assert report['dataset_bytes_recovered_and_verified'] is True
assert report['historical_quality_report_byte_reproduced'] is True
assert report['raw_reference_access_question_resolved_locally'] is True
assert report['raw_reference_complete_scientific_qualification'] is False
assert report['physical_qualification_authorizations_opened']==0
assert report['scientific_gates_closed']==11

for key in (
    'author_confirmed_gt_checksum',
    'reference_event_and_timebase_verified',
    'reference_to_sensor_clock_mapping_verified',
    'mocap_tracked_body_origin_verified',
    'mocap_to_lidar_transform_verified',
    'physical_sensor_calibration_verified',
    'invalid_quaternions_repaired',
    'automatic_reference_filter_authorized',
    'real_pose_factors_authorized',
    'health_training_authorized',
    'ate_rpe_authorized',
    'raw_bag_opened',
    'confirmation_test_accessed',
    'original_gt_modified',
    'git_modified',
):
    assert report[key] is False,key

validation={
    'schema':'TRUST_ROBOT_R68_INDEPENDENT_PHYSICAL_GATE_REVIEW_V1',
    'status':'PASS',
    'historical_gate_receipts_unchanged':True,
    'recovered_gt_is_not_physical_calibration':True,
    'raw_gt_acquisition_issue_closed_locally':True,
    'eleven_scientific_gates_remain_closed':True,
    'real_pose_factors_authorized':False,
    'health_training_authorized':False,
    'ate_rpe_authorized':False,
}
with (out/'r68_independent_validation_v1.json').open('x',encoding='utf-8') as f:
    json.dump(validation,f,sort_keys=True,indent=2)
    f.write('\n')

print('R68_INDEPENDENT_GATE_RECONCILIATION=PASS')
print('R68_INDEPENDENT_SCIENCE_DENIAL=PASS')
