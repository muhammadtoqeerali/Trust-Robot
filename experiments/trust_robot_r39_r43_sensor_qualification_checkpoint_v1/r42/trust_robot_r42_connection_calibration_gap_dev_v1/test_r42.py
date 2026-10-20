import ast
import copy
import pathlib
import struct
import sys

import r42_connection_inventory as m
import r42_independent_verify as v

for file in pathlib.Path(sys.argv[1]).glob('*.py'):
    ast.parse(
        file.read_text(),
        filename=str(file)
    )

def make(**fields):
    return b''.join(
        struct.pack(
            '<I',
            len(key.encode() + b'=' + value)
        ) + key.encode() + b'=' + value
        for key, value in fields.items()
    )

raw = make(
    op=b'\x07',
    topic=b'/camera/imu'
)

assert v.parse_fields(raw) == {
    b'op': b'\x07',
    b'topic': b'/camera/imu'
}

try:
    v.parse_fields(raw + b'\x00')
except ValueError:
    pass
else:
    raise AssertionError('TRUNCATED_HEADER_ACCEPTED')

example = {
    'schema': m.SCHEMA,
    'trajectory_id': 'room_02',
    'split': 'train',
    'github_baseline': m.BASE,
    'source_bag_sha256': m.BAG,
    'recording_header_and_connection_records_read': True,
    'sensor_payload_decompressed': False,
    'sensor_messages_decoded': 0,
    'confirmation_test_accessed': False,
    'github_modified': False,
    'connection_count': 15,
    'camera_info_topic_count': 0,
    'tf_topic_count': 0,
    'mocap_or_pose_reference_topic_count': 0,
    'r40_local_calibration_candidate_count': 10,
    'r41_local_reference_candidate_count': 0,
    'r41_frozen_reference_content_matches': 0,
    'author_relative_imu_rotation_supported_but_full_extrinsic_verified':
        False,
    'reference_mocap_invalid_rotation_count': 90,
    'unresolved_requirements': {
        key: 'NOT_PHYSICALLY_QUALIFIED'
        for key in m.CLOSED
    },
    'qualified_pose_factors': 0,
    'health_labels': 0,
    'ate_rpe_scores': 0,
    'next_phase':
        'R43_TRAIN_REFERENCE_CALIBRATION_SOURCE_ACQUISITION_PROTOCOL',
    'connections': [
        {
            'connection_id': i,
            'topic': '/camera/imu',
            'message_type': 'sensor_msgs/Imu',
            'physical_calibration_values_qualified': False
        }
        for i in range(15)
    ]
}

m.policy(example)

rejected = 0

mutations = (
    ('split', 'confirmation_test'),
    ('trajectory_id', 'room_03'),
    ('source_bag_sha256', '0'*64),
    ('sensor_payload_decompressed', True),
    ('sensor_messages_decoded', 1),
    ('confirmation_test_accessed', True),
    ('github_modified', True),
    ('camera_info_topic_count', 1),
    ('tf_topic_count', 1),
    ('mocap_or_pose_reference_topic_count', 1),
    ('r40_local_calibration_candidate_count', 9),
    ('r41_local_reference_candidate_count', 1),
    ('r41_frozen_reference_content_matches', 1),
    (
        'author_relative_imu_rotation_supported_but_full_extrinsic_verified',
        True
    ),
    ('reference_mocap_invalid_rotation_count', 0),
    ('qualified_pose_factors', 1),
    ('health_labels', 1),
    ('ate_rpe_scores', 1),
    ('next_phase', 'R44_SKIP')
)

for key, value in mutations:
    invalid = copy.deepcopy(example)
    invalid[key] = value

    try:
        m.policy(invalid)
    except ValueError:
        rejected += 1
    else:
        raise AssertionError(
            'SCIENTIFIC_PROMOTION_ACCEPTED:' + key
        )

for change in ('calibration', 'connection', 'injected_tf'):
    invalid = copy.deepcopy(example)

    if change == 'calibration':
        invalid['unresolved_requirements'][
            m.CLOSED[0]
        ] = 'QUALIFIED'

    elif change == 'connection':
        invalid['connections'][0]['connection_id'] = 4

    else:
        invalid['connections'][0]['topic'] = '/tf'
        invalid['connections'][0]['message_type'] = (
            'tf2_msgs/TFMessage'
        )

    try:
        m.policy(invalid)
    except ValueError:
        rejected += 1
    else:
        raise AssertionError(
            'UNSAFE_CONNECTION_ACCEPTED:' + change
        )

assert rejected == 22

print('R42_PYTHON_AST=3_PASS')
print('R42_MANUFACTURED_ROS_HEADER_FIELDS=PASS')
print(
    'R42_NEGATIVE_SCIENCE_CONNECTION_CONTROLS=22_REJECTED'
)
