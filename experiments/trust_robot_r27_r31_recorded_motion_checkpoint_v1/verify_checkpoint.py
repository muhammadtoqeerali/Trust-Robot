"""No-bag R27-R31 SHA, provenance and scientific-gate verifier."""

import ast
import hashlib
import json
import math
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parents[1]

BASE = 'd1c8aa7811619d096865f9b5f23a0ca7e940fa81'
BAG = 'ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1'

COUNTS = {
    'r27': 5,
    'r28': 6,
    'r29': 4,
    'r30': 4,
    'r31': 4,
}

PINS = {
    'r27/r27_lidar_diagnostic_registration_v1.json':
        '9e3d5ea5488ca8ccd5274a9da8145f34f5f0e05514814c73591d1a3a31b3569e',
    'r27/r27_independent_validation_v1.json':
        'bfd6f5053b5ef1667cfba1445de6c0b0437fc66d538f9b6286ad3787b0dfbc8f',
    'r28/r28_lidar_sensitivity_v1.json':
        'c7c827996ac684addb86b6ed2b704fb57d38a43a2a3f76aa808193fa26f32658',
    'r28/r28_independent_validation_v1.json':
        'a2fe1c8a24d516f3271defa0cca3fe16d66c84de5921b716e2b7f443772f9d88',
    'r29/r29_lidar_multipair_diagnostics_v1.json':
        '5af225ff0ac9225fb16828a6ffacda4e1efcaddc69564f363095d8fe1071402b',
    'r29/r29_independent_validation_v1.json':
        'd1ccc46e81a83d0a7eb13a976286e3414d920dd0d86e1047d0f839c8fe29a978',
    'r30/r30_geometry_confidence_limits_v1.json':
        '373fe8993ccf6afa82bed9fd8f5197954e4b5412bc69d9558914dd08195d8f7d',
    'r30/r30_independent_validation_v1.json':
        'e41e59bbe240c927767b0b4dc906e2045d5db574c74559750a3cd0092491b471',
    'r31/r31_camera_pixel_motion_v1.json':
        'f04d6c1ecda049edea612dea9214ccb4c22355b37585e64a0a9169db8f355470',
    'r31/r31_independent_validation_v1.json':
        '068243ed843cba5b5a080821bec9296a017236a945de629a4a6827969d454f00',
}

def need(ok, reason):
    if not ok:
        raise ValueError('R32_VERIFICATION_DENIED:' + reason)

def sha(path):
    p = pathlib.Path(path)
    need(
        p.is_file()
        and not p.is_symlink()
        and p.stat().st_nlink == 1
        and 0 < p.stat().st_size <= 4_000_000,
        'UNSAFE_FILE:' + str(p)
    )
    return hashlib.sha256(p.read_bytes()).hexdigest()

def load(rel):
    return json.loads(
        (ROOT / rel).read_text(encoding='utf-8')
    )

def digest(rel):
    return sha(ROOT / rel)

def finite(x):
    return type(x) in (int, float) and math.isfinite(x)

def false_gates(obj, fields, prefix):
    for key in fields:
        need(obj.get(key) is False, prefix + ':' + key)

def zero_gates(obj, fields, prefix):
    for key in fields:
        need(
            type(obj.get(key)) is int and obj[key] == 0,
            prefix + ':' + key
        )

m = load('checkpoint_manifest_v1.json')

need(
    m['schema'] ==
    'TRUST_ROBOT_R27_R31_TRAIN_RECORDED_MOTION_CHECKPOINT_V1'
    and m['parent_commit'] == BASE
    and m['branch'] == 'kios-isaacsim-v15-integration',
    'MANIFEST_ID'
)

need(
    m['trajectory_id'] == 'room_02'
    and m['split'] == 'train'
    and m['authenticated_bag_sha256'] == BAG
    and m['bag_archived'] is False,
    'TRAIN_BAG'
)

need(
    set(m['phase_files']) == set(COUNTS)
    and len(m['frozen_sha256']) == 23,
    'PHASE_INVENTORY'
)

need(
    all(
        len(m['phase_files'][key]) == n
        for key, n in COUNTS.items()
    ),
    'PHASE_COUNTS'
)

members = set().union(
    *(set(m['phase_files'][key]) for key in COUNTS)
)

need(
    members == set(m['frozen_sha256']),
    'PHASE_MEMBERSHIP'
)

