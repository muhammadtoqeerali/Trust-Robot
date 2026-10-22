"""R92 read-only physical qualification decision from frozen Git evidence.

No raw dataset reads, clocks fitted, new source admissions, or gate upgrades.
"""

import hashlib
import json
import pathlib
import subprocess

SCHEMA = 'TRUST_ROBOT_R92_PHYSICAL_SOURCE_QUALIFICATION_GAP_V1'
PARENT = '8b6024cc7c09568fc1e5485abdc0a5aa2bb72cd9'

ROOT43 = 'experiments/trust_robot_r39_r43_sensor_qualification_checkpoint_v1/r43/trust_robot_r43_source_acquisition_protocol_result_v1/'
ROOT53 = 'experiments/trust_robot_r51_r55f_evidence_checkpoint_v1/evidence/trust_robot_r53_timing_receipt_boundary_result_v1/'
ROOT68 = 'experiments/trust_robot_r64_r68_original_gt_recovery_checkpoint_v1/evidence/r68/result/'
ROOT74 = 'experiments/trust_robot_r70_r74_scientific_admissibility_checkpoint_v1/evidence/result/'
ROOT76 = 'experiments/trust_robot_r76_r78_physical_intake_runtime_checkpoint_v1/evidence/'

SOURCES = {
    'r43': ROOT43 + 'r43_unfilled_source_receipts_v1.json',
    'r53': ROOT53 + 'r53_unfilled_physical_timing_receipts_v1.json',
    'r68': ROOT68 + 'r68_physical_gate_reconciliation_v1.json',
    'r74': ROOT74 + 'r74_scientific_admissibility_v1.json',
    'r76': ROOT76 + 'r76/result/r76_source_intake_contract_v1.json',
    'r77': ROOT76 + 'r77/result/r77_intake_sensor_factor_boundary_v1.json',
    'r78': ROOT76 + 'r78/result/r78_runtime_boundary_decision_v1.json',
    'r87_manifest':
        'experiments/trust_robot_r84_r86_synthetic_inertial_rolling_checkpoint_v1/checkpoint_manifest_v1.json',
    'r91_manifest':
        'experiments/trust_robot_r88_r90_schur_prior_checkpoint_v1/checkpoint_manifest_v1.json',
    'sync_doc':
        'docs/audits/trust_robot/M2DGR_PHASE3B_SYNCHRONIZATION_EVIDENCE.md',
    'camera_doc':
        'docs/audits/trust_robot/M2DGR_PHASE3C_CAMERA_IMU_SYNCHRONIZATION_EVIDENCE.md',
    'lidar_doc':
        'docs/audits/trust_robot/M2DGR_PHASE3D_LIDAR_IMU_SYNCHRONIZATION_EVIDENCE.md',
    'calibration_doc':
        'docs/audits/trust_robot/M2DGR_CALIBRATION_EVIDENCE.md'
}

GATE_NAMES = {
    'camera_imu_extrinsics_physically_verified',
    'camera_intrinsics_physically_verified',
    'camera_lidar_extrinsics_physically_verified',
    'cross_sensor_synchronization_physically_verified',
    'health_training_authorized',
    'm2dgr_ate_rpe_authorized',
    'metric_visual_pose_authorized',
    'mocap_body_to_lidar_physically_verified',
    'raw_reference_available_locally',
    'real_sensor_factors_authorized',
    'reference_capture_clock_physically_verified'
}

TIMING_NAMES = {
    'camera_color',
    'camera_imu',
    'handsfree_imu',
    'mocap_reference',
    'velodyne_lidar'
}

class EvidenceError(ValueError):
    pass

def need(value, reason):
    if not value:
        raise EvidenceError(reason)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(value):
    return (
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False)
        + '\n'
    ).encode()

def load(repo):
    """Read 13 named tracked files, compare against the actual Git blobs."""

    repo = pathlib.Path(repo)
    records = {}
    pins = {}

    for name, relative in SOURCES.items():
        path = repo / relative

        need(path.is_file() and not path.is_symlink(),
             'SOURCE_MISSING:' + name)

        raw = path.read_bytes()

        need(0 < len(raw) < 2_000_000, 'SOURCE_SIZE:' + name)

        expected = subprocess.check_output([
            'git', '-C', str(repo),
            'show', 'HEAD:' + relative
        ])

        need(raw == expected, 'GIT_BLOB_CHANGED:' + name)

        pins[name] = {
            'repo_relative_path': relative,
            'sha256': sha(raw)
        }

        records[name] = (
            raw.decode('utf-8')
            if name.endswith('_doc')
            else json.loads(raw)
        )

    return records, pins

