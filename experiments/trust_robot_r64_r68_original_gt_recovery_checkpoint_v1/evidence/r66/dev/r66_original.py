"""Replay committed original scientific reference rule on exact TRAIN GT."""
import hashlib
import json
import pathlib
import sys

repo, gt, index_path, prior_path, out = map(pathlib.Path, sys.argv[1:])

sys.path.insert(0, str(repo/'src'))

from trust_robot.m2dgr_reference import audit_m2dgr_reference

EXPECTED = '79d2c6d9132ce3cf87bb87445729302cd73709a59344a3dfacc5d7788937589d'

legacy = json.loads(index_path.read_text())
previous = json.loads(prior_path.read_text())

matches = [
    a for a in legacy['artifacts']
    if a['trajectory_id'] == 'room_02'
]
assert len(matches) == 1
assert matches[0]['raw_reference_sha256'] == EXPECTED
assert matches[0]['rotation_invalid_count'] == 90

assert previous['source_sha256'] == EXPECTED
assert previous['current_profile']['numeric_row_count'] == 3831
assert previous['current_profile']['numeric_width_histogram'] == {'8':3831}
assert previous['current_profile']['eight_column_diagnostics_only'][
    'candidate_last_four_deviation_gt_1e_2'
] == 90

audit = audit_m2dgr_reference(
    gt, trajectory_id='room_02', qnorm_tolerance=0.001
)

assert audit.source_sha256 == EXPECTED
assert audit.family.value == 'mocap'
assert audit.row_count == 3831
assert audit.qnorm_tolerance == 0.001
assert len(audit.invalid_rotation_sample_indices) == 90
assert len(audit.invalid_translation_sample_indices) == 0

invalid = list(audit.invalid_rotation_sample_indices)

runs = []
for index in invalid:
    if not runs or index > runs[-1][1] + 1:
        runs.append([index,index])
    else:
        runs[-1][1] = index

assert sum(b-a+1 for a,b in runs) == 90

source_code = repo/'src/trust_robot/m2dgr_reference.py'

report = {
    'schema':'TRUST_ROBOT_R66_ORIGINAL_RULE_REPLAY_V1',
    'trajectory':'room_02',
    'split':'train',
    'gt_sha256':EXPECTED,
    'original_auditor_relative_path':'src/trust_robot/m2dgr_reference.py',
    'original_auditor_sha256':hashlib.sha256(
        source_code.read_bytes()
    ).hexdigest(),
    'original_audit':audit.to_dict(),
    'invalid_sample_index_runs_0_based':runs,
    'invalid_run_count':len(runs),
    'maximum_invalid_run_length':max(b-a+1 for a,b in runs),
    'r65_deviation_gt_0p01_count':90,
    'historical_reference_invalid_count':90,
    'exact_historical_invalid_index_artifact_compared':False,
    'original_gt_modified':False,
    'reference_timestamp_semantics_qualified':False,
    'mocap_frame_to_lidar_qualified':False,
    'physical_calibration_qualified':False,
    'scientific_gates_closed':11,
    'pose_factors_authorized':False,
    'health_training_authorized':False,
    'ate_rpe_authorized':False,
    'confirmation_test_accessed':False,
    'raw_bag_opened':False,
    'git_modified':False,
}

path = out/'r66_original_rotation_rule_v1.json'
with path.open('x',encoding='utf-8') as f:
    json.dump(report,f,sort_keys=True,indent=2,allow_nan=False)
    f.write('\n')

print('R66_ORIGINAL_RULE_QNORM_TOLERANCE=0.001')
print('R66_ORIGINAL_RULE_RECORDS='+str(audit.row_count))
print('R66_ORIGINAL_RULE_INVALID_ROTATIONS='+str(len(invalid)))
print('R66_ORIGINAL_RULE_VALID_ROTATIONS='+str(audit.rotation_valid_count))
print('R66_ORIGINAL_RULE_INVALID_TRANSLATIONS='+str(len(audit.invalid_translation_sample_indices)))
print('R66_INVALID_ROTATION_RUNS='+str(len(runs)))
print('R66_LONGEST_INVALID_RUN='+str(report['maximum_invalid_run_length']))
print('R66_FIRST_INVALID_RUNS_0_BASED='+json.dumps(runs[:12]))
