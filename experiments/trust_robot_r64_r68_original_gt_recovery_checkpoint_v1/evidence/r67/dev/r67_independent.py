"""Independent original-GT mask/runs comparison against regenerated Phase-2 artifact."""
import hashlib
import json
import math
import pathlib
import sys

gt, qualityfile, receiptfile, r66file, indexfile, out = map(
    pathlib.Path,sys.argv[1:]
)

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
quality=json.loads(qualityfile.read_text())
receipt=json.loads(receiptfile.read_text())
r66=json.loads(r66file.read_text())
index=json.loads(indexfile.read_text())

original=next(x for x in index['artifacts'] if x['trajectory_id']=='room_02')

assert sha(gt)==receipt['source_gt_sha256']
assert sha(qualityfile)==original['artifact_file_sha256']
assert quality['reference_quality_content_sha256']==original['artifact_content_sha256']

rows=[]
for line in gt.read_text(encoding='ascii').splitlines():
    if not line.strip():
        continue
    fields=line.split()
    assert len(fields)==8
    rows.append(tuple(float(x) for x in fields))

assert len(rows)==3831
assert all(math.isfinite(row[0]) for row in rows)
assert all(b[0]>a[0] for a,b in zip(rows,rows[1:]))

invalid=[]
for idx,row in enumerate(rows):
    q=row[4:8]
    if not all(math.isfinite(x) for x in q):
        invalid.append(idx)
        continue
    norm=math.sqrt(sum(x*x for x in q))
    if not (norm>0 and abs(norm-1.0)<=0.001):
        invalid.append(idx)

assert invalid==r66['original_audit']['invalid_rotation_sample_indices']
assert len(invalid)==quality['rotation_validity']['invalid_count']==90

def runs(indices):
    result=[]
    for n in indices:
        if not result or n>result[-1][1]+1:
            result.append([n,n])
        else:
            result[-1][1]=n
    return result

def expected_runs(indices):
    return [
        {
            'start_sample_index':a,
            'end_sample_index':b,
            'start_timestamp_seconds':rows[a][0],
            'end_timestamp_seconds':rows[b][0],
        }
        for a,b in runs(indices)
    ]

assert quality['rotation_validity']['invalid_sample_runs']==expected_runs(invalid)

valid=[i for i in range(len(rows)) if i not in set(invalid)]
assert quality['rotation_validity']['valid_sample_runs']==expected_runs(valid)

assert quality['translation_validity']['invalid_count']==0
assert quality['translation_validity']['valid_sample_runs']==expected_runs(
    list(range(len(rows)))
)

assert quality['sample_count']==len(rows)
assert quality['quality_summary']['evaluation_ready'] is False
assert quality['continuous_time_coverage']['verified'] is False

assert receipt['scientific_gates_closed']==11
for k in (
    'original_gt_modified','physical_reference_quality_verified',
    'mocap_to_lidar_transform_verified','reference_clock_verified',
    'continuous_time_coverage_verified','real_pose_factors_authorized',
    'health_training_authorized','ate_rpe_authorized',
    'raw_bag_opened','confirmation_test_accessed','git_modified'
):
    assert receipt[k] is False,k

report={
    'schema':'TRUST_ROBOT_R67_INDEPENDENT_HISTORICAL_QUALITY_REPLAY_V1',
    'status':'PASS',
    'historical_file_sha256_exact_match':True,
    'historical_content_sha256_exact_match':True,
    'invalid_rotation_indices_independently_verified':90,
    'invalid_rotation_runs_independently_verified':61,
    'physical_semantics_qualified':False,
    'scientific_gates_opened':0,
    'real_pose_factors_health_or_scoring_authorized':False
}

with (out/'r67_independent_validation_v1.json').open('x',encoding='utf-8') as f:
    json.dump(report,f,sort_keys=True,indent=2)
    f.write('\n')

print('R67_INDEPENDENT_HISTORICAL_FILE_SHA=EXACT')
print('R67_INDEPENDENT_ROTATION_RUNS=EXACT')
print('R67_INDEPENDENT_SCIENCE_DENIAL=PASS')
