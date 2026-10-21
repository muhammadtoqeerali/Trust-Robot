"""Independent quarantine receipt checks, rehashing any candidate without promotion."""
import hashlib
import json
import pathlib
import stat
import sys

out, stage, protocol = map(pathlib.Path, sys.argv[1:])
receipt = json.loads((out/'r61_quarantine_receipt_v1.json').read_text())
gates = json.loads(protocol.read_text())
assert receipt['schema'] == 'TRUST_ROBOT_R61_READ_ONLY_GT_QUARANTINE_V1'
assert receipt['candidate_path'] == str(stage)
assert len(receipt['scientific_gates_closed']) == 11
assert receipt['scientific_gates_closed'] == sorted(gates['requests'])
assert receipt['science_gates_opened'] == 0
assert receipt['official_ground_truth_independently_authenticated'] is False
assert receipt['clock_frame_pose_semantics_qualified'] is False
assert receipt['quarantine_only_not_gt_ingestion'] is True
for field in ('real_pose_factors_authorized', 'health_training_authorized',
              'ate_rpe_authorized', 'raw_bag_opened', 'confirmation_test_accessed',
              'git_modified', 'author_communication_sent_by_this_phase'):
    assert receipt[field] is False, field
result = receipt['candidate']
assert result['status'] in {
    'ABSENT', 'REFUSED_NONREGULAR_OR_LINK', 'REFUSED_SIZE_BOUND',
    'REFUSED_NON_GT_WEB_OR_CONTAINER_CONTENT', 'REFUSED_BINARY_CONTENT',
    'CANDIDATE_BYTES_PRESENT_UNVERIFIED'
}
if result['status'] == 'ABSENT':
    assert not stage.exists() and not stage.is_symlink()
    assert result['observed_sha256'] is None
elif result['status'] in ('REFUSED_NONREGULAR_OR_LINK', 'REFUSED_SIZE_BOUND'):
    assert result['observed_sha256'] is None
else:
    st = stage.lstat()
    assert stat.S_ISREG(st.st_mode) and st.st_nlink == 1
    digest = hashlib.sha256()
    total = 0
    with stage.open('rb') as f:
        while True:
            chunk = f.read(1024*1024)
            if not chunk:
                break
            digest.update(chunk)
            total += len(chunk)
    assert digest.hexdigest() == result['observed_sha256']
    assert total == result['bytes'] == st.st_size
    assert result['historical_digest_match'] is (digest.hexdigest() == receipt['historical_expected_digest_only'])
verification = {
    'schema': 'TRUST_ROBOT_R61_INDEPENDENT_QUARANTINE_REPLAY_V1',
    'status': 'PASS', 'observed_stage_status': result['status'],
    'authentic_official_gt_certified': False,
    'scientific_gates_opened': 0,
    'real_pose_factors_or_scoring_admitted': False,
}
with (out/'r61_independent_validation_v1.json').open('x',encoding='utf-8') as f:
    json.dump(verification, f, indent=2, sort_keys=True)
    f.write('\n')
print('R61_INDEPENDENT_QUARANTINE_REPLAY=PASS')
print('R61_ELEVEN_GATES=ALL_CLOSED')
