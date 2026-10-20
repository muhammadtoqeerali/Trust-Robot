"""TRAIN-only R33-R36 evidence review; no raw bag access."""

import ast
import hashlib
import json
import pathlib
import sys

BAG = 'ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1'
BASE = 'ebfd02b0ef8ad79b2e6a9810897fcb71efec2e87'

TOPICS = ('/camera/imu', '/handsfree/imu')

FRAMES = {
    '/camera/imu': 'camera_imu_optical_frame',
    '/handsfree/imu': 'base_link'
}

PINS = {
    'r33/trust_robot_r33_camera_multipair_dev_v1/r33_camera_multipair.py':
        '3139e3514a53c7e03f22a932e2810a42b749983ad18bedd43a245dd2c9579c53',
    'r33/trust_robot_r33_camera_multipair_dev_v1/r33_independent_verify.py':
        '8af2a47fd76c71b09a31f6a3dd073426aeb43ab6217478c099a07c1ac5931206',
    'r33/trust_robot_r33_camera_multipair_dev_v1/r33_camera_multipair_initial_failed_v1.py.saved':
        '26ed1990ef00cb01c2b60f1af9b60b832e892ede988571fdc72b42a19f3e8dc4',
    'r33/trust_robot_r33_camera_multipair_dev_v1/r33_independent_verify_initial_failed_v1.py.saved':
        '68eb81ea44758c9cfff53e43625c4fef97ec7bd935febe24f35c25c374ad5436',
    'r33/trust_robot_r33_camera_multipair_result_v1/r33_failed_baseline_repair_provenance_v1.json':
        'c7ce9e145bc4505fb8ce35844f5e76bc978432b7bc4bba5d25d9fc6e1fb6245c',
    'r33/trust_robot_r33_camera_multipair_result_v1/r33_camera_multipair_pixel_diagnostics_v1.json':
        '1e74e18205b8429d88632826f1f3c30055165352228a19aefa1064432b2853b1',
    'r33/trust_robot_r33_camera_multipair_result_v1/r33_independent_validation_v1.json':
        'fcd1fa9d17a498be09b945da3c0721552fa520028f34cdee1d3b54e0ffa90321',

    'r34/trust_robot_r34_imu_short_interval_dev_v1/r34_imu.py':
        '377627ecabd5c8d0f3fb2555e83ae48ad527111bec22986e1f277080d0bead2a',
    'r34/trust_robot_r34_imu_short_interval_dev_v1/r34_independent_verify.py':
        '95cf6a99057a79c82d43da16c298c083194d00489b98bb76e09793b3e8c40bb3',
    'r34/trust_robot_r34_imu_short_interval_result_v1/r34_imu_short_interval_diagnostics_v1.json':
        '778c223c6c034343413ff848db6276aecdd730390311f178cb918b94ee10064e',
    'r34/trust_robot_r34_imu_short_interval_result_v1/r34_independent_validation_v1.json':
        'c3be4f270b093fb6342537de446f6c2c3da89aee7ce0e83a83ba3c7066b99c54',

    'r35/trust_robot_r35_imu_variation_frame_dev_v1/r35_analysis.py':
        'd1183ea286007e81c46f52b391a8b23217d846f0d5d90784547513db36a5d691',
    'r35/trust_robot_r35_imu_variation_frame_dev_v1/r35_independent_verify.py':
        'af716ff68601855b7a3a1bb4cbbc72a3ded0e41347741a518213324c7fdb5d88',
    'r35/trust_robot_r35_imu_variation_frame_dev_v1/test_r35.py':
        '4a81d0c33985a29bacd75df7718a3c38d24f0219338aa8f3215009f4405709da',
    'r35/trust_robot_r35_imu_variation_frame_result_v1/r35_imu_variation_frame_v1.json':
        'a0fbf5931833dfecb609f82e27fdd13fa2fc4dbfead8dbb106a99af162698e1e',
    'r35/trust_robot_r35_imu_variation_frame_result_v1/r35_independent_validation_v1.json':
        '883ca024ed05600552db5f5cd72e07af761c9b4c859bbc5b648426b3c3439971',

    'r36/trust_robot_r36_gyro_windows_dev_v1/r36_gyro_windows.py':
        'bd06da40051d6c167b253322ba55a8655269110481f8b89e675493aaac430afa',
    'r36/trust_robot_r36_gyro_windows_dev_v1/r36_independent_verify.py':
        'eb2a52f5f8168070dc015a9fdd17d50f6a9ffbcc8ff97b48a000a7b018a9b645',
    'r36/trust_robot_r36_gyro_windows_dev_v1/test_r36.py':
        '7f17e0dd25a8ff20f42f2651fe69964193908c41ec27b8c6d55a9b06151eebd2',
    'r36/trust_robot_r36_gyro_windows_result_v1/r36_gyro_window_candidates_v1.json':
        'c025f71eeb8a8467c0ca86cbec079d1bf0d977841d25140750d813d89a54714a',
    'r36/trust_robot_r36_gyro_windows_result_v1/r36_independent_validation_v1.json':
        '81acef17dc943327a69ee202839eae83565d20276bb3fbb0b0479d3d2e2df980'
}

