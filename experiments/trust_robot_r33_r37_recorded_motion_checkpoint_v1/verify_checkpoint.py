"""Independent R33–R37 SHA and scientific gate verifier."""

import ast
import hashlib
import json
import pathlib
import subprocess

A = pathlib.Path(__file__).resolve().parent
R = A.parents[1]

BASE = 'ebfd02b0ef8ad79b2e6a9810897fcb71efec2e87'
BAG = 'ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1'
SPLIT = '017a388ef1ce4ad30812669632a022ca37c084871bc949693fd9c0541014238f'

COUNTS = {
    'r33': 7,
    'r34': 4,
    'r35': 5,
    'r36': 5,
    'r37': 5
}

def need(ok, reason):
    if not ok:
        raise ValueError(
            'R38_ARCHIVE_DENIED:' + reason
        )

def sha(blob):
    return hashlib.sha256(blob).hexdigest()

def hashed(path):
    need(
        path.is_file()
        and not path.is_symlink()
        and path.stat().st_nlink == 1
        and 0 < path.stat().st_size <= 4_000_000,
        'UNSAFE_FILE:' + str(path)
    )
    return sha(path.read_bytes())

def load(relative):
    return json.loads(
        (A / relative).read_text()
    )

def find(sources, filename):
    matches = [
        key for key in sources
        if key.endswith('/' + filename)
    ]
    need(
        len(matches) == 1,
        'UNIQUE_FILE:' + filename
    )
    return matches[0]

def item(sources, filename):
    return A / find(sources, filename)

def denied(report, fields, label):
    for key in fields:
        need(
            report.get(key) is False,
            label + ':' + key
        )

def zero(report, fields, label):
    for key in fields:
        need(
            type(report.get(key)) is int
            and report[key] == 0,
            label + ':' + key
        )

m = load('checkpoint_manifest_v1.json')

need(
    m['schema'] ==
    'TRUST_ROBOT_R33_R37_TRAIN_RECORDED_MOTION_CHECKPOINT_V1'
    and m['parent_commit'] == BASE
    and m['branch'] == 'kios-isaacsim-v15-integration',
    'MANIFEST_ID'
)

need(
    m['trajectory_id'] == 'room_02'
    and m['split'] == 'train'
    and m['bag_sha256'] == BAG
    and m['split_manifest_sha256'] == SPLIT,
    'MANIFEST_INPUT'
)

need(
    m['raw_bag_in_archive'] is False
    and m['phase_counts'] == COUNTS,
    'MANIFEST_SCOPE'
)

zero(
    m,
    ('real_pose_factors_generated', 'health_labels_generated'),
    'MANIFEST'
)

denied(
    m,
    (
        'physical_capture_time_verified',
        'cross_modal_alignment_performed',
        'full_extrinsics_verified',
        'independent_ground_truth_scored',
        'real_sensor_factor_execution_authorized',
        'health_model_training_authorized',
        'm2dgr_scoring_authorized'
    ),
    'MANIFEST'
)

pins = m['source_artifact_sha256']
files = m['file_sha256']

need(
    len(pins) == 26
    and len(files) == 27
    and set(files) == set(pins) | {'README.md'},
    'EXACT_MANIFEST_FILE_COUNT'
)

need(
    all(files[key] == value for key, value in pins.items()),
    'FROZEN_PINS'
)

need(
    {
        phase: sum(
            key.startswith(phase + '/')
            for key in pins
        )
        for phase in COUNTS
    } == COUNTS,
    'PHASE_COUNTS'
)

actual = {
    p.relative_to(A).as_posix()
    for p in A.rglob('*')
    if p.is_file()
}

need(
    actual == set(files) | {
        'checkpoint_manifest_v1.json',
        'verify_checkpoint.py'
    },
    'EXACT_ARCHIVE_FILE_INVENTORY'
)

need(
    not any(p.is_symlink() for p in A.rglob('*')),
    'ARCHIVE_SYMLINK'
)

for rel, expected in files.items():
    parts = pathlib.PurePosixPath(rel)

    need(
        not parts.is_absolute()
        and '..' not in parts.parts
        and len(expected) == 64,
        'PATH_OR_SHA'
    )

    if rel != 'README.md':
        need(
            len(parts.parts) == 3
            and parts.parts[0] in COUNTS,
            'PHASE_FILE_PATH'
        )

    need(
        hashed(A / rel) == expected,
        'FROZEN_SHA:' + rel
    )

    if rel.endswith(('.py', '.py.saved')):
        ast.parse(
            (A / rel).read_text(),
            filename=rel
        )
    elif rel.endswith('.json'):
        load(rel)
    else:
        need(
            rel == 'README.md',
            'UNEXPECTED_EXTENSION'
        )

need(
    hashed(
        R /
        'manifests/m2dgr_trajectory_manifest_v1_split_freeze_v1.json'
    ) == SPLIT,
    'FROZEN_SPLIT'
)

