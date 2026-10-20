"""R41: classify archived software configs and bounded TRAIN reference receipts."""

import hashlib
import json
import os
import pathlib
import stat
import subprocess
import sys

BASE = 'df78336320b3b026e448a09d39dfc571f922ae00'
BAG = 'ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1'
REFERENCE = '79d2c6d9132ce3cf87bb87445729302cd73709a59344a3dfacc5d7788937589d'

FILES = (
    'embedded/embedded_reference_path_contract_v1.json',
    'integrity/integrity_calibration_protocol_v1.json',
    'ood/ood_calibration_protocol_v1.json',
    'trust_robot/phase5_camera_imu_diagnostic_channel_contract_candidate_v1.json',
    'trust_robot/phase5_camera_imu_observation_adapter_candidate_v1.json',
    'trust_robot/phase5_camera_imu_train_ingestion_candidate_v1.json',
    'trust_robot/phase6_probabilistic_calibration_contract_candidate_v1.json',
    'v2/imu_reliability_v2_competitor_and_benchmark_protocol_candidate_v1.json',
    'v2/imu_reliability_v2_competitor_and_benchmark_protocol_candidate_v1b.json',
    'v2/imu_reliability_v2_competitor_and_benchmark_protocol_v1.json'
)

GATES = (
    'physical_camera_intrinsics_verified',
    'physical_sensor_extrinsics_verified',
    'mocap_reference_body_origin_verified',
    'reference_timestamp_event_verified',
    'reference_to_estimator_timebase_verified',
    'inter_stream_sync_verified',
    'calibrated_sensor_covariance_verified',
    'real_pose_factor_admission',
    'm2dgr_scoring_authorized',
    'health_training_authorized'
)

EXTS = {
    '.txt', '.csv', '.tsv', '.json',
    '.yaml', '.yml', '.tum', '.pose'
}

MAX_NODES = 6000
MAX_DEPTH = 6
MAX_MATCHES = 24
MAX_READ = 8_000_000

def need(ok, msg):
    if not ok:
        raise ValueError('R41_DENIED:' + msg)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def load(path):
    return json.loads(pathlib.Path(path).read_text())

def hash_read(path):
    fd = os.open(
        str(path),
        os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    )

    try:
        s = os.fstat(fd)

        need(
            stat.S_ISREG(s.st_mode)
            and 0 < s.st_size <= MAX_READ,
            'UNSAFE_REFERENCE_FILE'
        )

        digest = hashlib.sha256()
        received = 0

        while received < s.st_size:
            chunk = os.read(
                fd,
                min(65536, s.st_size - received)
            )

            need(bool(chunk), 'SHORT_REFERENCE_READ')

            digest.update(chunk)
            received += len(chunk)

        return digest.hexdigest(), s.st_size

    finally:
        os.close(fd)

def search_reference(train):
    stack = [(train, 0)]
    found = []
    visited = 0
    skipped = 0

    while stack:
        directory, depth = stack.pop()

        with os.scandir(directory) as iterator:
            entries = sorted(
                iterator,
                key=lambda entry: entry.name
            )

        for entry in entries:
            visited += 1

            need(
                visited <= MAX_NODES,
                'SEARCH_BOUNDED_NODES'
            )

            rel = pathlib.Path(entry.path).relative_to(train)
            components = [x.lower() for x in rel.parts]

            if (
                'confirmation_test' in components
                or any(
                    x in (
                        'rosbags', 'bags', '.git',
                        'experiments', '__pycache__',
                        '.cache', 'outputs'
                    )
                    for x in components
                )
            ):
                skipped += 1
                continue

            metadata = entry.stat(
                follow_symlinks=False
            )

            if stat.S_ISLNK(metadata.st_mode):
                skipped += 1
                continue

            if stat.S_ISDIR(metadata.st_mode):
                if depth < MAX_DEPTH:
                    stack.append(
                        (pathlib.Path(entry.path), depth + 1)
                    )
                continue

            if not stat.S_ISREG(metadata.st_mode):
                continue

            name = entry.name.lower()

            if (
                'room_02' not in name
                or pathlib.Path(name).suffix not in EXTS
            ):
                continue

            need(
                len(found) < MAX_MATCHES,
                'SEARCH_BOUNDED_MATCHES'
            )

            candidate = {
                'relative_path': rel.as_posix(),
                'size_bytes': metadata.st_size,
                'sha256': None,
                'matches_frozen_room_02_reference_sha256': False,
                'reference_physically_qualified': False
            }

            if 0 < metadata.st_size <= MAX_READ:
                digest, length = hash_read(
                    pathlib.Path(entry.path)
                )

                need(
                    length == metadata.st_size,
                    'FILE_MUTATED'
                )

                candidate['sha256'] = digest
                candidate[
                    'matches_frozen_room_02_reference_sha256'
                ] = digest == REFERENCE

            found.append(candidate)

    return (
        sorted(found, key=lambda x: x['relative_path']),
        visited,
        skipped
    )