def analyze(d, pins):
    r43, r53, r68, r74 = (
        d[k] for k in ('r43','r53','r68','r74')
    )
    r76, r77, r78 = (
        d[k] for k in ('r76','r77','r78')
    )

    need(set(pins) == set(SOURCES), 'SOURCE_SET')

    need(
        r43.get('schema') == 'TRUST_ROBOT_R43_EMPTY_EVIDENCE_RECEIPTS_V1'
        and set(r43['gate_receipts']) == GATE_NAMES
        and r43['source_data_present'] is False,
        'HISTORICAL_R43'
    )

    need(
        r53.get('schema') == 'TRUST_ROBOT_R53_UNFILLED_PHYSICAL_SOURCE_RECEIPTS_V1'
        and set(r53['receipts']) == TIMING_NAMES
        and r53['source_data_present'] is False,
        'HISTORICAL_R53'
    )

    for name, receipt in r43['gate_receipts'].items():
        need(
            receipt['status'] == 'NO_SOURCE_RECEIVED'
            and receipt['physical_qualification_authorized'] is False
            and receipt['source_sha256'] is None
            and receipt['independent_validation_sha256'] is None
            and type(receipt['required_fields']) is dict
            and len(receipt['required_fields']) > 0
            and all(v is None for v in receipt['required_fields'].values()),
            'R43_UNFILLED:' + name
        )

    for name, receipt in r53['receipts'].items():
        need(
            receipt['status'] == 'NO_PHYSICAL_SOURCE_RECEIVED'
            and receipt['independently_validated'] is False
            and receipt['physical_measurement_qualified'] is False
            and type(receipt['fields']) is dict
            and len(receipt['fields']) >= 10
            and all(v is None for v in receipt['fields'].values()),
            'R53_UNFILLED:' + name
        )

    need(
        r68.get('schema') ==
            'TRUST_ROBOT_R68_RECOVERED_GT_PHYSICAL_GATE_RECONCILIATION_V1'
        and r68['scientific_gates_closed'] == 11
        and r68['raw_reference_access_question_resolved_locally'] is True
        and r68['dataset_bytes_recovered_and_verified'] is True
        and r68['raw_reference_complete_scientific_qualification'] is False
        and r68['invalid_rotation_count'] == 90
        and r68['reference_sample_count'] == 3831
        and r68['gt_file_size_bytes'] == 504403
        and r68['invalid_quaternions_repaired'] is False,
        'R68_GT_RECOVERY_DISTINCTION'
    )

    need(
        r68['source_receipt_sha256']['r43'] == pins['r43']['sha256']
        and r68['source_receipt_sha256']['r53'] == pins['r53']['sha256'],
        'R68_R43_R53_LINEAGE'
    )

    need(
        r74.get('schema') ==
            'TRUST_ROBOT_R74_SANITIZED_EVIDENCE_DECISION_V1'
        and r74['scientific_gates_closed'] == 11
        and r74['historical_gt_sha256'] == r68['gt_sha256']
        and r74['structurally_invalid_rotations'] == 90
        and r74['author_calibration_explicit_mocap_terms'] == 0
        and all(x is False for x in r74['physical_qualification'].values()),
        'R74_PHYSICAL_DECISIONS'
    )

    need(
        r76.get('schema') ==
            'TRUST_ROBOT_R76_PHYSICAL_SOURCE_INTAKE_CONTRACT_V1'
        and r76['scientific_gates_closed'] == 11
        and r76['independent_new_sources_qualified'] == 0
        and r76['new_execution_authorizations'] == 0
        and r76['historical_r43_raw_gt_status_not_current'] is True
        and r76['original_room_02_gt_recovered_in_later_phase'] is True
        and set(r76['historical_r43_gates']) == GATE_NAMES
        and set(r76['historical_r53_receipts']) == TIMING_NAMES,
        'R76_LATEST_INTAKE'
    )

    need(
        r76['frozen_evidence_sha256']['r43'] == pins['r43']['sha256']
        and r76['frozen_evidence_sha256']['r53'] == pins['r53']['sha256']
        and r76['frozen_evidence_sha256']['r74'] == pins['r74']['sha256'],
        'R76_SOURCE_LINEAGE'
    )

    need(
        r77.get('status') == 'PASS_SOFTWARE_ONLY'
        and r77['scientific_gates_closed'] == 11
        and r77['new_physical_evidence_received'] is False
        and r77['m2dgr_sensor_admission_gate_rejected'] is True
        and r77['multimodal_recorded_factor_gate_rejected'] is True,
        'R77_FACTOR_DENIAL'
    )

    need(
        r78.get('status') == 'PASS_SOFTWARE_ONLY'
        and r78['scientific_gates_closed'] == 11
        and r78['runtime_authorizations'] == 0
        and r78['physically_qualified_sources'] == 0
        and r78['historical_timing_receipts'] == 5
        and r78['apparently_filled_author_like_cases_denied'] == 11,
        'R78_RUNTIME_DENIAL'
    )

    for phase in ('r87_manifest', 'r91_manifest'):
        need(
            d[phase].get('source_count') == 12
            and d[phase].get('scientific_gates_closed') == 11,
            'RECENT_CHECKPOINT:' + phase
        )

    need(
        d['r91_manifest']['schema'] ==
            'TRUST_ROBOT_R88_R90_SCHUR_PRIOR_CHECKPOINT_V1',
        'R91_MANIFEST'
    )

    need(
        'Calibration verification remains incomplete.'
        in d['calibration_doc'],
        'CALIBRATION_DOCUMENT'
    )

    need(
        'synchronization remains unverified'
        in d['sync_doc'],
        'CLOCK_DOCUMENT'
    )

    need(
        'physical capture synchronization remains unverified'
        in d['camera_doc']
        and 'physical capture synchronization remains unverified'
        in d['lidar_doc'],
        'CAPTURE_DOCUMENTS'
    )

    gates = {}

    for name, receipt in sorted(r43['gate_receipts'].items()):
        legacy = receipt['status']

        current_interpretation = (
            'LOCAL_BYTES_RECOVERED; FULL_PHYSICAL_QUALIFICATION_INCOMPLETE'
            if name == 'raw_reference_available_locally'
            else 'NOT_INDEPENDENTLY_QUALIFIED'
        )

        gates[name] = {
            'historical_receipt_status': legacy,
            'latest_supported_interpretation': current_interpretation,
            'historical_required_fields':
                sorted(receipt['required_fields']),
            'physical_gate_authorized': False,
            'origin_record': 'r43',
            'later_state_records': ['r68','r74','r76','r77','r78']
        }

    timing = {}

    for name, receipt in sorted(r53['receipts'].items()):
        timing[name] = {
            'historical_status': receipt['status'],
            'missing_receipt_fields': sorted(receipt['fields']),
            'physical_capture_time_qualified': False,
            'origin_record': 'r53'
        }

    actions = [
        {
            'priority': 1,
            'task': 'Obtain independently checkable capture-event and clock-mapping receipts for five streams',
            'receipt_sources': sorted(TIMING_NAMES),
            'gate_dependencies': [
                'cross_sensor_synchronization_physically_verified',
                'reference_capture_clock_physically_verified'
            ],
            'requires_new_external_or_independent_physical_evidence': True
        },
        {
            'priority': 2,
            'task': 'Identify tracked mocap rigid-body origin and measured mocap-to-LiDAR SE3 transform with direction, units and validation',
            'gate_dependencies': [
                'mocap_body_to_lidar_physically_verified'
            ],
            'requires_new_external_or_independent_physical_evidence': True
        },
        {
            'priority': 3,
            'task': 'Independently qualify camera intrinsics, camera-to-IMU and camera-to-LiDAR extrinsics, including applicable sensor frames',
            'gate_dependencies': [
                'camera_intrinsics_physically_verified',
                'camera_imu_extrinsics_physically_verified',
                'camera_lidar_extrinsics_physically_verified'
            ],
            'requires_new_external_or_independent_physical_evidence': True
        },
        {
            'priority': 4,
            'task': 'Predeclare how 90 invalid GT rotations and discontinuous reference coverage will be handled; verify temporal association and evaluation protocol',
            'gate_dependencies': [
                'raw_reference_available_locally',
                'm2dgr_ate_rpe_authorized'
            ],
            'requires_new_external_or_independent_physical_evidence': True
        },
        {
            'priority': 5,
            'task': 'Only after independent qualifications, review measured factors, metric visual pose and scientifically justified health training',
            'gate_dependencies': [
                'metric_visual_pose_authorized',
                'real_sensor_factors_authorized',
                'health_training_authorized'
            ],
            'requires_new_external_or_independent_physical_evidence': True
        }
    ]

    need(
        {x for action in actions for x in action['gate_dependencies']}
        == GATE_NAMES,
        'ACTION_GATE_COVERAGE'
    )

    return {
        'schema': SCHEMA,
        'status': 'PASS_EXISTING_EVIDENCE_GAP_ANALYSIS_ONLY',
        'git_parent': PARENT,
        'source_files_sha256': pins,
        'tracked_evidence_files_read': len(SOURCES),
        'historical_unfilled_gate_receipts': len(gates),
        'historical_unfilled_timing_receipts': len(timing),
        'new_physically_qualified_sources_established': 0,
        'gate_matrix': gates,
        'timing_receipt_matrix': timing,
        'reference_recovery': {
            'trajectory': 'room_02',
            'gt_sha256': r68['gt_sha256'],
            'gt_size_bytes': r68['gt_file_size_bytes'],
            'gt_samples': r68['reference_sample_count'],
            'invalid_rotation_records': 90,
            'raw_gt_bytes_recovered_locally': True,
            'reference_physically_qualified': False,
            'invalid_rotations_repaired_or_imputed': False
        },
        'source_provenance': {
            'author_calibration_has_explicit_mocap_terms': False,
            'historical_author_like_candidates_qualified': 0,
            'physical_capture_clock_mapping_qualified': False
        },
        'priority_actions': actions,
        'raw_rosbags_or_gt_opened_during_r92': False,
        'new_external_evidence_received_during_r92': False,
        'author_request_sent_during_r92': False,
        'real_sensor_factors_authorized': False,
        'health_training_authorized': False,
        'ate_rpe_authorized': False,
        'confirmation_test_accessed': False,
        'scientific_gates_closed': 11
    }

