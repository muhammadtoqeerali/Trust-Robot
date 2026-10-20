"""R45: immutable upstream author-source discovery and safe intake gates.

No network requests, no download, no decoding of sensor payloads.
"""
import hashlib
import json
import pathlib
import sys

LOCAL_BASE = '17536d0e9a03eb4f0b4adfb5056dc7ba63df9921'
UPSTREAM_BASE = '5db59c1fe38d8f1d2fb3a71f1f8c5581b8de00e5'
BAG = 'ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1'
AUTHOR = 'SJTU-ViSYS/M2DGR'

# Immutable Git object IDs checked against the public upstream repository
# during discovery; R45 deliberately does not retrieve these files on KIOS.
SOURCES = (
    ('calibration_results.txt', 'f2b1180f9cdef4e665332a09973f9acba9d9d34e',
     'AUTHOR_PUBLISHED_CALIBRATION_TABLE_CANDIDATE',
     'Sensor calibration and extrinsic candidates; requires applicability, matrix orientation and independent physical validation'),
    ('my_params_camera.yaml', '9c429c28dcfc7bea2e59be5529c79ecf46cdf3c6',
     'APPLICATION_CAMERA_VIO_CONFIGURATION_CANDIDATE',
     'LVI-SAM camera parameter choices and IMU/camera mapping; not a new calibration experiment'),
    ('my_params_lidar.yaml', 'a768b1a8f8baa5649009c941817a51ff3f3e00e9',
     'APPLICATION_LIDAR_IMU_CONFIGURATION_CANDIDATE',
     'LVI-SAM LiDAR and HandsFree IMU application settings; not independent physical validation'),
    ('README.md', 'c394994a8431426c0bd4b3dcf618faf7b97d119f',
     'UPSTREAM_DATASET_DESCRIPTION_AND_AUTHOR_CONTEXT',
     'Dataset author describes sensor suite, synchronization claims, calibration methods and export tools'),
)

GATES = (
    'camera_intrinsics_physically_verified',
    'camera_lidar_extrinsics_physically_verified',
    'camera_imu_extrinsics_physically_verified',
    'mocap_body_to_lidar_physically_verified',
    'reference_capture_clock_physically_verified',
    'cross_sensor_synchronization_physically_verified',
    'raw_reference_available_locally',
    'metric_visual_pose_authorized',
    'real_sensor_factors_authorized',
    'health_training_authorized',
    'm2dgr_ate_rpe_authorized',
)

DENIED = (
    'external_file_content_downloaded', 'external_calibration_loaded',
    'official_blob_sha256_verified_on_kios', 'sensor_frame_transforms_validated',
    'capture_clock_physically_verified', 'mocap_body_transform_verified',
    'real_sensor_factors_authorized', 'health_training_authorized',
    'm2dgr_scoring_authorized', 'confirmation_test_accessed',
    'raw_bag_opened', 'github_modified',
)

def need(condition, reason):
    if not condition:
        raise ValueError('R45_DENIED:' + reason)