PHASE_COUNTS = {
    'r33': 7,
    'r34': 4,
    'r35': 5,
    'r36': 5
}

GATES = (
    'physical_capture_time_verified',
    'cross_modal_alignment_performed',
    'full_extrinsics_verified',
    'health_model_training_authorized',
    'real_sensor_factor_execution_authorized',
    'm2dgr_scoring_authorized',
    'ground_truth_scored',
    'statistical_stability_established',
    'raw_recording_modified',
    'github_modified'
)

def need(ok, why):
    if not ok:
        raise ValueError('R37_DENIED:' + why)

def digest(path):
    return hashlib.sha256(
        pathlib.Path(path).read_bytes()
    ).hexdigest()

def load(path):
    return json.loads(pathlib.Path(path).read_text())

def path_for(root, key):
    return root / key.split('/', 1)[1]

def item(root, name):
    found = [
        key for key in PINS
        if key.endswith('/' + name)
    ]

    need(len(found) == 1, 'UNIQUE_ITEM:' + name)

    return path_for(root, found[0])

def source_audit(root):
    need(
        len(PINS) == 21
        and {
            k: sum(
                p.startswith(k + '/')
                for p in PINS
            )
            for k in PHASE_COUNTS
        } == PHASE_COUNTS,
        'PIN_COUNTS'
    )

    for key, expected in PINS.items():
        path = path_for(root, key)

        need(
            path.is_file()
            and not path.is_symlink()
            and path.stat().st_nlink == 1
            and 0 < path.stat().st_size < 4_000_000,
            'UNSAFE_SOURCE:' + key
        )

        need(
            digest(path) == expected,
            'SOURCE_SHA:' + key
        )

        if path.suffix == '.json':
            load(path)

        if (
            path.name.endswith('.py')
            or path.name.endswith('.py.saved')
        ):
            ast.parse(
                path.read_text(),
                filename=str(path)
            )

def gates(report, keys, label):
    for key in keys:
        need(
            report.get(key) is False,
            label + ':' + key
        )

def policy(report):
    need(
        report.get('schema') ==
        'TRUST_ROBOT_R37_R33_R36_NONFACTOR_CHECKPOINT_READINESS_V1'
        and report.get('trajectory_id') == 'room_02'
        and report.get('split') == 'train'
        and report.get('github_parent_commit') == BASE
        and report.get('authenticated_bag_sha256') == BAG,
        'READINESS_SCOPE'
    )

    need(
        report.get('phase_counts') == PHASE_COUNTS
        and report.get('source_sha256') == PINS
        and report.get('off_git_artifact_count') == 21,
        'FROZEN_FILES'
    )

    need(
        report.get('readiness_decision') ==
        'READY_FOR_SHA_PINNED_R33_R37_NONFACTOR_GITHUB_CHECKPOINT'
        and report.get('raw_bag_archived') is False,
        'READINESS_DECISION'
    )

    gates(report, GATES, 'SCIENCE')

    for key in (
        'scientific_pose_factors',
        'health_labels',
        'pose_accuracy_scores'
    ):
        need(
            type(report.get(key)) is int
            and report[key] == 0,
            'SCIENTIFIC_COUNT:' + key
        )

    observed = report.get('observations', {})

    need(
        observed.get('camera_pairs') == 8
        and observed.get('camera_frames') == 16
        and observed.get('imu_short_intervals') == 16
        and observed.get('imu_short_messages') == 32
        and observed.get('imu_gyro_windows') == 16
        and observed.get('imu_gyro_messages') == 48
        and observed.get('imu_gyro_intervals') == 32,
        'OBSERVATION_COUNTS'
    )

