"""Bounded, read-only numerical structure profiling; no GT pose admission."""
import collections
import hashlib
import json
import math
import os
import pathlib
import stat
import statistics
import sys

EXPECTED = '79d2c6d9132ce3cf87bb87445729302cd73709a59344a3dfacc5d7788937589d'
SIZE = 504403

def profile(data):
    if not data or b'\x00' in data:
        raise ValueError('EMPTY_OR_BINARY')
    if data.lstrip().lower().startswith(
        (b'<html', b'<!doctype', b'%pdf', b'pk\x03\x04')
    ):
        raise ValueError('NON_GT_CONTENT')

    lines = data.decode('utf-8-sig').splitlines()
    widths = collections.Counter()
    rows = []
    blanks = comments = nonnumeric = 0

    for line in lines:
        s = line.strip()
        if not s:
            blanks += 1
            continue
        if s.startswith(('#', '%', '//')):
            comments += 1
            continue
        pieces = s.split(',') if ',' in s else s.split()
        if len(pieces) > 64:
            raise ValueError('EXCESSIVE_COLUMNS')
        try:
            values = [float(x) for x in pieces]
        except ValueError:
            nonnumeric += 1
            continue
        widths[len(values)] += 1
        rows.append(values)

    if not rows:
        raise ValueError('NO_NUMERIC_ROWS')

    candidate = [r for r in rows if len(r) == 8]
    time_values = [
        r[0] for r in rows
        if r and math.isfinite(r[0])
    ]
    sequence = [
        r[0] for r in rows
        if r and math.isfinite(r[0])
    ]
    deltas = [b-a for a,b in zip(sequence,sequence[1:])]

    diag = {
        'eight_column_rows': len(candidate),
        'quaternion_order_verified': False,
        'rotation_frame_verified': False,
        'candidate_last_four_nonfinite': 0,
        'candidate_last_four_zero_norm': 0,
        'candidate_last_four_deviation_gt_1e_3': 0,
        'candidate_last_four_deviation_gt_1e_2': 0,
        'candidate_last_four_deviation_gt_1e_1': 0,
        'candidate_translation_nonfinite': 0,
    }

    for r in candidate:
        if not all(math.isfinite(x) for x in r[1:4]):
            diag['candidate_translation_nonfinite'] += 1

        q = r[4:8]
        if not all(math.isfinite(x) for x in q):
            diag['candidate_last_four_nonfinite'] += 1
            continue

        n = math.hypot(*q)
        if n <= 1e-12:
            diag['candidate_last_four_zero_norm'] += 1
        for threshold, key in (
            (1e-3,'candidate_last_four_deviation_gt_1e_3'),
            (1e-2,'candidate_last_four_deviation_gt_1e_2'),
            (1e-1,'candidate_last_four_deviation_gt_1e_1')
        ):
            if abs(n-1.0) > threshold:
                diag[key] += 1

    return {
        'raw_line_count': len(lines),
        'blank_lines': blanks,
        'comment_lines': comments,
        'nonnumeric_lines': nonnumeric,
        'numeric_row_count': len(rows),
        'numeric_width_histogram': dict(sorted(
            ((str(k),v) for k,v in widths.items()),
            key=lambda x:int(x[0])
        )),
        'first_column_is_verified_physical_time': False,
        'first_column_finite_values': len(time_values),
        'first_column_min': min(time_values) if time_values else None,
        'first_column_max': max(time_values) if time_values else None,
        'first_column_span': (
            max(time_values)-min(time_values)
            if time_values else None
        ),
        'first_column_nonfinite': sum(
            bool(r) and not math.isfinite(r[0]) for r in rows
        ),
        'first_column_duplicate_steps': sum(d==0 for d in deltas),
        'first_column_decreasing_steps': sum(d<0 for d in deltas),
        'first_column_median_positive_delta': (
            statistics.median(d for d in deltas if d>0)
            if any(d>0 for d in deltas) else None
        ),
        'eight_column_diagnostics_only': diag,
    }