need(
    set(m['file_sha256'])
    == set(m['frozen_sha256']) | {'README.md'},
    'FILE_INVENTORY'
)

need(
    all(
        m['file_sha256'][k] == v
        for k, v in m['frozen_sha256'].items()
    ),
    'FROZEN_SHA_MAPPING'
)

need(
    all(m['frozen_sha256'].get(k) == v
        for k, v in PINS.items()),
    'INDEPENDENT_REPORT_PINS'
)

actual = {
    p.relative_to(ROOT).as_posix()
    for p in ROOT.rglob('*')
    if p.is_file()
}

need(
    actual == set(m['file_sha256']) |
    {'checkpoint_manifest_v1.json', 'verify_checkpoint.py'},
    'EXACT_ARCHIVE_FILES'
)

need(
    not any(p.is_symlink() for p in ROOT.rglob('*')),
    'SYMLINK'
)

for rel, expected in m['file_sha256'].items():
    pure = pathlib.PurePosixPath(rel)

    need(
        not pure.is_absolute()
        and '..' not in pure.parts
        and pure.suffix in ('.py', '.json', '.md')
        and re.fullmatch('[a-f0-9]{64}', expected),
        'FILE_PATH_OR_HASH'
    )

    need(digest(rel) == expected, 'SHA:' + rel)

    if rel.endswith('.py'):
        ast.parse((ROOT / rel).read_text(), filename=rel)
    elif rel.endswith('.json'):
        load(rel)

need(
    sha(REPO / 'manifests/m2dgr_trajectory_manifest_v1_split_freeze_v1.json')
    == m['frozen_split_sha256'],
    'FROZEN_SPLIT'
)

docs = {
    'AGENTS.md',
    'docs/TRUST_ROBOT_PROJECT_STATE.md',
    'docs/audits/trust_robot/TRUST_ROBOT_KIOS_R27_R31_RECORDED_MOTION_V1.md',
}

need(
    set(m['documentation_sha256']) == docs,
    'DOCUMENT_SET'
)

manifest_rel = (
    ROOT / 'checkpoint_manifest_v1.json'
).relative_to(REPO).as_posix()

commit = subprocess.check_output(
    ['git', '-C', str(REPO), 'rev-list', '-1',
     'HEAD', '--', manifest_rel],
    text=True
).strip()

if commit:
    parent = subprocess.check_output(
        ['git', '-C', str(REPO), 'rev-parse', commit + '^'],
        text=True
    ).strip()

    need(parent == BASE, 'COMMIT_PARENT')

for rel, expected in m['documentation_sha256'].items():
    if commit:
        contents = subprocess.check_output(
            ['git', '-C', str(REPO), 'show',
             commit + ':' + rel]
        )
    else:
        contents = (REPO / rel).read_bytes()

    need(
        hashlib.sha256(contents).hexdigest() == expected,
        'DOC_SHA:' + rel
    )

old = (
    REPO /
    'experiments/trust_robot_r17_r20_recorded_input_checkpoint_v1'
)

prior = (
    REPO /
    'experiments/trust_robot_r22_r25_recorded_diagnostics_checkpoint_v1'
)

need(
    sha(old / 'r17/r17_recorded_index.json') ==
    '4e904e29f507519e4447642edec55954b672aae2c305ff513bd6aa857c92a5af',
    'R17_FROZEN'
)

need(
    sha(old / 'r18/r18_bounded_recorded_samples.json') ==
    '68accc1d4ab7b4c131bd60767be249054ba2469fad266292f615b6619d969bfa',
    'R18_FROZEN'
)

need(
    sha(prior / 'r22/r22_recorded_content_diagnostics_v1.json') ==
    '5f6f3d4e9e3a8e7b49614a8a56ba1cd560d5ccc5b57eae397258f170f03ce849',
    'R22_FROZEN'
)

paths = [
    'r27/r27_lidar_diagnostic_registration_v1.json',
    'r27/r27_independent_validation_v1.json',
    'r28/r28_lidar_sensitivity_v1.json',
    'r28/r28_independent_validation_v1.json',
    'r29/r29_lidar_multipair_diagnostics_v1.json',
    'r29/r29_independent_validation_v1.json',
    'r30/r30_geometry_confidence_limits_v1.json',
    'r30/r30_independent_validation_v1.json',
    'r31/r31_camera_pixel_motion_v1.json',
    'r31/r31_independent_validation_v1.json',
]