def digest(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()

def load(path):
    return json.loads(pathlib.Path(path).read_text())

def registry():
    rows = []
    for filename, blob, role, note in SOURCES:
        rows.append({
            'path': filename,
            'upstream_git_blob_sha1': blob,
            'upstream_immutable_commit': UPSTREAM_BASE,
            'source_repository': AUTHOR,
            'immutable_source_url':
                'https://github.com/' + AUTHOR + '/blob/' + UPSTREAM_BASE + '/' + filename,
            'role': role,
            'interpretation': note,
            'content_downloaded_on_kios': False,
            'file_bytes_sha256_observed_on_kios': None,
            'physical_calibration_qualified': False,
            'room_02_sensor_applicability_verified': False,
            'reference_clock_semantics_verified': False,
        })
    return rows

def policy(report):
    need(report.get('schema') == 'TRUST_ROBOT_R45_AUTHOR_UPSTREAM_CALIBRATION_INTAKE_READINESS_V1', 'SCHEMA')
    need(report.get('trajectory_id') == 'room_02' and report.get('split') == 'train'
         and report.get('local_github_parent') == LOCAL_BASE
         and report.get('source_bag_sha256') == BAG, 'TRAIN_SOURCE')
    need(report.get('author_repository') == AUTHOR and report.get('author_repository_commit') == UPSTREAM_BASE, 'AUTHOR')
    need(report.get('upstream_candidates') == registry(), 'IMMUTABLE_CANDIDATES')
    need(report.get('r43_gate_statuses') == {gate: 'NOT_QUALIFIED' for gate in GATES}, 'ELEVEN_GATES')
    need(report.get('unfilled_r43_source_receipts') == 11, 'EMPTY_RECEIPTS')
    need(all(report.get(k) is False for k in DENIED), 'SCIENCE_OR_ACCESS')
    need(all(type(report.get(k)) is int and report.get(k) == 0
             for k in ('real_pose_factors_generated', 'health_labels_generated',
                       'ate_rpe_scores_generated', 'new_external_source_files')), 'SCIENCE_COUNTS')
    need(report.get('next_phase') == 'R46_UPSTREAM_CALIBRATION_CONTENT_PROVENANCE_AUDIT', 'NEXT')
    need(report.get('candidate_evidence_status') == 'UPSTREAM_DISCOVERED_NOT_ACQUIRED_OR_QUALIFIED', 'EVIDENCE_LEVEL')

def build(r43p, receipts_path, v43p, r42p, report_path, plan_path):
    r43, empty, v43, r42 = map(load, (r43p, receipts_path, v43p, r42p))
    need(r43['schema'] == 'TRUST_ROBOT_R43_SOURCE_ACQUISITION_GATE_PROTOCOL_V1'
         and r43['trajectory_id'] == 'room_02' and r43['split'] == 'train'
         and r43['source_acquisition_status'] == 'NOT_ACQUIRED'
         and r43['unresolved_gate_count'] == 11, 'R43_SOURCE')
    need(r43['upstream_report_sha256']['r42'] == digest(r42p), 'R42_CHAIN')
    need(v43['r43_protocol_sha256'] == digest(r43p)
         and v43['unfilled_receipts_sha256'] == digest(receipts_path)
         and v43['nonempty_source_receipts'] == 0, 'R43_INDEPENDENT')
    need(empty['schema'] == 'TRUST_ROBOT_R43_EMPTY_EVIDENCE_RECEIPTS_V1'
         and empty['source_data_present'] is False, 'EMPTY_TEMPLATE')
    need(set(r43['requests']) == set(empty['gate_receipts']) == set(GATES), 'GATES_MATCH')
    for gate in GATES:
        need(r43['requests'][gate]['status'] == 'NOT_QUALIFIED'
             and r43['requests'][gate]['physical_validation_completed'] is False, 'NOT_QUALIFIED:' + gate)
        row = empty['gate_receipts'][gate]
        need(row['status'] == 'NO_SOURCE_RECEIVED'
             and row['source_uri'] is None
             and row['source_sha256'] is None
             and row['independent_validation_sha256'] is None
             and row['physical_qualification_authorized'] is False
             and all(value is None for value in row['required_fields'].values()), 'SOURCE_RECEIPT:' + gate)
    need(r42['connection_count'] == 15 and r42['camera_info_topic_count'] == 0
         and r42['tf_topic_count'] == 0 and r42['mocap_or_pose_reference_topic_count'] == 0
         and r42['sensor_payload_decompressed'] is False, 'RECORDED_HEADERS')
    need(r43['existing_d435i_relative_rotation_content_support'] is True
         and r43['full_extrinsic_from_partial_rotation'] is False, 'PARTIAL_ROTATION')
    output = {
        'schema': 'TRUST_ROBOT_R45_AUTHOR_UPSTREAM_CALIBRATION_INTAKE_READINESS_V1',
        'trajectory_id': 'room_02', 'split': 'train',
        'local_github_parent': LOCAL_BASE,
        'source_bag_sha256': BAG,
        'author_repository': AUTHOR,
        'author_repository_commit': UPSTREAM_BASE,
        'upstream_candidates': registry(),
        'candidate_evidence_status': 'UPSTREAM_DISCOVERED_NOT_ACQUIRED_OR_QUALIFIED',
        'r43_source_sha256': {
            'protocol': digest(r43p),
            'empty_receipts': digest(receipts_path),
            'independent_validation': digest(v43p),
            'r42_connection_report': digest(r42p),
        },
        'r43_gate_statuses': {gate: 'NOT_QUALIFIED' for gate in GATES},
        'unfilled_r43_source_receipts': 11,
        'applicability_checks_next': [
            'Pin upstream author file bytes to immutable Git blob and independent SHA256',
            'Resolve author calibration table transform direction, matrix layout, units and distortion model',
            'Confirm calibration applies to room_02 RealSense and HandsFree sensor devices and capture configuration',
            'Compare author calibration table vs downstream LVI-SAM parameters and independently resolve differences',
            'Confirm exact image stream resolution and camera model without inferring calibrated physical clock',
            'Obtain reference source receipt and qualify mocap body origin, frame alignment and timestamp semantics',
            'Keep original R43 receipts empty until separately reviewed evidence is admitted',
        ],
        'next_phase': 'R46_UPSTREAM_CALIBRATION_CONTENT_PROVENANCE_AUDIT',
        'real_pose_factors_generated': 0,
        'health_labels_generated': 0,
        'ate_rpe_scores_generated': 0,
        'new_external_source_files': 0,
        **{gate: False for gate in DENIED},
    }
    policy(output)
    with report_path.open('x') as f:
        json.dump(output, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')
    lines = [
        '# R45 — Upstream M2DGR calibration source intake readiness',
        '',
        'Immutable published upstream candidates; **no file content downloaded or qualified on KIOS**.',
        '',
        'Upstream repository: `SJTU-ViSYS/M2DGR`.',
        'Upstream commit: `'+UPSTREAM_BASE+'`.',
        '',
        '## Immutable candidates',
        '',
    ]
    for row in output['upstream_candidates']:
        lines.extend([
            '- **'+row['path']+'** — '+row['role']+'; Git blob `'+row['upstream_git_blob_sha1']+'`.',
            '  '+row['immutable_source_url'],
            '  '+row['interpretation']+'.',
        ])
    lines += [
        '', '## Critical distinction', '',
        'The official dataset README and published calibration_results.txt provide prospective sensor parameters, but actual applicability to the frozen room_02 messages, matrix storage layout, sensor frame direction, complete physical clock alignment and independent reference validity have not been demonstrated.',
        'LVI-SAM parameter YAML files may contain application-specific choices and must not override independently verified author calibration receipts.',
        'The R43 evidence-receipt template remains fully empty. There is no incoming calibration file in this phase.',
        '', '## Next R46', '',
        'Audit content of specifically approved, pinned upstream sources under a separate read-only source-intake stage. Before use, independently verify SHA256, precise sensor applicability, transform orientation, units and discrepancies between the calibration table and application YAMLs. Do not admit pose factors, health labels or ATE/RPE.',
        '', 'No Git changes, no raw ROS bag access, no confirmation-test data.', ''
    ]
    with plan_path.open('x') as f:
        f.write('\n'.join(lines))
    print('R45_UPSTREAM_AUTHOR_REPOSITORY='+AUTHOR)
    print('R45_UPSTREAM_IMMUTABLE_COMMIT='+UPSTREAM_BASE)
    print('R45_AUTHOR_SOURCE_CANDIDATES=4_PINNED_BY_GIT_BLOB_ID')
    print('R45_AUTHOR_CALIBRATION_AND_CONFIG_CANDIDATES=3_NOT_QUALIFIED')
    print('R45_R43_EVIDENCE_GATES=11_CLOSED')
    print('R45_EXTERNAL_FILES_ACQUIRED_ON_KIOS=0')

if __name__=='__main__':
    build(*(pathlib.Path(x) for x in sys.argv[1:7]))