def checked_read(path):
    before = path.lstat()
    if not (
        stat.S_ISREG(before.st_mode)
        and before.st_nlink == 1
        and before.st_size == SIZE
        and stat.S_IMODE(before.st_mode) == 0o400
    ):
        raise ValueError('UNSAFE_SOURCE_FILE')

    fd = os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    with os.fdopen(fd,'rb') as f:
        opened = os.fstat(f.fileno())
        data = f.read(SIZE+1)
        finished = os.fstat(f.fileno())
    after = path.lstat()

    ident = lambda s: (
        s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns
    )
    if not (
        ident(before)==ident(opened)==ident(finished)==ident(after)
        and len(data)==SIZE
    ):
        raise ValueError('CHANGED_DURING_READ')
    if hashlib.sha256(data).hexdigest()!=EXPECTED:
        raise ValueError('GT_SHA_MISMATCH')
    return data

def main(gt,index,receipt,out):
    source = checked_read(gt)
    evidence = json.loads(index.read_text())
    previous = json.loads(receipt.read_text())
    matches = [
        x for x in evidence['artifacts']
        if x['trajectory_id']=='room_02'
    ]
    assert len(matches)==1
    assert matches[0]['raw_reference_sha256']==EXPECTED
    assert matches[0]['rotation_invalid_count']==90
    assert previous['final_sha256']==EXPECTED
    assert previous['scientific_gates_closed']==11

    p = profile(source)
    report = {
        'schema':'TRUST_ROBOT_R65_RAW_GT_NUMERICAL_STRUCTURE_V1',
        'trajectory':'room_02',
        'split':'train',
        'source_sha256':EXPECTED,
        'source_bytes':len(source),
        'historical_rotation_invalid_count':90,
        'historical_reference_source':'mocap',
        'current_profile':p,
        'prior_90_samples_reclassified_as_valid':False,
        'format_semantics_author_confirmed':False,
        'timestamp_physical_event_verified':False,
        'sensor_to_reference_clock_mapping_verified':False,
        'mocap_body_to_lidar_transform_verified':False,
        'physical_calibration_verified':False,
        'scientific_gates_closed':11,
        'real_pose_factors_authorized':False,
        'health_training_authorized':False,
        'ate_rpe_authorized':False,
        'raw_rosbag_opened':False,
        'confirmation_test_accessed':False,
        'github_modified':False,
        'original_gt_modified':False,
    }
    with (out/'r65_primary_profile_v1.json').open('x',encoding='utf-8') as f:
        json.dump(report,f,indent=2,sort_keys=True,allow_nan=False)
        f.write('\n')

    q=p['eight_column_diagnostics_only']
    print('R65_NUMERIC_ROWS='+str(p['numeric_row_count']))
    print('R65_COLUMN_HISTOGRAM='+json.dumps(p['numeric_width_histogram'],sort_keys=True))
    print('R65_NONNUMERIC_LINES='+str(p['nonnumeric_lines']))
    print('R65_FIRST_COLUMN_MIN='+str(p['first_column_min']))
    print('R65_FIRST_COLUMN_MAX='+str(p['first_column_max']))
    print('R65_FIRST_COLUMN_SPAN='+str(p['first_column_span']))
    print('R65_DUPLICATE_STEPS='+str(p['first_column_duplicate_steps']))
    print('R65_DECREASING_STEPS='+str(p['first_column_decreasing_steps']))
    print('R65_EIGHT_COLUMN_ROWS='+str(q['eight_column_rows']))
    print('R65_QUATERNION_NONFINITE='+str(q['candidate_last_four_nonfinite']))
    print('R65_QUATERNION_ZERO_NORM='+str(q['candidate_last_four_zero_norm']))
    print('R65_QUATERNION_NORM_DEVIATION_GT_1E_2='+str(q['candidate_last_four_deviation_gt_1e_2']))
    print('R65_HISTORICAL_ROTATION_INVALID=90_NOT_SILENTLY_REPAIRED')

if __name__=='__main__':
    main(*map(pathlib.Path,sys.argv[1:]))