(
    r27, v27, r28, v28, r29,
    v29, r30, v30, r31, v31
) = [load(path) for path in paths]

for name, report in (
    ('R27', r27), ('R28', r28), ('R29', r29),
    ('R30', r30), ('R31', r31)
):
    need(
        report.get('trajectory_id') == 'room_02'
        and report.get('split', 'train') == 'train',
        'TRAIN:' + name
    )

need(
    all(x['split'] == 'train' for x in (r29, r30, r31)),
    'EXPLICIT_TRAIN'
)

need(
    r29['authenticated_bag_sha256']
    == r30['authenticated_bag_sha256']
    == r31['bag_sha256']
    == BAG,
    'BAG_CHAIN'
)

need(
    r29['prior_reports_sha256'] == {
        'r17': sha(old / 'r17/r17_recorded_index.json'),
        'r18': sha(old / 'r18/r18_bounded_recorded_samples.json'),
        'r27': digest(paths[0]),
        'r28': digest(paths[2]),
    },
    'R29_LINEAGE'
)

need(
    r30['r17_sha256']
    == sha(old / 'r17/r17_recorded_index.json')
    and r30['r29_sha256'] == digest(paths[4]),
    'R30_LINEAGE'
)

need(
    r31['source_report_sha256'] == {
        'r17': sha(old / 'r17/r17_recorded_index.json'),
        'r18': sha(old / 'r18/r18_bounded_recorded_samples.json'),
        'r22': sha(
            prior / 'r22/r22_recorded_content_diagnostics_v1.json'
        ),
    },
    'R31_LINEAGE'
)

need(
    digest('r28/r28_r27_independent_replay_v1.json')
    == digest(paths[1]),
    'R28_R27_INDEPENDENT_REPLAY'
)

need(
    r29['pair_count'] == 8
    and r29['selected_unique_chunks'] == 16
    and r29['per_scan_selected_points'] == 512
    and r29['fixed_registration_iterations'] == 10
    and len(r29['pairs']) == 8,
    'R29_COUNTS'
)

need(
    [p['pair_index'] for p in r29['pairs']]
    == list(range(8))
    and len({
        s['chunk_offset']
        for p in r29['pairs']
        for s in p['scans']
    }) == 16,
    'R29_PAIRS'
)

for pair in r29['pairs']:
    need(
        len(pair['scans']) == 2
        and pair['registration'][
            'candidate_registered_as_factor'
        ] is False
        and pair['registration'][
            'independent_pose_accuracy_claimed'
        ] is False,
        'R29_PAIR_GATE'
    )

    need(
        pair['observed_header_gap_ns']
        == pair['scans'][1]['header_stamp_ns']
        - pair['scans'][0]['header_stamp_ns']
        > 0,
        'R29_HEADER_GAP'
    )

need(
    r30['pair_count'] == 8
    and r30['scans_considered'] == 16
    and r30['subset_size'] == 512
    and len(r30['pairs']) == 8,
    'R30_COUNTS'
)

for older, newer in zip(r29['pairs'], r30['pairs']):
    need(
        newer['source_message_sha256']
        == [
            s['serialized_message_sha256']
            for s in older['scans']
        ],
        'R30_SOURCE_LINK'
    )

    need(
        newer['forward_factor_admitted'] is False
        and newer['reverse_factor_admitted'] is False,
        'R30_FACTOR_DENIAL'
    )

    for key in (
        'roundtrip_translation_m',
        'roundtrip_rotation_deg'
    ):
        value = newer['inverse_consistency'][key]
        need(
            finite(value) and value >= 0,
            'R30_CLOSURE_METRIC'
        )

need(
    r31['frame_count'] == 2
    and r31['pair_count'] == 1
    and len(r31['frames']) == 2
    and r31['frames'][0]['sequence'] == 1085
    and r31['frames'][1]['sequence'] == 1086,
    'R31_FRAMES'
)

image_samples = json.loads(
    (
        old / 'r18/r18_bounded_recorded_samples.json'
    ).read_text()
)['samples']['/camera/color/image_raw/compressed']

need(
    [
        x['serialized_message_sha256']
        for x in r31['frames']
    ] == [
        x['serialized_message_sha256']
        for x in image_samples
    ],
    'R31_IMAGE_SOURCE'
)

tracking = r31['pixel_motion']

