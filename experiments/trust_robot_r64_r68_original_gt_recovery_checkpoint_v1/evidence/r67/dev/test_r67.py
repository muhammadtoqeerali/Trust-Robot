"""Synthetic positive and negative tests for committed reference parser."""
import pathlib
import sys
import tempfile

repo=pathlib.Path(sys.argv[1])
sys.path.insert(0,str(repo/'src'))

from trust_robot.m2dgr_reference_quality import (
    build_m2dgr_reference_quality_payload,
)
from trust_robot.m2dgr_reference import M2DGRReferenceError
from trust_robot.reference_quality import (
    validate_reference_quality_payload,
    ReferenceQualityError,
)

with tempfile.TemporaryDirectory(prefix='r67_synthetic_') as tmp:
    p=pathlib.Path(tmp)/'room_02.txt'
    p.write_text(
        '1 0 0 0 0 0 0 1\n'
        '2 0 0 0 0 0 0 0.5\n'
        '3 0 0 0 0 0 0 1\n'
    )
    payload=build_m2dgr_reference_quality_payload(
        p,trajectory_id='room_02'
    )
    validate_reference_quality_payload(payload)

    assert payload['rotation_validity']['invalid_count']==1
    assert payload['rotation_validity']['valid_count']==2
    assert payload['translation_validity']['invalid_count']==0
    assert payload['quality_summary']['evaluation_ready'] is False

    invalid_samples=payload['rotation_validity']['invalid_sample_runs']
    assert len(invalid_samples)==1
    assert invalid_samples[0]['start_sample_index']==1
    assert invalid_samples[0]['end_sample_index']==1

    tampered=dict(payload)
    tampered['sample_count']=99
    try:
        validate_reference_quality_payload(tampered)
    except ReferenceQualityError:
        pass
    else:
        raise AssertionError('TAMPERED_REFERENCE_QUALITY_ACCEPTED')

    negatives=[
        '1 0 0 0 0 0 1\n',
        '1 0 0 0 0 0 0 1\n1 0 0 0 0 0 0 1\n',
        '2 0 0 0 0 0 0 1\n1 0 0 0 0 0 0 1\n',
        'nan 0 0 0 0 0 0 1\n',
        '1 0 0 0 wrong 0 0 1\n',
    ]

    for bad in negatives:
        p.write_text(bad)
        try:
            build_m2dgr_reference_quality_payload(
                p,trajectory_id='room_02'
            )
        except (M2DGRReferenceError,ValueError):
            pass
        else:
            raise AssertionError('MALFORMED_REFERENCE_ACCEPTED')

print('R67_SYNTHETIC_PHASE2_REPLAY=PASS')
print('R67_NEGATIVE_CONTROLS=6_REJECTED')
