"""R83C independent archive integrity and scientific-boundary verifier."""

import hashlib
import json
import pathlib
import stat
import sys

SCHEMA = (
    'TRUST_ROBOT_R80_R82_RECORDED_MULTIMODAL_CHECKPOINT_V1'
)

BASE = 'aa4c06bdc2eac5cff7352157beef9ec534f2f455'
TAR_SHA = 'ea657ee247f90ba480040d38b1226f40dee6ccb39b5aa2c21584eda28d5d83c2'

def require(condition, reason):
    if not condition:
        raise ValueError('R83C_CHECKPOINT_DENIED:' + reason)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def obj(root, rel):
    return json.loads((root / rel).read_bytes())

def verify(root):
    require(
        root.is_dir() and not root.is_symlink(),
        'ROOT'
    )

    manifest = obj(root, 'checkpoint_manifest_v1.json')

    require(manifest.get('schema') == SCHEMA, 'SCHEMA')
    require(manifest.get('parent_commit') == BASE, 'PARENT')

    require(
        manifest.get('branch') ==
        'kios-isaacsim-v15-integration',
        'BRANCH'
    )

    require(
        manifest.get('handoff_archive_sha256') == TAR_SHA,
        'TRANSFER_SHA'
    )

    pins = manifest.get('source_sha256')
    meta = manifest.get('metadata_sha256')

    require(
        type(pins) is dict
        and len(pins) == 13
        and manifest.get('source_count') == 13,
        'SOURCE_COUNT'
    )

    require(
        type(meta) is dict
        and set(meta) == {
            'README.md',
            'verify_checkpoint.py'
        },
        'METADATA'
    )

    expected = (
        set(pins)
        | set(meta)
        | {'checkpoint_manifest_v1.json'}
    )

    require(len(expected) == 16, 'EXPECTED_FILE_COUNT')

    directories = set()

    for rel in expected:
        path = pathlib.PurePosixPath(rel)

        require(
            not path.is_absolute()
            and '..' not in path.parts,
            'PATH'
        )

        for n in range(1, len(path.parts)):
            directories.add(
                '/'.join(path.parts[:n])
            )

    actual = {
        str(p.relative_to(root))
        for p in root.rglob('*')
    }

    require(
        actual == expected | directories,
        'FILE_ALLOWLIST'
    )

    for rel in directories:
        p = root / rel

        require(
            p.is_dir() and not p.is_symlink(),
            'DIRECTORY:' + rel
        )

    for rel in expected:
        s = (root / rel).lstat()

        require(
            stat.S_ISREG(s.st_mode)
            and s.st_nlink == 1
            and 0 < s.st_size <= 4_000_000,
            'FILE:' + rel
        )

    for rel, pin in {**pins, **meta}.items():
        require(
            type(pin) is str
            and len(pin) == 64
            and sha((root / rel).read_bytes()) == pin,
            'HASH:' + rel
        )

    hand = obj(
        root,
        'evidence/handoff_manifest_v1.json'
    )

    require(
        hand.get('schema') ==
        'TRUST_ROBOT_R83_SANITIZED_R81_R82_TRANSFER_V1',
        'HANDOFF_SCHEMA'
    )

    require(
        hand.get('source_count') == 8
        and hand.get('kios_baseline') == BASE,
        'HANDOFF_PARENT'
    )

    hp = hand.get('source_sha256')

    require(
        type(hp) is dict and len(hp) == 8,
        'HANDOFF_SOURCES'
    )

    r80_paths = {
        'evidence/r80/dev/r80_motion.py',
        'evidence/r80/dev/test_r80.py',
        'evidence/r80/result/r80_recorded_lidar_motion_bridge_v1.json',
        'evidence/r80/result/r80_independent_validation_v1.json'
    }

    require(
        {
            'evidence/' + k
            for k in hp
        } | {'evidence/handoff_manifest_v1.json'}
        == set(pins) - r80_paths,
        'HANDOFF_ALLOWLIST'
    )

    for rel, pin in hp.items():
        require(
            pins['evidence/' + rel] == pin,
            'HANDOFF_SOURCE_SHA:' + rel
        )

        require(
            (root / 'evidence' / rel).stat().st_size
            == hand['source_bytes'][rel],
            'HANDOFF_SOURCE_SIZE:' + rel
        )

    for filename, pin in hand[
        'r80_kios_expected_sha256'
    ].items():
        rel = (
            'evidence/r80/'
            + (
                'dev/' if filename.endswith('.py')
                else 'result/'
            )
            + filename
        )

        require(
            pins.get(rel) == pin,
            'R80_HANDOFF_PIN:' + filename
        )

    r80 = obj(
        root,
        'evidence/r80/result/r80_recorded_lidar_motion_bridge_v1.json'
    )

    r80v = obj(
        root,
        'evidence/r80/result/r80_independent_validation_v1.json'
    )

    r81 = obj(
        root,
        'evidence/r81/result/r81_full_train_increment_adapter_v1.json'
    )

    r81v = obj(
        root,
        'evidence/r81/result/r81_independent_validation_v1.json'
    )

    r82 = obj(
        root,
        'evidence/r82/result/r82_temporal_window_manifest_v1.json'
    )

    r82v = obj(
        root,
        'evidence/r82/result/r82_independent_validation_v1.json'
    )

    require(
        r80.get('schema') ==
        'TRUST_ROBOT_R80_RECORDED_LIDAR_MOTION_BRIDGE_V1',
        'R80_SCHEMA'
    )

    require(
        r80.get('pair_count') == 8
        and len(r80.get('records', [])) == 8,
        'R80_COUNT'
    )

    require(
        r80v.get('status') == 'PASS'
        and r80v.get('result_sha256') ==
        pins['evidence/r80/result/r80_recorded_lidar_motion_bridge_v1.json'],
        'R80_RECEIPT'
    )

    require(
        r81.get('status') == 'PASS'
        and r81.get('schema') ==
        'TRUST_ROBOT_R81_FULL_TRAIN_READ_ONLY_INCREMENT_ADAPTER_V1',
        'R81_STATUS'
    )

    require(
        r81.get('trajectory_count') == 22
        and r81.get('increment_count') == 90992
        and r81.get('scan_count') == 91014,
        'R81_COUNTS'
    )

    require(
        len(r81.get('trajectory_results', [])) == 22
        and sum(
            x['increments']
            for x in r81['trajectory_results']
        ) == 90992,
        'R81_ROWS'
    )

    require(
        r81v.get('status') == 'PASS'
        and r81v.get('result_sha256') ==
        pins['evidence/r81/result/r81_full_train_increment_adapter_v1.json'],
        'R81_RECEIPT'
    )

    require(
        r81v.get('code_sha256') ==
        pins['evidence/r81/dev/r81_adapter.py']
        and r81v.get('test_sha256') ==
        pins['evidence/r81/dev/test_r81.py'],
        'R81_SOURCE_TEST_LINEAGE'
    )

    require(
        r82.get('schema') ==
        'TRUST_ROBOT_R82_STREAM_LOCAL_TEMPORAL_DIAGNOSTIC_V1'
        and r82.get('status') == 'PASS',
        'R82_STATUS'
    )

    require(
        r82.get('trajectory_count') == 22
        and r82.get('source_feature_records') == 2816957
        and r82.get('source_feature_files') == 62,
        'R82_COUNTS'
    )

    require(
        r82.get('source_R81_result_sha256') ==
        pins['evidence/r81/result/r81_full_train_increment_adapter_v1.json'],
        'R81_R82_LINEAGE'
    )

    require(
        r82v.get('status') == 'PASS'
        and r82v.get('report_sha256') ==
        pins['evidence/r82/result/r82_temporal_window_manifest_v1.json'],
        'R82_RECEIPT'
    )

    require(
        r82v.get('engine_sha256') ==
        pins['evidence/r82/dev/r82_temporal.py']
        and r82v.get('tests_sha256') ==
        pins['evidence/r82/dev/test_r82.py'],
        'R82_SOURCE_TEST_LINEAGE'
    )

    require(
        r82v.get('verified_window_files') == 62
        and r82v.get('source_feature_records') == 2816957
        and r82v.get('derived_window_count') ==
        r82.get('derived_window_count'),
        'R82_WINDOWS'
    )

    trajectories = r81['trajectory_results']

    require(
        [
            x['trajectory']
            for x in trajectories
        ] == [
            x['trajectory']
            for x in r82['trajectory_summaries']
        ],
        'TRAIN_ORDER'
    )

    require(
        sum(
            x['lidar_source_increment_count']
            for x in r82['trajectory_summaries']
        ) == 90992,
        'R82_LIDAR_COUNTS'
    )

    require(
        sum(
            sum(
                s['source_record_count']
                for s in x['camera_imu_streams'].values()
            )
            for x in r82['trajectory_summaries']
        ) == 2816957,
        'R82_FEATURE_COUNTS'
    )

    for trajectory in r82['trajectory_summaries']:
        for stream, value in trajectory[
            'camera_imu_streams'
        ].items():

            if (
                trajectory['trajectory'] in (
                    'street_010',
                    'street_09'
                )
                and stream in (
                    '/camera/imu',
                    '/camera/color/image_raw/compressed'
                )
            ):
                require(
                    value.get('availability') ==
                    'observed_absent'
                    and value.get('source_record_count') == 0,
                    'MISSING_MODALITY'
                )

            require(
                value.get('availability') in (
                    'observed_present',
                    'observed_absent'
                ),
                'AVAILABILITY'
            )

    scientific_checks = (
        (
            r80,
            (
                'real_pose_factors_authorized',
                'ate_rpe_authorized',
                'health_training_authorized',
                'confirmation_test_accessed',
                'raw_rosbag_or_gt_opened'
            )
        ),
        (
            r81,
            (
                'real_pose_factors_authorized',
                'ate_rpe_authorized',
                'health_training_authorized',
                'confirmation_test_accessed',
                'raw_rosbags_or_gt_opened'
            )
        ),
        (
            r82,
            (
                'real_factors_authorized',
                'ate_rpe_computed',
                'health_label_or_probability_emitted',
                'reference_or_confirmation_accessed',
                'physical_clock_or_cross_modal_sync_assumed'
            )
        ),
        (
            manifest,
            (
                'raw_rosbags_archived',
                'original_gt_archived',
                'private_verona_reports_archived',
                'se3_raw_feature_rows_archived',
                'r82_window_files_archived',
                'cross_modal_clock_qualified',
                'real_pose_factors_authorized',
                'health_training_authorized',
                'ate_rpe_authorized',
                'confirmation_test_accessed'
            )
        )
    )

    for data, fields in scientific_checks:
        for field in fields:
            require(
                data.get(field) is False,
                'SCIENCE:' + field
            )

    for data in (
        r80, r81, r82,
        r80v, r81v, r82v,
        manifest
    ):
        require(
            data.get('scientific_gates_closed') == 11,
            'SCIENTIFIC_GATES'
        )

    for rel in pins:
        raw = (root / rel).read_bytes()

        require(
            not any(
                marker in raw
                for marker in (
                    b'/mnt/hdd16T/',
                    b'/home/kios/',
                    b'C:\\Users\\'
                )
            ),
            'PRIVATE_PATH:' + rel
        )

    print('R83C_STANDALONE_ARCHIVE_VERIFIER=PASS')
    print('R83C_EXACT_SOURCE_FILES=13_SHA256_VERIFIED')
    print('R83C_R80_R82_CROSS_PHASE_RECEIPTS=PASS')
    print('R83C_SCIENTIFIC_GATES=11_CLOSED')

if __name__ == '__main__':
    require(
        len(sys.argv) == 3 and sys.argv[1] == 'verify',
        'ARGUMENTS'
    )

    verify(pathlib.Path(sys.argv[2]))
