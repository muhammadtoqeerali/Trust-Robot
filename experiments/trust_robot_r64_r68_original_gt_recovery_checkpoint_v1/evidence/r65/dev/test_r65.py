"""Synthetic-only numerical profiling controls."""
from r65_primary import profile

valid = (
    b'# synthetic only\n'
    b'0 1 2 3 0 0 0 1\n'
    b'1 1 2 3 0 0 0 0\n'
    b'2 1 2 3 nan 0 0 1\n'
    b'3 1 2 3 0 0 0 1\n'
)
p=profile(valid)
assert p['numeric_row_count']==4
assert p['numeric_width_histogram']=={'8':4}
q=p['eight_column_diagnostics_only']
assert q['candidate_last_four_zero_norm']==1
assert q['candidate_last_four_nonfinite']==1
assert q['candidate_last_four_deviation_gt_1e_2']==1

t=profile(b'1 0 0 0 0 0 0 1\n1 0 0 0 0 0 0 1\n0 0 0 0 0 0 0 1\n')
assert t['first_column_duplicate_steps']==1
assert t['first_column_decreasing_steps']==1

neg=[
    b'',
    b'<html>Sign in</html>',
    b'abc\n',
    b'1 2\x00 3\n',
    (b'1 '*65)+b'\n',
]
for item in neg:
    try:
        profile(item)
    except (ValueError,UnicodeError):
        pass
    else:
        raise AssertionError('NEGATIVE_CONTROL_ACCEPTED')

print('R65_SYNTHETIC_QUATERNION_AND_TIMESTAMP_DIAGNOSTICS=PASS')
print('R65_NEGATIVE_CONTENT_CONTROLS=5_REJECTED')
