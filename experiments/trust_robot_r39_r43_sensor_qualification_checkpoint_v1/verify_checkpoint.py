"""Independent fail-closed R39–R43 archive verifier. No raw bag required."""

import ast
import hashlib
import json
import pathlib
import subprocess

A = pathlib.Path(__file__).resolve().parent
R = A.parents[1]

BASE = 'df78336320b3b026e448a09d39dfc571f922ae00'
BAG = 'ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1'
SPLIT = '017a388ef1ce4ad30812669632a022ca37c084871bc949693fd9c0541014238f'

COUNTS = {'r39':6, 'r40':8, 'r41':6, 'r42':6, 'r43':7}

def need(ok, reason):
    if not ok:
        raise ValueError('R44_ARCHIVE_DENIED:' + reason)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def read(path):
    return json.loads(pathlib.Path(path).read_text())

def verified_sha(path):
    need(
        path.is_file() and not path.is_symlink()
        and path.stat().st_nlink == 1
        and 0 < path.stat().st_size < 4000000,
        'UNSAFE_FILE:' + str(path)
    )
    return sha(path.read_bytes())

def item(pins, filename):
    candidates = [
        name for name in pins
        if name.endswith('/' + filename)
    ]
    need(len(candidates) == 1, 'UNIQUE_FILE:' + filename)
    return A / candidates[0]

def denied(record, keys, label):
    for key in keys:
        need(record.get(key) is False, label + ':' + key)

def zero(record, keys, label):
    for key in keys:
        need(
            type(record.get(key)) is int and record[key] == 0,
            label + ':' + key
        )

manifest = read(A/'checkpoint_manifest_v1.json')

need(
    manifest.get('schema') ==
    'TRUST_ROBOT_R39_R43_SENSOR_QUALIFICATION_CHECKPOINT_V1'
    and manifest.get('parent_commit') == BASE
    and manifest.get('branch') == 'kios-isaacsim-v15-integration',
    'MANIFEST'
)

need(
    manifest.get('trajectory_id') == 'room_02'
    and manifest.get('split') == 'train'
    and manifest.get('bag_sha256') == BAG
    and manifest.get('split_manifest_sha256') == SPLIT,
    'SOURCE_SCOPE'
)

need(
    manifest.get('phase_counts') == COUNTS
    and manifest.get('raw_bag_in_archive') is False
    and manifest.get('confirmation_test_accessed') is False,
    'CHECKPOINT_SCOPE'
)

zero(
    manifest,
    ('real_pose_factors_generated',
     'health_labels_generated',
     'ate_rpe_scores_generated'),
    'MANIFEST'
)

denied(
    manifest,
    ('physical_capture_clock_qualified',
     'sensor_extrinsics_qualified',
     'mocap_reference_qualified',
     'health_training_authorized',
     'real_sensor_factors_authorized',
     'm2dgr_scoring_authorized'),
    'MANIFEST'
)

pins = manifest['artifact_sha256']
files = manifest['file_sha256']

need(
    len(pins) == 33 and len(files) == 34
    and set(files) == set(pins) | {'README.md'},
    'FILE_COUNTS'
)

need(
    all(files.get(key) == value for key, value in pins.items()),
    'FILE_PINS'
)

need(
    {
        phase: sum(key.startswith(phase+'/') for key in pins)
        for phase in COUNTS
    } == COUNTS,
    'PHASE_COUNTS'
)

need(
    not any(path.is_symlink() for path in A.rglob('*')),
    'SYMLINK_FOUND'
)

actual = {
    path.relative_to(A).as_posix()
    for path in A.rglob('*') if path.is_file()
}

need(
    actual == set(files) | {
        'checkpoint_manifest_v1.json',
        'verify_checkpoint.py'
    },
    'EXACT_ARCHIVE_FILE_INVENTORY'
)

for relative, expected in files.items():
    parts = pathlib.PurePosixPath(relative)

    need(
        not parts.is_absolute()
        and '..' not in parts.parts
        and len(expected) == 64,
        'FILE_PATH'
    )

    if relative != 'README.md':
        need(
            len(parts.parts) == 3
            and parts.parts[0] in COUNTS,
            'PHASE_PATH'
        )

    path = A / relative
    need(verified_sha(path) == expected, 'FILE_SHA:' + relative)

    if relative.endswith(('.py', '.py.saved')):
        ast.parse(path.read_bytes(), filename=relative)
    elif relative.endswith('.json'):
        read(path)
    else:
        need(relative.endswith('.md'), 'FILE_EXTENSION')

