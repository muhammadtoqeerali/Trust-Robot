"""Shape-only candidate intake. Valid syntax never means qualified physics."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re

CANDIDATE_SCHEMA = (
    'TRUST_ROBOT_R76_PHYSICAL_SOURCE_CANDIDATE_V1'
)
CONTRACT_SCHEMA = (
    'TRUST_ROBOT_R76_PHYSICAL_SOURCE_INTAKE_CONTRACT_V1'
)

SHA = re.compile(r'[0-9a-f]{64}\Z')

REF = re.compile(
    r'(?:https://[A-Za-z0-9.-]+(?:/[^\s]*)?'
    r'|author-source:[a-z0-9_-]+)\Z'
)

FIELDS = frozenset((
    'schema',
    'claim_id',
    'trajectory_id',
    'split',
    'source_class',
    'source_reference',
    'source_sha256',
    'evidence_fields',
    'independent_validation_sha256',
    'physical_validation_completed',
    'factor_execution_authorized',
    'confirmation_test_used',
))

SOURCE_CLASSES = frozenset((
    'author_source_candidate',
    'measurement_candidate',
    'synthetic_fixture',
))


class IntakeError(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise IntakeError(reason)


def load(path):
    return json.loads(
        pathlib.Path(path).read_text(encoding='utf-8')
    )


def sha(path):
    return hashlib.sha256(
        pathlib.Path(path).read_bytes()
    ).hexdigest()


def frozen_boundary(r43, r53, r74):
    require(
        r43.get('schema') ==
        'TRUST_ROBOT_R43_EMPTY_EVIDENCE_RECEIPTS_V1',
        'R43_SCHEMA'
    )

    require(
        r53.get('schema') ==
        'TRUST_ROBOT_R53_UNFILLED_PHYSICAL_SOURCE_RECEIPTS_V1',
        'R53_SCHEMA'
    )

    require(
        r74.get('schema') ==
        'TRUST_ROBOT_R74_SANITIZED_EVIDENCE_DECISION_V1',
        'R74_SCHEMA'
    )

    gates = r43.get('gate_receipts')
    receipts = r53.get('receipts')

    require(
        type(gates) is dict and len(gates) == 11,
        'R43_COUNT'
    )

    require(
        type(receipts) is dict and len(receipts) == 5,
        'R53_COUNT'
    )

    for name, g in gates.items():
        require(
            g.get('status') == 'NO_SOURCE_RECEIVED'
            and g.get('physical_qualification_authorized') is False
            and g.get('source_uri') is None
            and g.get('source_sha256') is None
            and g.get('independent_validation_sha256') is None,
            'R43_FROZEN:' + name
        )

        fields = g.get('required_fields')

        require(
            type(fields) is dict
            and len(fields) > 0
            and all(v is None for v in fields.values()),
            'R43_FIELDS:' + name
        )

    for name, g in receipts.items():
        fields = g.get('fields')

        require(
            g.get('status') == 'NO_PHYSICAL_SOURCE_RECEIVED'
            and g.get('physical_measurement_qualified') is False
            and g.get('independently_validated') is False
            and type(fields) is dict
            and len(fields) > 0
            and all(v is None for v in fields.values()),
            'R53_FROZEN:' + name
        )

    q = r74.get('physical_qualification')

    require(
        type(q) is dict
        and len(q) == 10
        and all(v is False for v in q.values()),
        'R74_QUALIFICATION'
    )

    require(
        r74.get('scientific_gates_closed') == 11
        and r74.get('historical_gt_records') == 3831
        and r74.get('structurally_invalid_rotations') == 90
        and r74.get('invalid_rotation_sample_runs') == 61
        and r74.get('author_vicon_nominal_rate_hz') == 50
        and r74.get('author_calibration_explicit_mocap_terms') == 0,
        'R74_SCIENCE_STATE'
    )

    require(
        r74.get('real_pose_factors_authorized') is False
        and r74.get('ate_rpe_authorized') is False
        and r74.get('health_training_authorized') is False
        and r74.get('confirmation_test_accessed') is False,
        'R74_EXECUTION_DENIAL'
    )

    return gates, receipts


def validate_candidate(candidate, gates):
    """Validate a proposed evidence format, never physical truth."""
    require(
        type(candidate) is dict and set(candidate) == FIELDS,
        'FIELD_SET'
    )

    require(
        candidate['schema'] == CANDIDATE_SCHEMA,
        'SCHEMA'
    )

    claim = candidate['claim_id']

    require(
        type(claim) is str and claim in gates,
        'UNKNOWN_CLAIM'
    )

    require(
        candidate['trajectory_id'] == 'room_02'
        and candidate['split'] == 'train',
        'TRAIN_ONLY'
    )

    require(
        type(candidate['source_class']) is str
        and candidate['source_class'] in SOURCE_CLASSES,
        'SOURCE_CLASS'
    )

    ref = candidate['source_reference']

    require(
        type(ref) is str
        and len(ref) <= 512
        and REF.fullmatch(ref) is not None,
        'SOURCE_REFERENCE'
    )

    digest = candidate['source_sha256']

    require(
        type(digest) is str
        and SHA.fullmatch(digest) is not None,
        'SHA_FORMAT'
    )

    fields = candidate['evidence_fields']

    require(
        type(fields) is dict
        and set(fields) == set(
            gates[claim]['required_fields']
        ),
        'EVIDENCE_FIELD_SET'
    )

    for name, value in fields.items():
        require(
            value is None or (
                type(value) is str
                and 0 < len(value) <= 512
                and all(ord(c) >= 32 for c in value)
                and '/home/' not in value
                and '/mnt/' not in value
            ),
            'UNVERIFIED_FIELD:' + name
        )

    require(
        candidate['independent_validation_sha256'] is None,
        'NO_INDEPENDENT_VALIDATION_IS_ESTABLISHED'
    )

    for key in (
        'physical_validation_completed',
        'factor_execution_authorized',
        'confirmation_test_used',
    ):
        require(
            candidate[key] is False,
            'UNAUTHORIZED:' + key
        )

    return {
        'schema': CANDIDATE_SCHEMA,
        'claim_id': claim,
        'trajectory_id': 'room_02',
        'split': 'train',
        'format_valid': True,
        'source_bytes_verified': False,
        'physical_qualification_established': False,
        'factor_execution_authorized': False,
        'status':
            'CANDIDATE_FORMAT_ONLY_NOT_PHYSICALLY_QUALIFIED',
    }


def build_contract(gates, timing, pins):
    return {
        'schema': CONTRACT_SCHEMA,
        'trajectory_id': 'room_02',
        'split': 'train',
        'git_parent_commit':
            'c1f59bb5e38bdfece14798031c0d911441b28de8',
        'frozen_evidence_sha256': pins,

        'historical_r43_gates': {
            name: {
                'required_fields': sorted(g['required_fields']),
                'historical_status': g['status'],
                'candidate_is_physical_proof': False,
            }
            for name, g in sorted(gates.items())
        },

        'historical_r53_receipts': {
            name: {
                'required_fields': sorted(g['fields']),
                'historical_status': g['status'],
                'physical_clock_qualified': False,
            }
            for name, g in sorted(timing.items())
        },

        'original_room_02_gt_recovered_in_later_phase': True,
        'historical_r43_raw_gt_status_not_current': True,

        'mocap_frame_qualified': False,
        'clock_mapping_qualified': False,

        'independent_new_sources_qualified': 0,
        'new_execution_authorizations': 0,
        'scientific_gates_closed': 11,

        'real_pose_factors_authorized': False,
        'health_training_authorized': False,
        'ate_rpe_authorized': False,

        'raw_gt_opened': False,
        'rosbag_opened': False,
        'confirmation_test_accessed': False,
        'git_modified': False,
    }


if __name__ == '__main__':
    import sys

    r43p, r53p, r74p, out = map(
        pathlib.Path, sys.argv[1:]
    )

    r43, r53, r74 = map(
        load, (r43p, r53p, r74p)
    )

    gates, timing = frozen_boundary(
        r43, r53, r74
    )

    obj = build_contract(
        gates,
        timing,
        {
            'r43': sha(r43p),
            'r53': sha(r53p),
            'r74': sha(r74p),
        }
    )

    target = out / 'r76_source_intake_contract_v1.json'

    with target.open('x', encoding='utf-8') as f:
        json.dump(
            obj, f, sort_keys=True,
            indent=2, allow_nan=False
        )
        f.write('\n')

    print('R76A_R43_HISTORICAL_GATE_RECEIPTS=11_FROZEN')
    print('R76A_R53_HISTORICAL_TIMING_RECEIPTS=5_FROZEN')
    print('R76A_R74_CURRENT_SCIENCE_BOUNDARY=VERIFIED')
    print('R76A_SOURCE_INTAKE_CONTRACT=CREATED')