def review(root, repository, destination):
    source_audit(root)

    r33 = load(item(
        root, 'r33_camera_multipair_pixel_diagnostics_v1.json'
    ))
    v33 = load(item(
        root, 'r33_independent_validation_v1.json'
    ))
    repair = load(item(
        root, 'r33_failed_baseline_repair_provenance_v1.json'
    ))

    r34 = load(item(
        root, 'r34_imu_short_interval_diagnostics_v1.json'
    ))
    v34 = load(item(
        root, 'r34_independent_validation_v1.json'
    ))

    r35 = load(item(
        root, 'r35_imu_variation_frame_v1.json'
    ))
    v35 = load(item(
        root, 'r35_independent_validation_v1.json'
    ))

    r36 = load(item(
        root, 'r36_gyro_window_candidates_v1.json'
    ))
    v36 = load(item(
        root, 'r36_independent_validation_v1.json'
    ))

    r17_path = (
        repository /
        'experiments/trust_robot_r17_r20_recorded_input_checkpoint_v1/r17/r17_recorded_index.json'
    )
    r18_path = (
        repository /
        'experiments/trust_robot_r17_r20_recorded_input_checkpoint_v1/r18/r18_bounded_recorded_samples.json'
    )
    r31_path = (
        repository /
        'experiments/trust_robot_r27_r31_recorded_motion_checkpoint_v1/r31/r31_camera_pixel_motion_v1.json'
    )

    need(
        digest(r17_path) ==
        '4e904e29f507519e4447642edec55954b672aae2c305ff513bd6aa857c92a5af',
        'R17_PIN'
    )
    need(
        digest(r18_path) ==
        '68accc1d4ab7b4c131bd60767be249054ba2469fad266292f615b6619d969bfa',
        'R18_PIN'
    )
    need(
        digest(r31_path) ==
        'f04d6c1ecda049edea612dea9214ccb4c22355b37585e64a0a9169db8f355470',
        'R31_PIN'
    )

    r31 = load(r31_path)

    reports = [r33, r34, r35, r36]

    need(
        all(
            x.get('trajectory_id') == 'room_02'
            and x.get('split') == 'train'
            and x.get('authenticated_bag_sha256') == BAG
            and x.get('github_baseline') == BASE
            for x in reports
        ),
        'RECORDED_TRAIN_CHAIN'
    )

    for name, report in zip(
        ('R33', 'R34', 'R35', 'R36'),
        reports
    ):
        gates(
            report,
            (
                'real_sensor_factor_execution_authorized',
                'health_model_training_authorized',
                'physical_capture_time_verified',
                'cross_modal_alignment_performed',
                'full_extrinsics_verified',
                'm2dgr_scoring_authorized',
                'raw_recording_modified',
                'github_modified'
            ),
            name
        )

        need(
            type(report.get('real_pose_factors_generated')) is int
            and report['real_pose_factors_generated'] == 0
            and type(report.get('health_labels_generated')) is int
            and report['health_labels_generated'] == 0,
            'NONFACTOR:' + name
        )

    proof_rows = (
        (
            'r33_camera_multipair_pixel_diagnostics_v1.json',
            v33, 'source_report_sha256'
        ),
        (
            'r34_imu_short_interval_diagnostics_v1.json',
            v34, 'source_report_sha256'
        ),
        (
            'r35_imu_variation_frame_v1.json',
            v35, 'r35_report_sha256'
        ),
        (
            'r36_gyro_window_candidates_v1.json',
            v36, 'source_report_sha256'
        )
    )

    for filename, validation, key in proof_rows:
        need(
            validation[key] == digest(item(root, filename)),
            'INDEPENDENT_PROOF:' + filename
        )

    need(
        r33['source_report_sha256'] == {
            'r17': digest(r17_path),
            'r18': digest(r18_path),
            'r31': digest(r31_path)
        }
        and v33['recorded_camera_messages_verified'] == 16
        and v33['independently_recomputed_pair_tracks'] == 8
        and v33['r31_baseline_identical'] is True
        and v33['independently_reconstructed_index_schedule'] is True,
        'R33_SOURCE_REPLAY'
    )

    need(
        r33['pair_count'] == 8
        and r33['frames_inspected'] == 16
        and len(r33['pairs']) == 8
        and [
            p['pair_index'] for p in r33['pairs']
        ] == list(range(8)),
        'R33_COUNTS'
    )

    need(
        r33['pairs'][0]['pixel_motion'] == r31['pixel_motion']
        and all(
            all(
                r33['pairs'][0]['frames'][i].get(key) == value
                for key, value in r31['frames'][i].items()
            )
            for i in range(2)
        ),
        'R31_EXACT_BASELINE'
    )

    for pair in r33['pairs']:
        motion = pair['pixel_motion']

        need(
            motion['metric_translation_m'] is None
            and motion['camera_pose_factor'] is None
            and motion['camera_rotation_radians'] is None
            and pair['metric_pose_qualified'] is False,
            'CAMERA_NOT_POSE'
        )

        need(
            0 <= motion['forward_backward_consistent_count']
            <= motion['initial_corner_count'] <= 400,
            'CAMERA_TRACKS'
        )

    need(
        repair['schema'] ==
        'TRUST_ROBOT_R33_R31_FRAME_METADATA_COMPATIBILITY_REPAIR_V1'
        and repair['original_bag_modified'] is False
        and repair['git_modified'] is False
        and repair['real_pose_factors_authorized'] is False,
        'REPAIR_PROVENANCE'
    )

    for name in (
        'r33_camera_multipair.py',
        'r33_independent_verify.py'
    ):
        evidence = repair['readers'][name]
        failed_name = name.replace(
            '.py', '_initial_failed_v1.py.saved'
        )

        need(
            evidence['failed_sha256'] ==
                digest(item(root, failed_name))
            and evidence['repaired_sha256'] ==
                digest(item(root, name))
            and evidence['failed_backup'] == failed_name,
            'R33_FAILURE_PRESERVATION'
        )

    need(
        r34['source_report_sha256']['r33'] ==
        digest(item(
            root, 'r33_camera_multipair_pixel_diagnostics_v1.json'
        ))
        and r34['stream_count'] == 2
        and r34['pairs_per_stream'] == 8
        and r34['serialized_imu_messages_inspected'] == 32
        and v34['original_imu_messages_relocated'] == 32
        and v34['independent_trapezoid_intervals_recomputed'] == 16,
        'R34_PROOF'
    )

    need(
        r35['r34_source_report_sha256'] ==
        digest(item(
            root, 'r34_imu_short_interval_diagnostics_v1.json'
        ))
        and r35['r34_independent_validation_sha256'] ==
        digest(item(
            root, 'r34_independent_validation_v1.json'
        ))
        and r35['r34_engine_source_sha256'] ==
        digest(item(root, 'r34_imu.py'))
        and r35['r34_independent_verifier_source_sha256'] ==
        digest(item(root, 'r34_independent_verify.py')),
        'R35_SOURCE_CHAIN'
    )

    need(
        r35['stream_count'] == 2
        and r35['interval_count'] == 16
        and r35['previously_authenticated_messages_represented'] == 32
        and r35['r35_reopened_raw_rosbag'] is False
        and v35['intervals_independently_recomputed'] == 16
        and v35['raw_bag_reopened'] is False,
        'R35_PROOF'
    )

    need(
        r36['source_report_sha256'] == {
            'r17': digest(r17_path),
            'r34': digest(item(
                root, 'r34_imu_short_interval_diagnostics_v1.json'
            )),
            'r35': digest(item(
                root, 'r35_imu_variation_frame_v1.json'
            ))
        },
        'R36_SOURCE_CHAIN'
    )

    need(
        r36['window_count_per_stream'] == 8
        and r36['source_message_count'] == 48
        and r36['total_time_intervals'] == 32
        and v36['authentic_imu_messages_relocated'] == 48
        and v36['independently_recomputed_three_sample_windows'] == 16
        and v36['numerical_rotation_crosscheck'] ==
        'PURE_PYTHON_QUATERNIONS_MATCH_SCIPY_SO3',
        'R36_PROOF'
    )

    for topic, frame, unknown in (
        (TOPICS[0], FRAMES[TOPICS[0]], 16),
        (TOPICS[1], FRAMES[TOPICS[1]], 0)
    ):
        need(
            r35['streams'][topic]['recorded_frame_id'] == frame
            and r35['streams'][topic]['summary'][
                'orientation_covariance_unknown_samples'
            ] == unknown,
            'IMU_FRAME_AND_ORIENTATION'
        )

        need(
            len(r34['streams'][topic]) == 8
            and len(r35['streams'][topic]['intervals']) == 8
            and len(r36['streams'][topic]) == 8,
            'IMU_INTERVAL_COUNTS'
        )

        for window in r36['streams'][topic]:
            numeric = window['gyro_numerics']

            need(
                window['physically_qualified_rotation'] is False
                and numeric['factor'] is None
                and numeric['velocity_m_s'] is None
                and numeric['translation_m'] is None,
                'GYRO_NONFACTOR'
            )

    result = {
        'schema':
            'TRUST_ROBOT_R37_R33_R36_NONFACTOR_CHECKPOINT_READINESS_V1',
        'trajectory_id': 'room_02',
        'split': 'train',
        'github_parent_commit': BASE,
        'authenticated_bag_sha256': BAG,
        'phase_counts': PHASE_COUNTS,
        'source_sha256': PINS,
        'off_git_artifact_count': 21,
        'raw_bag_archived': False,
        'readiness_decision':
            'READY_FOR_SHA_PINNED_R33_R37_NONFACTOR_GITHUB_CHECKPOINT',
        'observations': {
            'camera_pairs': 8,
            'camera_frames': 16,
            'imu_short_intervals': 16,
            'imu_short_messages': 32,
            'imu_gyro_windows': 16,
            'imu_gyro_messages': 48,
            'imu_gyro_intervals': 32
        },
        'recorded_orientation_sentinel_counts': {
            'camera_imu_unknown': 16,
            'handsfree_imu_unknown': 0
        },
        'r33_original_failure_and_repair_preserved': True,
        'independent_provenance_replays': 4,
        'interpretation':
            'sha_frozen_nonfactor_development_archival_only_no_pose_accuracy_or_health_training',
        'scientific_pose_factors': 0,
        'health_labels': 0,
        'pose_accuracy_scores': 0,
        **{key: False for key in GATES}
    }

    policy(result)

    with destination.open('x', encoding='utf-8') as f:
        json.dump(
            result,
            f,
            indent=2,
            sort_keys=True,
            allow_nan=False
        )
        f.write('\n')

    print('R37_FROZEN_R33_R36_ARTIFACTS=21_SHA256_PINNED')
    print('R37_R33_ORIGINAL_FAILURE_AND_TARGETED_REPAIR=PRESERVED')
    print('R37_R33_R36_SOURCE_AND_INDEPENDENT_REPORT_LINKS=VERIFIED')
    print('R37_SCIENTIFIC_CHECKPOINT_READINESS=NONFACTOR_ONLY')

if __name__ == '__main__':
    review(
        *(pathlib.Path(x) for x in sys.argv[1:4])
    )