def classification(rel):
    if rel.startswith('trust_robot/'):
        return (
            'TRUST_ROBOT_SOFTWARE_CONTRACT_NOT_PHYSICAL_CALIBRATION_RECEIPT'
        )

    return (
        'SEPARATE_SOFTWARE_PROTOCOL_NOT_PHYSICAL_CALIBRATION_RECEIPT'
    )

def policy(report):
    need(
        report.get('schema') ==
        'TRUST_ROBOT_R41_TRAIN_CALIBRATION_CANDIDATE_SEMANTICS_V1'
        and report.get('trajectory_id') == 'room_02'
        and report.get('split') == 'train'
        and report.get('github_baseline') == BASE,
        'SCOPE'
    )

    need(
        report.get('source_bag_sha256') == BAG
        and report.get('raw_bag_opened') is False
        and report.get('confirmation_test_payload_accessed') is False
        and report.get('github_modified') is False,
        'ACCESS'
    )

    need(
        all(
            type(report.get(k)) is int
            and report[k] == 0
            for k in (
                'qualified_pose_factors',
                'health_labels',
                'ate_rpe_scores'
            )
        ),
        'ZERO_SCIENCE'
    )

    need(
        set(report.get('qualification_gates', {})) == set(GATES)
        and all(
            value == 'UNVERIFIED_OR_DENIED'
            for value in report['qualification_gates'].values()
        ),
        'GATES'
    )

    records = report.get('configuration_semantics', [])

    need(
        len(records) == 10
        and [
            item['relative_config_path']
            for item in records
        ] == list(FILES),
        'CONFIG_INVENTORY'
    )

    need(
        all(
            item.get('role') ==
                classification(item['relative_config_path'])
            and item.get(
                'physical_sensor_calibration_qualified'
            ) is False
            and item.get('git_blob_identical') is True
            for item in records
        ),
        'ROLE_PROMOTION'
    )

    need(
        report.get('config_role_counts') == {
            'trust_robot_software_contracts': 4,
            'separate_software_protocols': 6
        },
        'ROLES'
    )

    need(
        report.get('room_02_reference_source') == 'mocap'
        and report.get('room_02_invalid_rotation_records') == 90
        and report.get('frozen_raw_reference_sha256') == REFERENCE,
        'MOCAP'
    )

    need(
        report.get('next_phase') ==
        'R42_TRAIN_SENSOR_CALIBRATION_EVIDENCE_GAP_RESOLUTION',
        'NEXT'
    )

    need(
        all(
            item['reference_physically_qualified'] is False
            for item in report.get(
                'room_02_reference_file_candidates', []
            )
        ),
        'FILE_PROMOTION'
    )

    need(
        report.get('physical_calibration_admitted') is False
        and report.get('reference_scoring_authorized') is False,
        'NONFACTOR'
    )