need(
    verified_sha(
        R/'manifests/m2dgr_trajectory_manifest_v1_split_freeze_v1.json'
    ) == SPLIT,
    'SPLIT_FREEZE'
)

# Before commit: verify worktree docs.
# After commit: verify those exact docs from the archived commit.
manifest_path = (
    A/'checkpoint_manifest_v1.json'
).relative_to(R).as_posix()

commit = subprocess.check_output([
    'git','-C',str(R),'rev-list','-1','HEAD','--',manifest_path
], text=True).strip()

if commit:
    parent = subprocess.check_output([
        'git','-C',str(R),'rev-parse',commit+'^'
    ], text=True).strip()
    need(parent == BASE, 'ARCHIVE_COMMIT_PARENT')

expected_docs = {
    'AGENTS.md',
    'docs/TRUST_ROBOT_PROJECT_STATE.md',
    'docs/audits/trust_robot/TRUST_ROBOT_KIOS_R39_R43_SENSOR_QUALIFICATION_V1.md'
}

need(
    set(manifest['documentation_sha256']) == expected_docs,
    'DOCUMENT_INVENTORY'
)

for relative, expected in manifest['documentation_sha256'].items():
    if commit:
        contents = subprocess.check_output([
            'git','-C',str(R),'show',commit+':'+relative
        ])
    else:
        contents = (R/relative).read_bytes()

    need(sha(contents) == expected, 'DOCUMENT_SHA:' + relative)

r39 = read(item(pins,'r39_qualification_evidence_v1.json'))
v39 = read(item(pins,'r39_independent_validation_v1.json'))

r40 = read(item(pins,'r40_local_asset_inventory_v1.json'))
v40 = read(item(pins,'r40_independent_validation_v1.json'))

r41 = read(item(pins,'r41_calibration_candidate_semantics_v1.json'))
v41 = read(item(pins,'r41_independent_validation_v1.json'))

r42 = read(item(pins,'r42_connection_calibration_gap_v1.json'))
v42 = read(item(pins,'r42_independent_validation_v1.json'))

r43 = read(item(pins,'r43_calibration_reference_acquisition_protocol_v1.json'))
v43 = read(item(pins,'r43_independent_validation_v1.json'))

receipts = read(item(pins,'r43_unfilled_source_receipts_v1.json'))
repair = read(item(pins,'r40_failed_manifest_field_repair_v1.json'))

proofs = (
    (r39,v39,'r39_qualification_evidence_v1.json','source_report_sha256'),
    (r40,v40,'r40_local_asset_inventory_v1.json','source_report_sha256'),
    (r41,v41,'r41_calibration_candidate_semantics_v1.json','r41_report_sha256'),
    (r42,v42,'r42_connection_calibration_gap_v1.json','source_report_sha256'),
    (r43,v43,'r43_calibration_reference_acquisition_protocol_v1.json','r43_protocol_sha256')
)

for source, validation, filename, key in proofs:
    need(
        validation[key] == verified_sha(item(pins,filename)),
        'INDEPENDENT_PROOF:' + filename
    )

need(
    all(
        source['trajectory_id'] == 'room_02'
        and source['split'] == 'train'
        for source in (r39,r40,r41,r42,r43)
    ),
    'TRAIN_ONLY'
)

need(
    all(
        source['github_baseline'] == BASE
        for source in (r39,r40,r41,r42,r43)
    ),
    'GITHUB_BASELINE'
)

need(
    r39['authenticated_bag_sha256']
    == r40['source_bag_sha256']
    == r41['source_bag_sha256']
    == r42['source_bag_sha256']
    == r43['bag_sha256']
    == BAG,
    'SOURCE_BAG_BINDING'
)

need(
    r39['decision'] ==
    'DIAGNOSTICS_VERIFIED_QUALIFIED_REAL_FACTORS_BLOCKED'
    and len(r39['qualification_gates']) == 9
    and all(
        item['status'] == 'NOT_QUALIFIED'
        for item in r39['qualification_gates'].values()
    ),
    'R39_QUALIFICATION'
)