def markdown(report):
    text = [
        '# R92 physical-source qualification: what is still missing',
        '',
        'Status: evidence-gap decision only. Nothing was physically requalified.',
        '',
        '## Findings',
        '',
        '- Eleven original scientific receipts remain historically unfilled; no later authorization was established.',
        '- Five sensor capture-time receipts remain historically unfilled.',
        '- Original room_02 GT bytes were recovered locally; access is resolved, but reference-frame/time/quality qualification is NOT.',
        '- The recovered reference has 3,831 records, including 90 structurally invalid rotations.',
        '- The latest reviewed runtime gate still denies real recorded factors.',
        '- No sealed confirmation-test access or new physical source intake occurred.',
        '',
        '## Physical evidence acquisition priorities',
        ''
    ]

    for action in report['priority_actions']:
        text.extend([
            f"### {action['priority']}. {action['task']}",
            '',
            'Affected gates: ' + ', '.join(action['gate_dependencies']),
            ''
        ])

    text.extend([
        '## Five unqualified timing streams',
        '',
        '| Stream | Required receipt fields (historical inventory) |',
        '|---|---|'
    ])

    for name, record in report['timing_receipt_matrix'].items():
        text.append(
            '| `' + name + '` | '
            + ', '.join(record['missing_receipt_fields'])
            + ' |'
        )

    text.extend([
        '',
        '## Eleven original gate receipts',
        '',
        '| Gate | Latest supported interpretation |',
        '|---|---|'
    ])

    for name, record in report['gate_matrix'].items():
        text.append(
            '| `' + name + '` | '
            + record['latest_supported_interpretation']
            + ' |'
        )

    text.extend([
        '',
        '## Reviewed immutable repository evidence',
        ''
    ])

    for key, item in sorted(report['source_files_sha256'].items()):
        text.append(
            '- `' + key + '`: `'
            + item['repo_relative_path'] + '` — SHA256 `'
            + item['sha256'] + '`'
        )

    text.extend([
        '',
        '## Decision',
        '',
        '**Do not authorize measured fusion factors, trust/health training, GT scoring or ATE/RPE.**',
        '',
        'Next work should obtain and independently validate authoritative physical evidence, not refit offsets from unqualified observations.',
        ''
    ])

    return '\n'.join(text)

if __name__ == '__main__':
    import sys

    repo, out = map(pathlib.Path, sys.argv[1:])

    sources, pins = load(repo)
    result = analyze(sources, pins)

    (out/'r92_physical_source_gap_decision_v1.json').write_bytes(
        canonical(result)
    )

    (out/'r92_evidence_acquisition_order_v1.md').write_text(
        markdown(result),
        encoding='utf-8'
    )

    print('R92_11_HISTORICAL_SCIENTIFIC_RECEIPTS=TRACEABLE')
    print('R92_5_UNFILLED_PHYSICAL_TIMING_RECEIPTS=TRACEABLE')
    print('R92_LOCAL_GT_RECOVERY_VS_PHYSICAL_QUALIFICATION=DISTINGUISHED')
    print('R92_PRIORITIZED_PHYSICAL_EVIDENCE_ACTIONS=5')
