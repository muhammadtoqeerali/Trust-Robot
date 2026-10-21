"""Independently parse raw GT and verify original-rule sample identities."""
import hashlib
import json
import math
import pathlib
import statistics
import sys

gt, out, prior = map(pathlib.Path, sys.argv[1:4])

EXPECTED='79d2c6d9132ce3cf87bb87445729302cd73709a59344a3dfacc5d7788937589d'

source=gt.read_bytes()
assert hashlib.sha256(source).hexdigest()==EXPECTED

report=json.loads((out/'r66_original_rotation_rule_v1.json').read_text())
previous=json.loads(prior.read_text())
assert report['gt_sha256']==EXPECTED

rows=[]
for raw in source.decode('ascii').splitlines():
    text=raw.strip()
    if not text:
        continue
    fields=text.split()
    assert len(fields)==8
    rows.append(tuple(float(x) for x in fields))

assert len(rows)==3831

timestamps=[r[0] for r in rows]
assert all(math.isfinite(t) for t in timestamps)
assert all(b>a for a,b in zip(timestamps,timestamps[1:]))

invalid=[]
invalid_translation=[]
norm_deviation_001=[]
norm_deviation_01=[]
rotation_steps=[]
previous_valid_q=None

for index,row in enumerate(rows):
    if not all(math.isfinite(v) for v in row[1:4]):
        invalid_translation.append(index)

    q=row[4:8]
    if not all(math.isfinite(x) for x in q):
        invalid.append(index)
        previous_valid_q=None
        continue

    magnitude=math.hypot(*q)
    if magnitude <= 0 or abs(magnitude-1.0)>0.001:
        invalid.append(index)
        previous_valid_q=None
    else:
        normalized=tuple(x/magnitude for x in q)
        if previous_valid_q is not None:
            dot=sum(x*y for x,y in zip(previous_valid_q,normalized))
            angle=math.degrees(
                2*math.acos(min(1.0,max(0.0,abs(dot))))
            )
            rotation_steps.append(angle)
        previous_valid_q=normalized

    if abs(magnitude-1.0)>0.001:
        norm_deviation_001.append(index)
    if abs(magnitude-1.0)>0.01:
        norm_deviation_01.append(index)

original=report['original_audit']
assert invalid==original['invalid_rotation_sample_indices']
assert invalid_translation==original['invalid_translation_sample_indices']
assert len(invalid)==90
assert len(norm_deviation_001)==90
assert len(norm_deviation_01)==90
assert invalid==norm_deviation_001==norm_deviation_01
assert previous['current_profile']['eight_column_diagnostics_only'][
    'candidate_last_four_deviation_gt_1e_2'
]==90

assert original['row_count']==3831
assert original['qnorm_tolerance']==0.001
assert original['rotation_valid_count']==3741

deltas=[b-a for a,b in zip(timestamps,timestamps[1:])]
assert math.isclose(original['min_dt_seconds'],min(deltas),rel_tol=1e-10,abs_tol=1e-10)
assert math.isclose(original['median_dt_seconds'],statistics.median(deltas),rel_tol=1e-10,abs_tol=1e-10)
assert math.isclose(original['max_dt_seconds'],max(deltas),rel_tol=1e-10,abs_tol=1e-10)

if rotation_steps:
    ordered=sorted(rotation_steps)
    pos=0.95*(len(ordered)-1)
    a=int(pos)
    p95=ordered[a]*(1-(pos-a))+ordered[min(a+1,len(ordered)-1)]*(pos-a)
    assert math.isclose(original['rotation_step_median_deg'],statistics.median(rotation_steps),rel_tol=1e-6,abs_tol=1e-6)
    assert math.isclose(original['rotation_step_p95_deg'],p95,rel_tol=1e-6,abs_tol=1e-6)
    assert math.isclose(original['rotation_step_max_deg'],max(rotation_steps),rel_tol=1e-6,abs_tol=1e-6)

runs=[]
for index in invalid:
    if not runs or index>runs[-1][1]+1:
        runs.append([index,index])
    else:
        runs[-1][1]=index

assert runs==report['invalid_sample_index_runs_0_based']
assert len(runs)==report['invalid_run_count']

for key in (
    'reference_timestamp_semantics_qualified',
    'mocap_frame_to_lidar_qualified',
    'physical_calibration_qualified',
    'pose_factors_authorized',
    'health_training_authorized',
    'ate_rpe_authorized',
    'confirmation_test_accessed',
    'raw_bag_opened',
    'git_modified',
    'original_gt_modified',
    'exact_historical_invalid_index_artifact_compared',
):
    assert report[key] is False,key

assert report['scientific_gates_closed']==11

validation={
    'schema':'TRUST_ROBOT_R66_INDEPENDENT_ROTATION_RULE_REPLAY_V1',
    'status':'PASS',
    'source_sha256':EXPECTED,
    'original_rule_invalid_indices_equal_independent':True,
    'invalid_rotations':90,
    'valid_rotations':3741,
    'invalid_translation':0,
    'invalid_runs':runs,
    'invalid_runs_are_sample_index_only':True,
    'historical_reference_quality_exact_indices_compared':False,
    'reference_physical_time_or_frame_verified':False,
    'scientific_gates_opened':0,
    'real_sensor_scoring_authorized':False,
}
with (out/'r66_independent_validation_v1.json').open('x',encoding='utf-8') as f:
    json.dump(validation,f,indent=2,sort_keys=True)
    f.write('\n')

print('R66_INDEPENDENT_INVALID_INDICES=EXACT_MATCH')
print('R66_INDEPENDENT_QNORM_0P001_INVALID=90')
print('R66_INDEPENDENT_QNORM_0P01_INVALID=90')
print('R66_INDEPENDENT_ROTATION_CONTINUITY=PASS')
print('R66_INDEPENDENT_SCIENCE_GATES=11_CLOSED')