zero(
    r39,
    ('scientific_pose_factors','health_labels','ate_rpe_scores'),
    'R39'
)

need(
    v39['authenticated_frozen_reports_verified'] == 7
    and v39['scientific_factor_admission'] is False,
    'R39_INDEPENDENT'
)

need(
    len(r40['candidate_files']) == 10
    and r40['room_02_reference_provenance'][
        'rotation_invalid_count'
    ] == 90
    and all(
        x['status'] == 'UNVERIFIED'
        for x in r40['qualification_requirements'].values()
    ),
    'R40_INVENTORY'
)

need(
    len(r40['recorded_stream_clock_domains']) == 4
    and r40['existing_reference_semantics'][
        'mocap_reference_body_origin_verified'
    ] is False,
    'R40_MOCAP_FIELD'
)

need(
    v40['repository_manifest_git_snapshots_verified'] == 11
    and v40['local_candidate_files_verified'] == 10,
    'R40_INDEPENDENT'
)

need(
    repair['schema'] ==
    'TRUST_ROBOT_R40_CANONICAL_MOCAP_FIELD_REPAIR_V1'
    and repair['failure'] ==
    'KeyError: mocap_body_origin_verified',
    'R40_REPAIR'
)

need(
    repair['original_source_sha256'] ==
        verified_sha(item(pins,'r40_inventory_initial_failed_v1.py.saved'))
    and repair['repaired_source_sha256'] ==
        verified_sha(item(pins,'r40_inventory.py')),
    'R40_FAILED_AND_REPAIRED_SHA'
)

denied(
    repair,
    ('recording_modified','github_modified',
     'sensor_factor_admission_authorized'),
    'R40_REPAIR'
)

need(
    r41['r40_report_sha256'] ==
        verified_sha(item(pins,'r40_local_asset_inventory_v1.json'))
    and r41['r40_independent_sha256'] ==
        verified_sha(item(pins,'r40_independent_validation_v1.json'))
    and r41['r39_report_sha256'] ==
        verified_sha(item(pins,'r39_qualification_evidence_v1.json')),
    'R41_SOURCE_CHAIN'
)

need(
    len(r41['configuration_semantics']) == 10
    and r41['config_role_counts'] == {
        'trust_robot_software_contracts': 4,
        'separate_software_protocols': 6
    }
    and len(r41['room_02_reference_file_candidates']) == 0
    and r41['matching_frozen_reference_payload_count'] == 0,
    'R41_EVIDENCE'
)

need(
    v41['git_commit_identical_configs'] == 10
    and v41['physical_calibration_qualified'] is False,
    'R41_INDEPENDENT'
)

need(
    r42['source_sha256']['r40'] ==
        verified_sha(item(pins,'r40_local_asset_inventory_v1.json'))
    and r42['source_sha256']['r41'] ==
        verified_sha(item(pins,'r41_calibration_candidate_semantics_v1.json')),
    'R42_SOURCE_CHAIN'
)

need(
    r42['connection_count'] == 15
    and len(r42['connections']) == 15
    and r42['sensor_messages_decoded'] == 0
    and r42['sensor_payload_decompressed'] is False,
    'R42_ROS_METADATA'
)

need(
    r42['camera_info_topic_count'] == 0
    and r42['tf_topic_count'] == 0
    and r42['mocap_or_pose_reference_topic_count'] == 0
    and len(r42['unresolved_requirements']) == 11,
    'R42_CALIBRATION_GATES'
)

need(
    v42['independently_parsed_original_connection_headers'] == 15
    and v42['sensor_payload_decompressed'] is False,
    'R42_INDEPENDENT'
)

upstream = {
    'r39': verified_sha(item(pins,'r39_qualification_evidence_v1.json')),
    'r40': verified_sha(item(pins,'r40_local_asset_inventory_v1.json')),
    'r41': verified_sha(item(pins,'r41_calibration_candidate_semantics_v1.json')),
    'r42': verified_sha(item(pins,'r42_connection_calibration_gap_v1.json')),
    'r42_independent': verified_sha(item(pins,'r42_independent_validation_v1.json'))
}

need(
    r43['upstream_report_sha256'] == upstream,
    'R43_UPSTREAM'
)

