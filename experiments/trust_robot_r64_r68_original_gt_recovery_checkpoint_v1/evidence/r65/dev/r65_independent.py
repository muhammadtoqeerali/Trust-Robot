"""Independent direct-file parse and scientific-denial verification."""
import collections
import hashlib
import json
import math
import pathlib
import re
import stat
import sys

gt,out,expected=map(str,sys.argv[1:4])
path=pathlib.Path(gt)
destination=pathlib.Path(out)
report=json.loads((destination/'r65_primary_profile_v1.json').read_text())

before=path.lstat()
assert stat.S_ISREG(before.st_mode) and before.st_nlink==1
assert stat.S_IMODE(before.st_mode)==0o400
assert before.st_size==504403
raw=path.read_bytes()
after=path.lstat()
assert (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(
    after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns
)
assert hashlib.sha256(raw).hexdigest()==expected==report['source_sha256']
assert report['source_bytes']==len(raw)

counts=collections.Counter()
blank=comment=nonnumeric=0
candidate=[]
times=[]
for line in raw.decode('utf-8-sig').splitlines():
    line=line.strip()
    if not line:
        blank+=1
        continue
    if line.startswith(('#','%','//')):
        comment+=1
        continue
    tokens=(line.split(',') if ',' in line else re.split(r'\s+',line))
    try:
        vals=tuple(float(x) for x in tokens)
    except ValueError:
        nonnumeric+=1
        continue
    counts[str(len(vals))]+=1
    if len(vals)==8:
        candidate.append(vals)
    if vals and math.isfinite(vals[0]):
        times.append(vals[0])

p=report['current_profile']
assert counts==p['numeric_width_histogram']
assert sum(counts.values())==p['numeric_row_count']
assert blank==p['blank_lines']
assert comment==p['comment_lines']
assert nonnumeric==p['nonnumeric_lines']
assert len(candidate)==p['eight_column_diagnostics_only']['eight_column_rows']

zero=nonfinite=deviation=translation_nonfinite=0
for r in candidate:
    if not all(map(math.isfinite,r[1:4])):
        translation_nonfinite+=1
    if not all(map(math.isfinite,r[4:8])):
        nonfinite+=1
        continue
    norm=math.sqrt(sum(x*x for x in r[4:8]))
    if norm <= 1e-12:
        zero+=1
    if abs(norm-1)>0.01:
        deviation+=1

q=p['eight_column_diagnostics_only']
assert q['candidate_last_four_nonfinite']==nonfinite
assert q['candidate_last_four_zero_norm']==zero
assert q['candidate_last_four_deviation_gt_1e_2']==deviation
assert q['candidate_translation_nonfinite']==translation_nonfinite

assert p['first_column_finite_values']==len(times)
assert p['first_column_min']==(min(times) if times else None)
assert p['first_column_max']==(max(times) if times else None)
assert p['first_column_duplicate_steps']==sum(a==b for a,b in zip(times,times[1:]))
assert p['first_column_decreasing_steps']==sum(b<a for a,b in zip(times,times[1:]))

assert report['historical_rotation_invalid_count']==90
assert report['scientific_gates_closed']==11
for key in (
    'prior_90_samples_reclassified_as_valid',
    'format_semantics_author_confirmed',
    'timestamp_physical_event_verified',
    'sensor_to_reference_clock_mapping_verified',
    'mocap_body_to_lidar_transform_verified',
    'physical_calibration_verified',
    'real_pose_factors_authorized',
    'health_training_authorized',
    'ate_rpe_authorized',
    'raw_rosbag_opened',
    'confirmation_test_accessed',
    'github_modified',
    'original_gt_modified',
):
    assert report[key] is False,key

check={
    'schema':'TRUST_ROBOT_R65_INDEPENDENT_DIRECT_GT_REPLAY_V1',
    'status':'PASS',
    'source_sha256':expected,
    'numeric_rows':sum(counts.values()),
    'eight_column_rows':len(candidate),
    'candidate_nonfinite_quaternions':nonfinite,
    'candidate_zero_norm_quaternions':zero,
    'candidate_nonunit_gt_0p01':deviation,
    'historical_invalid_rotations':90,
    'historical_rotation_rule_reproduced':False,
    'all_scientific_gates_closed':True,
}
with (destination/'r65_independent_validation_v1.json').open('x',encoding='utf-8') as f:
    json.dump(check,f,sort_keys=True,indent=2)
    f.write('\n')

print('R65_INDEPENDENT_SOURCE_REHASH=PASS')
print('R65_INDEPENDENT_NUMERICAL_STRUCTURE=PASS')
print('R65_INDEPENDENT_SCIENCE_DENIAL=PASS')
