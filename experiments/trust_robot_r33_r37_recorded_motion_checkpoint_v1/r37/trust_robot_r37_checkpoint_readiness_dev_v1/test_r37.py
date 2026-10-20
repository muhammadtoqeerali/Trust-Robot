import copy
import numpy as np
from scipy.spatial.transform import Rotation

import r37_review as m
import r37_independent_verify as v

assert len(m.PINS) == 21
assert m.PHASE_COUNTS == {
    'r33': 7,
    'r34': 4,
    'r35': 5,
    'r36': 5
}

matrix = v.qmatrix(
    v.qmul(
        v.qexp([0, .003, 0]),
        v.qexp([.005, 0, 0])
    )
)

expected = (
    Rotation.from_rotvec([0, .003, 0])
    * Rotation.from_rotvec([.005, 0, 0])
).as_matrix()

assert np.allclose(
    matrix, expected, atol=1e-12
)

example = {
    'schema':
        'TRUST_ROBOT_R37_R33_R36_NONFACTOR_CHECKPOINT_READINESS_V1',
    'trajectory_id': 'room_02',
    'split': 'train',
    'github_parent_commit': m.BASE,
    'authenticated_bag_sha256': m.BAG,
    'phase_counts': m.PHASE_COUNTS,
    'source_sha256': m.PINS,
    'off_git_artifact_count': 21,
    'readiness_decision':
        'READY_FOR_SHA_PINNED_R33_R37_NONFACTOR_GITHUB_CHECKPOINT',
    'raw_bag_archived': False,
    'observations': {
        'camera_pairs': 8,
        'camera_frames': 16,
        'imu_short_intervals': 16,
        'imu_short_messages': 32,
        'imu_gyro_windows': 16,
        'imu_gyro_messages': 48,
        'imu_gyro_intervals': 32
    },
    'scientific_pose_factors': 0,
    'health_labels': 0,
    'pose_accuracy_scores': 0,
    **{key: False for key in m.GATES}
}

m.policy(example)

rejected = 0

for key in (
    *m.GATES,
    'scientific_pose_factors',
    'health_labels',
    'pose_accuracy_scores'
):
    challenge = copy.deepcopy(example)
    challenge[key] = (
        True if key in m.GATES else 1
    )

    try:
        m.policy(challenge)
    except ValueError:
        rejected += 1
    else:
        raise AssertionError(
            'PROMOTION_ACCEPTED:' + key
        )

mutations = (
    ('split', 'confirmation_test'),
    ('raw_bag_archived', True),
    ('off_git_artifact_count', 20),
    ('readiness_decision', 'QUALIFIED_POSE'),
    ('authenticated_bag_sha256', '0'*64),
    ('github_parent_commit', '0'*40),
    ('phase_counts', {
        'r33': 8,
        'r34': 4,
        'r35': 5,
        'r36': 5
    }),
    ('source_sha256', {}),
    ('observations', {}),
    ('trajectory_id', 'room_03')
)

for key, value in mutations:
    challenge = copy.deepcopy(example)
    challenge[key] = value

    try:
        m.policy(challenge)
    except ValueError:
        rejected += 1
    else:
        raise AssertionError(
            'INVALID_READINESS_ACCEPTED:' + key
        )

assert rejected == len(m.GATES) + 3 + len(mutations)

print('R37_NUMERICAL_QUATERNION_FIXTURE=PASS')
print(
    'R37_NEGATIVE_READINESS_CONTROLS=%d_REJECTED'
    % rejected
)