manifest_rel = (
    A / 'checkpoint_manifest_v1.json'
).relative_to(R).as_posix()

commit = subprocess.check_output(
    [
        'git', '-C', str(R),
        'rev-list', '-1', 'HEAD',
        '--', manifest_rel
    ],
    text=True
).strip()

if commit:
    parent = subprocess.check_output(
        [
            'git', '-C', str(R),
            'rev-parse', commit + '^'
        ],
        text=True
    ).strip()

    need(
        parent == BASE,
        'ARCHIVE_COMMIT_PARENT'
    )

docs = {
    'AGENTS.md',
    'docs/TRUST_ROBOT_PROJECT_STATE.md',
    'docs/audits/trust_robot/TRUST_ROBOT_KIOS_R33_R37_RECORDED_MOTION_V1.md'
}

need(
    set(m['documentation_sha256']) == docs,
    'DOCUMENT_INVENTORY'
)

for rel, expected in m['documentation_sha256'].items():
    if commit:
        raw = subprocess.check_output(
            [
                'git', '-C', str(R),
                'show', commit + ':' + rel
            ]
        )
    else:
        raw = (R / rel).read_bytes()

    need(
        sha(raw) == expected,
        'COMMIT_SCOPED_DOCUMENT:' + rel
    )

r37 = load(find(
    pins, 'r37_readiness_report_v1.json'
))
v37 = load(find(
    pins, 'r37_independent_validation_v1.json'
))

need(
    r37['schema'] ==
    'TRUST_ROBOT_R37_R33_R36_NONFACTOR_CHECKPOINT_READINESS_V1'
    and r37['readiness_decision'] ==
    'READY_FOR_SHA_PINNED_R33_R37_NONFACTOR_GITHUB_CHECKPOINT',
    'R37_READINESS'
)

need(
    r37['source_sha256'] == {
        key: value
        for key, value in pins.items()
        if not key.startswith('r37/')
    },
    'R37_21_FROZEN_BINDINGS'
)

need(
    v37['source_readiness_report_sha256'] ==
        hashed(item(pins, 'r37_readiness_report_v1.json'))
    and v37['source_artifacts_independently_hashed'] == 21
    and v37['science_gates_closed'] is True,
    'R37_INDEPENDENT'
)

need(
    r37['authenticated_bag_sha256'] == BAG
    and r37['trajectory_id'] == 'room_02'
    and r37['split'] == 'train',
    'R37_TRAIN_SCOPE'
)

zero(
    r37,
    (
        'scientific_pose_factors',
        'health_labels',
        'pose_accuracy_scores'
    ),
    'R37'
)

denied(
    r37,
    (
        'real_sensor_factor_execution_authorized',
        'health_model_training_authorized',
        'm2dgr_scoring_authorized',
        'physical_capture_time_verified',
        'cross_modal_alignment_performed',
        'full_extrinsics_verified',
        'statistical_stability_established',
        'raw_recording_modified',
        'github_modified'
    ),
    'R37'
)

r33 = load(find(
    pins, 'r33_camera_multipair_pixel_diagnostics_v1.json'
))
v33 = load(find(
    pins, 'r33_independent_validation_v1.json'
))
repair = load(find(
    pins, 'r33_failed_baseline_repair_provenance_v1.json'
))

r34 = load(find(
    pins, 'r34_imu_short_interval_diagnostics_v1.json'
))
v34 = load(find(
    pins, 'r34_independent_validation_v1.json'
))

r35 = load(find(
    pins, 'r35_imu_variation_frame_v1.json'
))
v35 = load(find(
    pins, 'r35_independent_validation_v1.json'
))

r36 = load(find(
    pins, 'r36_gyro_window_candidates_v1.json'
))
v36 = load(find(
    pins, 'r36_independent_validation_v1.json'
))

proofs = (
    (
        'R33', r33, v33,
        'r33_camera_multipair_pixel_diagnostics_v1.json',
        'source_report_sha256'
    ),
    (
        'R34', r34, v34,
        'r34_imu_short_interval_diagnostics_v1.json',
        'source_report_sha256'
    ),
    (
        'R35', r35, v35,
        'r35_imu_variation_frame_v1.json',
        'r35_report_sha256'
    ),
    (
        'R36', r36, v36,
        'r36_gyro_window_candidates_v1.json',
        'source_report_sha256'
    )
)

for phase, report, validation, filename, key in proofs:
    need(
        report['trajectory_id'] == 'room_02'
        and report['split'] == 'train'
        and report['authenticated_bag_sha256'] == BAG
        and report['github_baseline'] == BASE,
        'TRAIN_SCOPE:' + phase
    )

    need(
        validation[key] == hashed(item(pins, filename)),
        'INDEPENDENT_REPORT_HASH:' + phase
    )

    denied(
        report,
        (
            'physical_capture_time_verified',
            'cross_modal_alignment_performed',
            'full_extrinsics_verified',
            'real_sensor_factor_execution_authorized',
            'health_model_training_authorized',
            'm2dgr_scoring_authorized',
            'raw_recording_modified',
            'github_modified'
        ),
        phase
    )

    zero(
        report,
        (
            'real_pose_factors_generated',
            'health_labels_generated'
        ),
        phase
    )