def run(repo, train, r40p, v40p, r39p, out, plan):
    r40 = load(r40p)
    v40 = load(v40p)
    r39 = load(r39p)

    need(
        r40['schema'] ==
        'TRUST_ROBOT_R40_TRAIN_CALIBRATION_REFERENCE_ASSET_INVENTORY_V1'
        and r40['trajectory_id'] == 'room_02'
        and r40['split'] == 'train'
        and r40['github_baseline'] == BASE,
        'R40_SCOPE'
    )

    need(
        v40['source_report_sha256'] == sha(r40p.read_bytes())
        and v40['local_candidate_files_verified'] == 10
        and v40['repository_manifest_git_snapshots_verified'] == 11,
        'R40_INDEPENDENT'
    )

    need(
        r39['decision'] ==
        'DIAGNOSTICS_VERIFIED_QUALIFIED_REAL_FACTORS_BLOCKED'
        and r39['split'] == 'train',
        'R39_GATES'
    )

    known = r40['candidate_files']

    need(
        len(known) == len(FILES)
        and all(
            item['scope'] == 'repository_configs'
            for item in known
        ),
        'R40_CANDIDATES'
    )

    by_name = {
        item['relative_path']: item
        for item in known
    }

    need(
        set(by_name) == set(FILES),
        'SOURCE_PATHS'
    )

    records = []

    for rel in FILES:
        path = repo / 'configs' / rel

        need(
            path.is_file()
            and not path.is_symlink()
            and path.stat().st_nlink == 1
            and 0 < path.stat().st_size <= 2_000_000,
            'CONFIG_FILE:' + rel
        )

        raw = path.read_bytes()

        frozen = subprocess.check_output([
            'git', '-C', str(repo),
            'show', BASE + ':configs/' + rel
        ])

        need(
            raw == frozen
            and sha(raw) == by_name[rel]['sha256_small_file'],
            'CONFIG_FROZEN:' + rel
        )

        doc = json.loads(raw)
        role = classification(rel)

        if rel == (
            'trust_robot/'
            'phase6_probabilistic_calibration_contract_candidate_v1.json'
        ):
            need(
                doc['calibration_scope'][
                    'sensor_geometry_calibration'
                ] is False
                and doc['current_evidence_gate'][
                    'calibration_execution_authorized'
                ] is False,
                'PHASE6_NOT_SENSOR_GEOMETRY'
            )

        if rel == (
            'trust_robot/'
            'phase5_camera_imu_observation_adapter_candidate_v1.json'
        ):
            need(
                doc['health_boundary'][
                    'classifier_training_authorized'
                ] is False,
                'ADAPTER_NO_TRAINING'
            )

        if rel == (
            'trust_robot/'
            'phase5_camera_imu_train_ingestion_candidate_v1.json'
        ):
            need(
                doc['scientific_boundary'][
                    'final_scoring_authorized'
                ] is False,
                'INGESTION_NO_SCORING'
            )

        records.append({
            'relative_config_path': rel,
            'sha256': sha(raw),
            'role': role,
            'top_level_fields': sorted(doc),
            'git_blob_identical': True,
            'physical_sensor_calibration_qualified': False
        })

    reference = r40['room_02_reference_provenance']

    need(
        reference['reference_source'] == 'mocap'
        and reference['rotation_invalid_count'] == 90
        and reference[
            'raw_reference_sha256_provenance_only'
        ] == REFERENCE,
        'ROOM_REFERENCE'
    )

    paths, visited, skipped = search_reference(train)

    direct = r40[
        'explicit_room_02_reference_path_receipts'
    ]

    for receipt in direct:
        rel = pathlib.PurePosixPath(
            receipt['path_relative_to_train']
        )

        need(
            not rel.is_absolute()
            and '..' not in rel.parts,
            'R40_DIRECT_PATH'
        )

        p = train.joinpath(*rel.parts)

        need(
            (
                p.is_file() and not p.is_symlink()
            ) == receipt['present_regular_file'],
            'R40_DIRECT_RECEIPT_CHANGED'
        )

    report = {
        'schema':
            'TRUST_ROBOT_R41_TRAIN_CALIBRATION_CANDIDATE_SEMANTICS_V1',
        'trajectory_id': 'room_02',
        'split': 'train',
        'github_baseline': BASE,
        'source_bag_sha256': BAG,
        'r40_report_sha256': sha(r40p.read_bytes()),
        'r40_independent_sha256': sha(v40p.read_bytes()),
        'r39_report_sha256': sha(r39p.read_bytes()),
        'configuration_semantics': records,
        'config_role_counts': {
            'trust_robot_software_contracts': 4,
            'separate_software_protocols': 6
        },
        'room_02_reference_source': 'mocap',
        'room_02_invalid_rotation_records': 90,
        'frozen_raw_reference_sha256': REFERENCE,
        'room_02_reference_file_candidates': paths,
        'matching_frozen_reference_payload_count':
            sum(
                item['matches_frozen_room_02_reference_sha256']
                for item in paths
            ),
        'reference_search_nodes_scanned': visited,
        'reference_search_entries_skipped': skipped,
        'prior_explicit_reference_paths_present':
            sum(
                item['present_regular_file']
                for item in direct
            ),
        'qualification_gates': {
            key: 'UNVERIFIED_OR_DENIED'
            for key in GATES
        },
        'physical_calibration_admitted': False,
        'reference_scoring_authorized': False,
        'qualified_pose_factors': 0,
        'health_labels': 0,
        'ate_rpe_scores': 0,
        'raw_bag_opened': False,
        'confirmation_test_payload_accessed': False,
        'github_modified': False,
        'next_phase':
            'R42_TRAIN_SENSOR_CALIBRATION_EVIDENCE_GAP_RESOLUTION'
    }

    policy(report)

    with out.open('x') as handle:
        json.dump(
            report, handle,
            indent=2,
            sort_keys=True,
            allow_nan=False
        )
        handle.write('\n')

    lines = [
        '# R41 — Configuration semantics and TRAIN mocap reference receipts',
        '',
        '## Evidence scope',
        '',
        'Exactly ten KIOS JSON candidates were byte-matched to the '
        'GitHub R38 commit. Their presence **does not** verify '
        'physical calibration.',
        '',
        '## Candidate classification',
        ''
    ]

    for item in records:
        lines.append(
            '- `configs/' + item['relative_config_path']
            + '` — ' + item['role']
        )

    lines.extend([
        '',
        '## TRAIN room_02 reference search',
        '',
        'Frozen reference source: mocap. The reference-quality index '
        'reports 90 invalid rotation records and zero invalid '
        'translation records.',
        '',
        'Bounded filename search: '
        + str(visited) + ' entries scanned, '
        + str(len(paths)) + ' room_02-named candidates found.',
        '',
        'Candidates byte-identical to frozen reference checksum: '
        + str(
            report['matching_frozen_reference_payload_count']
        ),
        '',
        'A matching checksum is not proof of mocap tracked origin, '
        'frame transform or physically synchronized evaluation.',
        ''
    ])

    for item in paths:
        lines.append(
            '- `' + item['relative_path'] + '` — SHA '
            + str(item['sha256'])
            + '; MATCHED_FROZEN_REFERENCE='
            + str(
                item['matches_frozen_room_02_reference_sha256']
            )
        )

    lines.extend([
        '',
        '## Scientific decision',
        '',
        'Real factor admission, health training, ATE/RPE and '
        'confirmation-test access remain closed.',
        '',
        '## R42 acceptance direction',
        '',
        'Resolve independent camera intrinsics, cross-sensor transforms, '
        'mocap body origin and timestamp semantics from physically '
        'traceable sources. Do not infer calibration from software contracts.',
        ''
    ])

    with plan.open('x') as handle:
        handle.write('\n'.join(lines))

    print('R41_CONFIGS_GIT_IDENTICAL=10')
    print(
        'R41_SOFTWARE_CONTRACTS_TRUST_ROBOT=4_OTHER_PROTOCOLS=6'
    )
    print(
        'R41_ROOM_02_REFERENCE_FILENAME_CANDIDATES=%d'
        % len(paths)
    )
    print(
        'R41_FROZEN_REFERENCE_BYTES_MATCHED=%d'
        % report['matching_frozen_reference_payload_count']
    )
    print('R41_SCIENTIFIC_CALIBRATION_ADMITTED=NO')

if __name__ == '__main__':
    run(
        *(pathlib.Path(p) for p in sys.argv[1:8])
    )
