import ast
import copy
import pathlib
import sys

import r41_semantics as s

files = sorted(
    pathlib.Path(sys.argv[1]).glob('*.py')
)

assert len(files) == 3

for path in files:
    ast.parse(
        path.read_text(),
        filename=str(path)
    )

print('R41_PYTHON_AST=3_PASS')

model = {
    'schema':
        'TRUST_ROBOT_R41_TRAIN_CALIBRATION_CANDIDATE_SEMANTICS_V1',
    'trajectory_id': 'room_02',
    'split': 'train',
    'github_baseline': s.BASE,
    'source_bag_sha256': s.BAG,
    'raw_bag_opened': False,
    'confirmation_test_payload_accessed': False,
    'github_modified': False,
    'physical_calibration_admitted': False,
    'reference_scoring_authorized': False,
    'qualified_pose_factors': 0,
    'health_labels': 0,
    'ate_rpe_scores': 0,
    'qualification_gates': {
        k: 'UNVERIFIED_OR_DENIED'
        for k in s.GATES
    },
    'configuration_semantics': [
        {
            'relative_config_path': name,
            'role': s.classification(name),
            'git_blob_identical': True,
            'physical_sensor_calibration_qualified': False
        }
        for name in s.FILES
    ],
    'config_role_counts': {
        'trust_robot_software_contracts': 4,
        'separate_software_protocols': 6
    },
    'room_02_reference_source': 'mocap',
    'room_02_invalid_rotation_records': 90,
    'frozen_raw_reference_sha256': s.REFERENCE,
    'room_02_reference_file_candidates': [],
    'next_phase':
        'R42_TRAIN_SENSOR_CALIBRATION_EVIDENCE_GAP_RESOLUTION'
}

s.policy(model)

changes = [
    ('split', 'confirmation_test'),
    ('trajectory_id', 'room_03'),
    ('github_baseline', '0'*40),
    ('source_bag_sha256', '0'*64),
    ('raw_bag_opened', True),
    ('confirmation_test_payload_accessed', True),
    ('github_modified', True),
    ('physical_calibration_admitted', True),
    ('reference_scoring_authorized', True),
    ('qualified_pose_factors', 1),
    ('health_labels', 1),
    ('ate_rpe_scores', 1),
    ('configuration_semantics', []),
    ('config_role_counts', {}),
    ('room_02_reference_source', 'rtk_ins'),
    ('room_02_invalid_rotation_records', 0),
    ('frozen_raw_reference_sha256', '0'*64),
    ('next_phase', 'SKIP')
]

rejected = 0

for key, value in changes:
    invalid = copy.deepcopy(model)
    invalid[key] = value

    try:
        s.policy(invalid)
    except ValueError:
        rejected += 1
    else:
        raise AssertionError(
            'PROMOTION_ACCEPTED:' + key
        )

for kind in (
    'gate',
    'role',
    'credential',
    'source_match'
):
    invalid = copy.deepcopy(model)

    if kind == 'gate':
        invalid['qualification_gates'][
            s.GATES[0]
        ] = 'VERIFIED'

    elif kind == 'role':
        invalid['configuration_semantics'][0][
            'role'
        ] = 'PHYSICAL'

    elif kind == 'credential':
        invalid['configuration_semantics'][0][
            'physical_sensor_calibration_qualified'
        ] = True

    else:
        invalid['room_02_reference_file_candidates'] = [
            {'reference_physically_qualified': True}
        ]

    try:
        s.policy(invalid)
    except ValueError:
        rejected += 1
    else:
        raise AssertionError(
            'PROMOTION_ACCEPTED:' + kind
        )

assert rejected == 22

assert s.classification(
    s.FILES[3]
).startswith('TRUST_ROBOT')

assert s.classification(
    s.FILES[0]
).startswith('SEPARATE')

print(
    'R41_NEGATIVE_SCIENCE_ROLE_AND_HOLDOUT_CONTROLS=22_REJECTED'
)