need(
    r33['pair_count'] == 8
    and r33['frames_inspected'] == 16
    and len(r33['pairs']) == 8,
    'CAMERA_COUNT'
)

need(
    v33['recorded_camera_messages_verified'] == 16
    and v33['independently_recomputed_pair_tracks'] == 8
    and v33['r31_baseline_identical'] is True,
    'CAMERA_INDEPENDENT'
)

for pair in r33['pairs']:
    need(
        pair['metric_pose_qualified'] is False
        and pair['pixel_motion']['camera_pose_factor'] is None
        and pair['pixel_motion']['metric_translation_m'] is None,
        'CAMERA_NONFACTOR'
    )

need(
    repair['original_bag_modified'] is False
    and repair['git_modified'] is False
    and repair['real_pose_factors_authorized'] is False,
    'REPAIR_GATES'
)

for name in (
    'r33_camera_multipair.py',
    'r33_independent_verify.py'
):
    failed = name.replace(
        '.py',
        '_initial_failed_v1.py.saved'
    )

    row = repair['readers'][name]

    need(
        row['failed_sha256'] == hashed(item(pins, failed))
        and row['repaired_sha256'] == hashed(item(pins, name))
        and row['failed_backup'] == failed,
        'R33_FAILURE_REPAIR_PRESERVATION'
    )

need(
    r34['source_report_sha256']['r33'] ==
        hashed(item(
            pins,
            'r33_camera_multipair_pixel_diagnostics_v1.json'
        ))
    and v34['original_imu_messages_relocated'] == 32
    and v34['independent_trapezoid_intervals_recomputed'] == 16,
    'IMU_SHORT_INTERVAL_CHAIN'
)

need(
    r35['r34_source_report_sha256'] ==
        hashed(item(
            pins,
            'r34_imu_short_interval_diagnostics_v1.json'
        ))
    and r35['r34_independent_validation_sha256'] ==
        hashed(item(
            pins,
            'r34_independent_validation_v1.json'
        ))
    and v35['intervals_independently_recomputed'] == 16,
    'IMU_VARIATION_CHAIN'
)

need(
    r36['source_report_sha256']['r34'] ==
        hashed(item(
            pins,
            'r34_imu_short_interval_diagnostics_v1.json'
        ))
    and r36['source_report_sha256']['r35'] ==
        hashed(item(
            pins,
            'r35_imu_variation_frame_v1.json'
        ))
    and v36['authentic_imu_messages_relocated'] == 48
    and v36['independently_recomputed_three_sample_windows'] == 16,
    'SO3_CHAIN'
)

for topic, unknown, frame in (
    ('/camera/imu', 16, 'camera_imu_optical_frame'),
    ('/handsfree/imu', 0, 'base_link')
):
    need(
        len(r34['streams'][topic]) == 8
        and len(r35['streams'][topic]['intervals']) == 8
        and len(r36['streams'][topic]) == 8,
        'IMU_COUNTS'
    )

    need(
        r35['streams'][topic]['recorded_frame_id'] == frame
        and r35['streams'][topic]['summary'][
            'orientation_covariance_unknown_samples'
        ] == unknown,
        'IMU_FRAME_SEMANTICS'
    )

    for window in r36['streams'][topic]:
        need(
            window['physically_qualified_rotation'] is False
            and window['gyro_numerics']['factor'] is None
            and window['gyro_numerics']['translation_m'] is None,
            'GYRO_NONFACTOR'
        )

need(
    r37['observations'] == {
        'camera_pairs': 8,
        'camera_frames': 16,
        'imu_short_intervals': 16,
        'imu_short_messages': 32,
        'imu_gyro_windows': 16,
        'imu_gyro_messages': 48,
        'imu_gyro_intervals': 32
    },
    'READINESS_OBSERVATIONS'
)

print('R33_R37_ARCHIVE_STANDALONE_VERIFIER=PASS')
print('R33_R37_FROZEN_SHA256=26_VERIFIED')
print('R33_R37_R33_ORIGINAL_FAILURE_AND_REPAIR=PRESERVED')
print('R33_R37_CAMERA_AND_IMU_REPORT_LINEAGE=VERIFIED')
print('R33_R37_COMMIT_SCOPED_DOCS=VERIFIED')
print('R33_R37_RAW_BAG_COMMITTED=NO')
print('R33_R37_REAL_SENSOR_FACTORS_HEALTH_SCORING=DENIED')
