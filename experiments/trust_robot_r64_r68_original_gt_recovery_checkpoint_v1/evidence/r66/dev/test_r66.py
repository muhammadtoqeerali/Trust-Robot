"""Synthetic checks of the original committed rule, including rejection."""
import pathlib
import sys
import tempfile

repo = pathlib.Path(sys.argv[1])
sys.path.insert(0,str(repo/'src'))
from trust_robot.m2dgr_reference import (
    audit_m2dgr_reference, M2DGRReferenceError
)

with tempfile.TemporaryDirectory(prefix='r66_synthetic_') as tmp:
    p=pathlib.Path(tmp)/'synthetic.txt'

    p.write_text(
        '1 0 0 0 0 0 0 1\n'
        '2 0 0 0 0 0 0 1.0005\n'
        '3 0 0 0 0 0 0 1.002\n'
        '4 0 0 0 0 0 0 0\n'
    )
    result=audit_m2dgr_reference(
        p,trajectory_id='room_02',qnorm_tolerance=0.001
    )
    assert result.invalid_rotation_sample_indices==(2,3)
    assert result.invalid_translation_sample_indices==()
    assert result.rotation_valid_count==2

    bad = [
        '1 0 0 0 0 0 0 1\n1 0 0 0 0 0 0 1\n',
        '2 0 0 0 0 0 0 1\n1 0 0 0 0 0 0 1\n',
        '1 0 0 0 0 0 1\n',
        '1 0 0 0 invalid 0 0 1\n',
        'nan 0 0 0 0 0 0 1\n',
    ]
    for text in bad:
        p.write_text(text)
        try:
            audit_m2dgr_reference(
                p,trajectory_id='room_02',qnorm_tolerance=0.001
            )
        except M2DGRReferenceError:
            pass
        else:
            raise AssertionError('SYNTHETIC_NEGATIVE_ACCEPTED')

print('R66_SYNTHETIC_ORIGINAL_RULE=PASS')
print('R66_SYNTHETIC_NEGATIVE_CONTROLS=5_REJECTED')