need(
    len(r43['frozen_manifest_sha256']) == 10
    and r43['split_manifest_sha256'] == SPLIT,
    'R43_FROZEN_MANIFESTS'
)

for name, expected in r43['frozen_manifest_sha256'].items():
    source = subprocess.check_output([
        'git','-C',str(R),'show',BASE+':manifests/'+name
    ])
    need(sha(source) == expected, 'R43_FROZEN_SOURCE:' + name)

need(
    r43['source_acquisition_status'] == 'NOT_ACQUIRED'
    and r43['unresolved_gate_count'] == 11
    and r43['room_02_reference_invalid_rotations'] == 90,
    'R43_SCIENCE'
)

need(
    r43['existing_d435i_relative_rotation_content_support'] is True
    and r43['full_extrinsic_from_partial_rotation'] is False
    and r43['reference_to_lidar_transform_known'] is False,
    'R43_PARTIAL_EXTRINSIC'
)

need(
    receipts['schema'] ==
    'TRUST_ROBOT_R43_EMPTY_EVIDENCE_RECEIPTS_V1'
    and receipts['source_data_present'] is False
    and set(receipts['gate_receipts']) == set(r43['requests']),
    'R43_RECEIPTS'
)

for gate, receipt in receipts['gate_receipts'].items():
    need(
        receipt['status'] == 'NO_SOURCE_RECEIVED'
        and receipt['source_uri'] is None
        and receipt['source_sha256'] is None
        and receipt['independent_validation_sha256'] is None
        and receipt['physical_qualification_authorized'] is False,
        'R43_EMPTY_RECEIPT:' + gate
    )
    need(
        all(x is None for x in receipt['required_fields'].values())
        and set(receipt['required_fields'])
            == set(r43['requests'][gate]['required_evidence_fields']),
        'R43_EMPTY_FIELDS:' + gate
    )
    need(
        r43['requests'][gate]['status'] == 'NOT_QUALIFIED'
        and r43['requests'][gate][
            'physical_validation_completed'
        ] is False,
        'R43_UNQUALIFIED_GATE:' + gate
    )

need(
    v43['commit_frozen_manifests_verified'] == 10
    and v43['prior_artifacts_verified'] == 5
    and v43['missing_evidence_gates_verified'] == 11
    and v43['nonempty_source_receipts'] == 0,
    'R43_INDEPENDENT'
)

for name, source, flags in (
    ('R40',r40,(
        'raw_bag_opened','confirmation_test_accessed',
        'github_modified','m2dgr_scoring_authorized')),
    ('R41',r41,(
        'raw_bag_opened','confirmation_test_payload_accessed',
        'github_modified','physical_calibration_admitted',
        'reference_scoring_authorized')),
    ('R42',r42,(
        'confirmation_test_accessed','github_modified')),
    ('R43',r43,(
        'raw_bag_opened','confirmation_test_accessed',
        'github_modified','real_sensor_factors_authorized',
        'health_training_authorized','m2dgr_ate_rpe_authorized'))
):
    denied(source, flags, name)

zero(r40,('qualified_real_sensor_factors','health_labels'),'R40')
zero(r41,('qualified_pose_factors','health_labels','ate_rpe_scores'),'R41')
zero(r42,('qualified_pose_factors','health_labels','ate_rpe_scores'),'R42')
zero(r43,(
    'qualified_pose_factors','health_labels',
    'ate_rpe_scores','external_sources_acquired'
),'R43')

print('R39_R43_ARCHIVE_STANDALONE_VERIFIER=PASS')
print('R39_R43_FROZEN_ARTIFACT_SHA256=33_VERIFIED')
print('R39_R43_R40_FAILED_AND_REPAIRED_SOURCES=PRESERVED')
print('R39_R43_INDEPENDENT_REPORT_LINEAGE=5_VERIFIED')
print('R39_R43_GIT_MANIFEST_RECEIPTS=10_VERIFIED')
print('R39_R43_UNFILLED_SOURCE_RECEIPTS=11')
print('R39_R43_COMMIT_SCOPED_DOCUMENTATION=VERIFIED')
print('R39_R43_RAW_BAG_ARCHIVED=NO')
print('R39_R43_REAL_FACTORS_HEALTH_SCORING=DENIED')