need(
    tracking['initial_corner_count'] == 400
    and tracking['forward_backward_consistent_count'] == 400
    and finite(tracking['median_displacement_px'])
    and tracking['median_displacement_px'] >= 0,
    'R31_TRACKS'
)

need(
    all(
        tracking.get(k) is None
        for k in (
            'metric_translation_m',
            'camera_rotation_radians',
            'camera_pose_factor',
        )
    ),
    'R31_NO_POSE'
)

for i, verification in (
    (29, v29), (30, v30), (31, v31)
):
    report_path = {
        29: paths[4],
        30: paths[6],
        31: paths[8],
    }[i]

    need(
        verification['source_report_sha256']
        == digest(report_path),
        'VALIDATION_LINK:' + str(i)
    )

need(
    v29['authenticated_lidar_messages_relocated'] == 16
    and v29['adjacent_pairs_verified'] == 8
    and v29['brute_force_registration_numeric_match'] is True,
    'R29_INDEPENDENT'
)

need(
    v30['original_lidar_messages_verified'] == 16
    and v30['independent_brute_force_registrations'] == 16
    and v30['bidirectional_roundtrips_verified'] == 8,
    'R30_INDEPENDENT'
)

need(
    v31['serialized_messages_verified'] == 2
    and v31['independent_lk_numeric_recomputation'] is True
    and v31['features_verified'] == 400
    and v31['forward_backward_consistent_tracks_verified'] == 400,
    'R31_INDEPENDENT'
)

need(
    r28['candidate_factors_admitted'] == 0
    and r28['relative_pose_accuracy_established'] is False,
    'R28_SCIENCE_GATE'
)

for report, keys, name in (
    (
        r29,
        (
            'physical_capture_time_verified',
            'cross_modal_alignment_performed',
            'full_extrinsics_verified',
            'independent_ground_truth_scored',
            'health_model_training_authorized',
            'real_sensor_factor_execution_authorized',
            'm2dgr_scoring_authorized',
            'pose_accuracy_established',
            'statistical_stability_established',
            'raw_recording_modified',
            'github_modified',
        ),
        'R29'
    ),
    (
        r30,
        (
            'physical_capture_time_verified',
            'cross_modal_alignment_performed',
            'full_extrinsics_verified',
            'independent_ground_truth_scored',
            'health_model_training_authorized',
            'real_sensor_factor_execution_authorized',
            'm2dgr_scoring_authorized',
            'pose_accuracy_established',
            'statistical_stability_established',
            'raw_recording_modified',
            'github_modified',
        ),
        'R30'
    ),
    (
        r31,
        (
            'metric_scale_established',
            'six_dof_pose_estimated',
            'physical_capture_time_verified',
            'cross_modal_alignment_performed',
            'full_extrinsics_verified',
            'ground_truth_scored',
            'health_model_training_authorized',
            'real_sensor_factor_execution_authorized',
            'm2dgr_scoring_authorized',
            'raw_recording_modified',
            'github_modified',
        ),
        'R31'
    ),
):
    false_gates(report, keys, name)

for report, name in (
    (r29, 'R29'), (r30, 'R30'), (r31, 'R31')
):
    zero_gates(
        report,
        ('real_pose_factors_generated', 'health_labels_generated'),
        name
    )

for field in (
    'real_sensor_factor_execution_authorized',
    'health_model_training_authorized',
    'm2dgr_scoring_authorized',
    'physical_capture_sync_verified',
    'full_extrinsics_verified',
):
    need(m[field] is False, 'MANIFEST_GATE:' + field)

zero_gates(
    m,
    ('scientific_pose_factors', 'health_labels'),
    'MANIFEST'
)

print('R27_R31_ARCHIVE_STANDALONE_VERIFIER=PASS')
print('R27_R31_FROZEN_ARTIFACT_SHA256=23_VERIFIED')
print('R27_R31_SOURCE_REPORT_LINEAGE=VERIFIED')
print('R27_R31_LIDAR_EIGHT_PAIRS_AND_CAMERA_TWO_FRAMES=VERIFIED')
print('R27_R31_DOCUMENTATION_COMMIT_SCOPED_SHA=VERIFIED')
print('R27_R31_RAW_ROSBAG_IN_ARCHIVE=NO')
print('R27_R31_REAL_POSE_FACTORS_AND_HEALTH_TRAINING=DENIED')
