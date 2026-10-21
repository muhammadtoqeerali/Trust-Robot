"""Synthetic acceptance and 12 mutation-based denial controls."""
import copy
import sys

import r76_intake as m

r43, r53, r74 = map(
    m.load, sys.argv[1:]
)

gates, _ = m.frozen_boundary(
    r43, r53, r74
)

claim = 'mocap_body_to_lidar_physically_verified'

assert claim in gates

fixture = {
    'schema': m.CANDIDATE_SCHEMA,
    'claim_id': claim,
    'trajectory_id': 'room_02',
    'split': 'train',
    'source_class': 'synthetic_fixture',
    'source_reference':
        'author-source:synthetic_fixture',
    'source_sha256': 'a' * 64,
    'evidence_fields': {
        x: None
        for x in gates[claim]['required_fields']
    },
    'independent_validation_sha256': None,
    'physical_validation_completed': False,
    'factor_execution_authorized': False,
    'confirmation_test_used': False,
}

result = m.validate_candidate(
    fixture, gates
)

assert result['format_valid'] is True
assert result['physical_qualification_established'] is False

filled = copy.deepcopy(fixture)

filled['evidence_fields'] = {
    k: 'SYNTHETIC_UNVERIFIED'
    for k in filled['evidence_fields']
}

assert m.validate_candidate(
    filled, gates
)['factor_execution_authorized'] is False

print('R76A_SYNTHETIC_FORMAT_POSITIVES=2_PASS_NO_PHYSICAL_PROOF')


def reject(label, fn):
    obj = copy.deepcopy(fixture)
    fn(obj)

    try:
        m.validate_candidate(obj, gates)
    except m.IntakeError:
        return

    raise AssertionError(
        'UNSAFE_CANDIDATE_ACCEPTED:' + label
    )


cases = (
    ('claim',
     lambda x: x.update(claim_id='unknown')),

    ('heldout',
     lambda x: x.update(split='confirmation_test')),

    ('trajectory',
     lambda x: x.update(trajectory_id='room_03')),

    ('missing',
     lambda x: x.pop('confirmation_test_used')),

    ('extra',
     lambda x: x['evidence_fields'].update(fake='x')),

    ('hash',
     lambda x: x.update(source_sha256='A' * 64)),

    ('source',
     lambda x: x.update(source_reference='file:///private')),

    ('physical',
     lambda x: x.update(physical_validation_completed=True)),

    ('factor',
     lambda x: x.update(factor_execution_authorized=True)),

    ('confirmation',
     lambda x: x.update(confirmation_test_used=True)),

    ('bool_int',
     lambda x: x.update(factor_execution_authorized=0)),

    ('validator',
     lambda x: x.update(
         independent_validation_sha256='b' * 64
     )),
)

for label, fn in cases:
    reject(label, fn)

print('R76A_NEGATIVE_CONTROLS=12_REJECTED')
