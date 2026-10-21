"""Recreate original Phase-2 reference quality with exact canonical GT basename."""
import hashlib
import json
import pathlib
import shutil
import sys
import tempfile

repo, gt, indexfile, r66file, dev, out = map(
    pathlib.Path, sys.argv[1:]
)

sys.path.insert(0, str(repo / 'src'))

from trust_robot.m2dgr_reference_quality import (
    build_m2dgr_reference_quality_payload,
)
from trust_robot.reference_quality import (
    canonical_reference_quality_json,
    validate_reference_quality_payload,
)

GT_SHA='79d2c6d9132ce3cf87bb87445729302cd73709a59344a3dfacc5d7788937589d'

index=json.loads(indexfile.read_text())
r66=json.loads(r66file.read_text())

entries=[
    e for e in index['artifacts']
    if e['trajectory_id']=='room_02'
]
assert len(entries)==1
original=entries[0]

assert original['raw_reference_sha256']==GT_SHA
assert original['reference_source']=='mocap'
assert original['rotation_invalid_count']==90

assert r66['gt_sha256']==GT_SHA
assert r66['original_audit']['row_count']==3831
assert len(r66['original_audit']['invalid_rotation_sample_indices'])==90

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

assert digest(gt)==GT_SHA

# The original generator embeds the filename in its source-relative path.
# Temporarily reproduce that filename OUTSIDE Git, without modifying GT.
with tempfile.TemporaryDirectory(
    prefix='r67_canonical_name_', dir=str(dev)
) as tmp:
    alias=pathlib.Path(tmp)/'room_02.txt'
    shutil.copyfile(gt,alias)
    alias.chmod(0o400)
    assert digest(alias)==GT_SHA

    payload=build_m2dgr_reference_quality_payload(
        alias,
        trajectory_id='room_02',
        qnorm_tolerance=0.001
    )
    validate_reference_quality_payload(payload)

serialized=canonical_reference_quality_json(payload).encode('utf-8')
rebuilt_sha=hashlib.sha256(serialized).hexdigest()

# Persist derived quality metadata, NEVER the GT payload.
artifact=out/'r67_rebuilt_room_02_reference_quality_v1.json'
with artifact.open('xb') as f:
    f.write(serialized)

print('R67_REBUILT_ARTIFACT_SHA256='+rebuilt_sha)
print('R67_HISTORICAL_ARTIFACT_SHA256='+original['artifact_file_sha256'])

if rebuilt_sha!=original['artifact_file_sha256']:
    raise RuntimeError('R67_HISTORICAL_ARTIFACT_FILE_SHA_MISMATCH')

if payload['reference_quality_content_sha256']!=original['artifact_content_sha256']:
    raise RuntimeError('R67_HISTORICAL_ARTIFACT_CONTENT_SHA_MISMATCH')

assert payload['source']['relative_path']=='raw/ground_truth/room_02.txt'
assert payload['source']['sha256']==GT_SHA
assert payload['sample_count']==3831
assert payload['reference_source']=='mocap'
assert payload['rotation_validity']['invalid_count']==90
assert payload['rotation_validity']['valid_count']==3741
assert payload['translation_validity']['invalid_count']==0
assert payload['quality_summary']['evaluation_ready'] is False
assert payload['quality_summary']['physical_quality_verified'] is False
assert payload['quality_summary']['synchronization_verified'] is False
assert payload['continuous_time_coverage']['verified'] is False

invalid_runs=payload['rotation_validity']['invalid_sample_runs']
expected_runs=r66['invalid_sample_index_runs_0_based']

assert [
    [x['start_sample_index'],x['end_sample_index']]
    for x in invalid_runs
]==expected_runs

assert len(invalid_runs)==61

receipt={
    'schema':'TRUST_ROBOT_R67_HISTORICAL_PHASE2_QUALITY_REPLAY_V1',
    'trajectory':'room_02',
    'split':'train',
    'source_gt_sha256':GT_SHA,
    'source_gt_bytes':504403,
    'original_quality_artifact_sha256':original['artifact_file_sha256'],
    'reproduced_quality_artifact_sha256':rebuilt_sha,
    'original_quality_content_sha256':original['artifact_content_sha256'],
    'exact_historical_quality_reproduction':True,
    'record_count':3831,
    'valid_rotation_count':3741,
    'invalid_rotation_count':90,
    'invalid_rotation_run_count':61,
    'invalid_translation_count':0,
    'temporary_canonical_gt_copy_removed':True,
    'original_gt_modified':False,
    'physical_reference_quality_verified':False,
    'mocap_to_lidar_transform_verified':False,
    'reference_clock_verified':False,
    'continuous_time_coverage_verified':False,
    'scientific_gates_closed':11,
    'real_pose_factors_authorized':False,
    'health_training_authorized':False,
    'ate_rpe_authorized':False,
    'raw_bag_opened':False,
    'confirmation_test_accessed':False,
    'git_modified':False,
}

with (out/'r67_replay_receipt_v1.json').open('x',encoding='utf-8') as f:
    json.dump(receipt,f,sort_keys=True,indent=2)
    f.write('\n')

print('R67_HISTORICAL_QUALITY_FILE_HASH=EXACT_MATCH')
print('R67_HISTORICAL_QUALITY_CONTENT_HASH=EXACT_MATCH')
print('R67_ORIGINAL_90_INVALID_ROTATIONS=REPRODUCED')
print('R67_ORIGINAL_61_INVALID_RUNS=REPRODUCED')
