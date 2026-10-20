"""Audit TRAIN room_02 ROS1 connection metadata, not sensor payloads."""

import hashlib
import json
import pathlib
import struct
import sys

import r18_decode as ros

BASE = 'df78336320b3b026e448a09d39dfc571f922ae00'
BAG = 'ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1'

SCHEMA = 'TRUST_ROBOT_R42_TRAIN_ROS_CONNECTION_CALIBRATION_GAP_V1'

TOPIC_DENY = (
    'sensor_msgs/CameraInfo',
    'tf2_msgs/TFMessage',
    'geometry_msgs/TransformStamped',
    'nav_msgs/Odometry',
    'geometry_msgs/PoseStamped',
    'geometry_msgs/PoseWithCovarianceStamped'
)

CLOSED = (
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
    'm2dgr_ate_rpe_authorized'
)

def need(ok, reason):
    if not ok:
        raise ValueError('R42_DENIED:' + reason)

def sha(blob):
    return hashlib.sha256(blob).hexdigest()

def load(path):
    return json.loads(pathlib.Path(path).read_text())

def connections(bag, index):
    frozen = {
        item['id']: item
        for item in index['connections']
    }

    need(
        len(frozen) == 15
        and index['connection_count'] == 15,
        'FROZEN_CONNECTION_COUNT'
    )

    records = []

    with bag.open('rb') as f:
        need(
            ros.read_exact(f, 13) == b'#ROSBAG V2.0\n',
            'ROS1_MAGIC'
        )

        header, _ = ros.file_record(f, 8192)

        need(
            header.get(b'op') == b'\x03',
            'ROS1_FILE_HEADER'
        )

        position = struct.unpack(
            '<Q', header[b'index_pos']
        )[0]

        need(
            position == index['index_position']
            and position > 0,
            'INDEX_POSITION'
        )

        f.seek(position)

        for _ in range(15):
            h, data = ros.file_record(f, 250000)

            need(
                h.get(b'op') == b'\x07',
                'CONNECTION_RECORD'
            )

            cid = ros.u32(h[b'conn'])

            need(
                cid in frozen,
                'UNKNOWN_CONNECTION'
            )

            metadata = ros.field_map(data)
            previous = frozen[cid]

            need(
                h[b'topic'].decode('utf-8')
                == previous['topic'],
                'CONNECTION_TOPIC'
            )

            need(
                metadata[b'type'].decode('utf-8')
                == previous['message_type'],
                'CONNECTION_TYPE'
            )

            need(
                metadata[b'md5sum'].decode('ascii')
                == previous['md5sum'],
                'CONNECTION_MD5'
            )

            need(
                sha(metadata[b'message_definition'])
                == previous['message_definition_sha256'],
                'MESSAGE_DEFINITION'
            )

            records.append({
                'connection_id': cid,
                'topic': previous['topic'],
                'message_type': previous['message_type'],
                'message_definition_sha256':
                    previous['message_definition_sha256'],
                'connection_metadata_keys': sorted(
                    k.decode('ascii')
                    for k in metadata
                ),
                'physical_calibration_values_qualified': False
            })

    need(
        len({
            item['connection_id']
            for item in records
        }) == 15,
        'UNIQUE_CONNECTION_COUNT'
    )

    return sorted(
        records,
        key=lambda item: item['connection_id']
    )

def policy(report):
    need(
        report.get('schema') == SCHEMA
        and report.get('trajectory_id') == 'room_02'
        and report.get('split') == 'train'
        and report.get('github_baseline') == BASE
        and report.get('source_bag_sha256') == BAG,
        'SCOPE'
    )

    need(
        report.get('recording_header_and_connection_records_read')
            is True
        and report.get('sensor_payload_decompressed') is False
        and report.get('sensor_messages_decoded') == 0
        and report.get('confirmation_test_accessed') is False
        and report.get('github_modified') is False,
        'ACCESS_BOUNDARY'
    )

    need(
        report.get('connection_count') == 15
        and len(report.get('connections', [])) == 15
        and report.get('camera_info_topic_count') == 0
        and report.get('tf_topic_count') == 0
        and report.get('mocap_or_pose_reference_topic_count') == 0,
        'TOPIC_COUNTS'
    )

    need(
        [
            item.get('connection_id')
            for item in report['connections']
        ] == list(range(15)),
        'CONNECTION_ORDER'
    )

    need(
        not any(
            item['message_type'] in TOPIC_DENY
            or item['topic'] in ('/tf', '/tf_static')
            for item in report['connections']
        ),
        'UNEXPECTED_REFERENCE_OR_CALIBRATION_TOPIC'
    )

    need(
        all(
            item['physical_calibration_values_qualified'] is False
            for item in report['connections']
        ),
        'NO_CALIBRATION_PROMOTION'
    )

    need(
        report.get('r40_local_calibration_candidate_count') == 10
        and report.get('r41_local_reference_candidate_count') == 0
        and report.get('r41_frozen_reference_content_matches') == 0,
        'UPSTREAM_INVENTORY'
    )

    need(
        report.get(
            'author_relative_imu_rotation_supported_but_full_extrinsic_verified'
        ) is False,
        'PARTIAL_ROTATION_NOT_FULL_EXTRINSIC'
    )

    need(
        report.get('reference_mocap_invalid_rotation_count') == 90,
        'REFERENCE_QUALITY'
    )

    need(
        set(report.get('unresolved_requirements', {}))
        == set(CLOSED)
        and all(
            value == 'NOT_PHYSICALLY_QUALIFIED'
            for value in report['unresolved_requirements'].values()
        ),
        'SCIENTIFIC_GATES'
    )

    need(
        report.get('qualified_pose_factors') == 0
        and report.get('health_labels') == 0
        and report.get('ate_rpe_scores') == 0,
        'ZERO_SCIENTIFIC_OUTPUTS'
    )

    need(
        report.get('next_phase') ==
        'R43_TRAIN_REFERENCE_CALIBRATION_SOURCE_ACQUISITION_PROTOCOL',
        'NEXT_PHASE'
    )

def run(repo, bag, r17p, r40p, r41p, out, md):
    index = load(r17p)
    r40 = load(r40p)
    r41 = load(r41p)

    need(
        index['schema'] ==
        'TRUST_ROBOT_R17_ROS1_INDEX_READONLY_V1'
        and index['trajectory_id'] == 'room_02'
        and index['split'] == 'train'
        and index['file_sha256'] == BAG,
        'R17_SOURCE'
    )

    need(
        r40['trajectory_id'] == r41['trajectory_id'] == 'room_02'
        and r40['split'] == r41['split'] == 'train',
        'UPSTREAM_SCOPE'
    )

    need(
        r40['raw_bag_opened'] is False
        and r41['raw_bag_opened'] is False,
        'UPSTREAM_PAYLOAD'
    )

    need(
        len(r40['candidate_files']) == 10
        and len(r41['configuration_semantics']) == 10,
        'TEN_SOFTWARE_CONFIGS'
    )

    need(
        len(r41['room_02_reference_file_candidates']) == 0
        and r41['matching_frozen_reference_payload_count'] == 0,
        'REFERENCE_NOT_LOCALLY_DISCOVERED'
    )

    calib_path = (
        repo / 'manifests/m2dgr_calibration_evidence_v1.json'
    )

    physical_path = (
        repo /
        'manifests/m2dgr_reference_physical_semantics_evidence_v1.json'
    )

    calibration = load(calib_path)
    reference = load(physical_path)

    interpretation = calibration['interpretation']

    prior = calibration[
        'observations'
    ]['author_calibration_provenance']

    need(
        interpretation['camera_intrinsics_verified'] is False
        and interpretation[
            'camera_lidar_extrinsic_verified'
        ] is False
        and interpretation['dataset_calibration_verified'] is False,
        'PRIOR_CALIBRATION_GATES'
    )

    need(
        interpretation[
            'd435i_imu_relative_rotation_has_independent_released_sensor_content_support'
        ] is True
        and interpretation[
            'd435i_imu_relative_rotation_support_is_full_extrinsic_verification'
        ] is False,
        'SUPPORTED_PARTIAL_ROTATION'
    )

    need(
        prior[
            'released_bag_camera_info_or_calibration_like_topic_present_count'
        ] == 0
        and prior['released_bag_tf_present_count'] == 0
        and prior['released_bag_tf_static_present_count'] == 0,
        'PRIOR_CONNECTION_EVIDENCE'
    )

    physical = reference['interpretation']

    need(
        physical['mocap_reference_body_origin_verified'] is False
        and physical['mocap_to_lidar_transform_verified'] is False
        and physical[
            'reference_timestamp_physical_measurement_event_verified'
        ] is False,
        'MOCAP_GEOMETRY_AND_CLOCK'
    )

    records = connections(bag, index)

    classified = {
        'camera_info_topic_count': sum(
            item['message_type'] == 'sensor_msgs/CameraInfo'
            for item in records
        ),
        'tf_topic_count': sum(
            item['topic'] in ('/tf', '/tf_static')
            or item['message_type'] == 'tf2_msgs/TFMessage'
            for item in records
        ),
        'mocap_or_pose_reference_topic_count': sum(
            item['message_type'] in (
                'geometry_msgs/PoseStamped',
                'geometry_msgs/PoseWithCovarianceStamped',
                'nav_msgs/Odometry'
            )
            or any(
                name in item['topic'].lower()
                for name in (
                    'mocap', 'ground_truth', 'groundtruth'
                )
            )
            for item in records
        )
    }

    need(
        all(value == 0 for value in classified.values()),
        'UNEXPECTED_CALIBRATION_TOPIC'
    )

    report = {
        'schema': SCHEMA,
        'trajectory_id': 'room_02',
        'split': 'train',
        'github_baseline': BASE,
        'source_bag_sha256': BAG,
        'source_sha256': {
            'r17': sha(r17p.read_bytes()),
            'r40': sha(r40p.read_bytes()),
            'r41': sha(r41p.read_bytes()),
            'calibration_evidence': sha(calib_path.read_bytes()),
            'reference_semantics': sha(physical_path.read_bytes())
        },
        'connection_count': 15,
        'connections': records,
        **classified,
        'r40_local_calibration_candidate_count': 10,
        'r41_local_reference_candidate_count': 0,
        'r41_frozen_reference_content_matches': 0,
        'author_relative_imu_rotation_supported_but_full_extrinsic_verified':
            False,
        'reference_mocap_invalid_rotation_count': 90,
        'unresolved_requirements': {
            requirement: 'NOT_PHYSICALLY_QUALIFIED'
            for requirement in CLOSED
        },
        'interpretation':
            'The fifteen ROS1 connection types do not expose CameraInfo, '
            'TF or mocap reference topics; message definitions and '
            'publisher metadata are not physical calibration or '
            'capture-clock certification.',
        'recording_header_and_connection_records_read': True,
        'sensor_payload_decompressed': False,
        'sensor_messages_decoded': 0,
        'confirmation_test_accessed': False,
        'github_modified': False,
        'qualified_pose_factors': 0,
        'health_labels': 0,
        'ate_rpe_scores': 0,
        'next_phase':
            'R43_TRAIN_REFERENCE_CALIBRATION_SOURCE_ACQUISITION_PROTOCOL'
    }

    policy(report)

    with out.open('x') as f:
        json.dump(
            report, f,
            sort_keys=True,
            indent=2,
            allow_nan=False
        )
        f.write('\n')

    lines = [
        '# R42 — TRAIN room_02 connection-level calibration gap resolution',
        '',
        'All 15 recorded connection headers matched the frozen R17 '
        'topic, type, MD5 and message-definition SHA256 receipts.',
        '',
        'No sensor-message payload was decompressed.',
        '',
        '## Direct bounded evidence',
        '',
        '- CameraInfo topic count: 0.',
        '- TF / TF-static topic count: 0.',
        '- Mocap or pose-reference topic count: 0.',
        '- R41 found no local room_02 reference-file candidate.',
        '- R41 verified ten software configuration files; none '
        'qualifies physical sensor calibration.',
        '- Existing M2DGR evidence supports a candidate D435i IMU '
        'relative rotation, not a complete physical extrinsic.',
        '- The room_02 mocap index reports 90 invalid rotation '
        'records. Reference body origin and physical timestamp '
        'semantics remain unverified.',
        '',
        'A missing ROS topic does not prove that external '
        'calibration data never existed.',
        '',
        '## Unresolved scientific requirements',
        ''
    ]

    for requirement in CLOSED:
        lines.append(
            '- ' + requirement.replace('_', ' ')
            + ': **NOT PHYSICALLY QUALIFIED**.'
        )

    lines += [
        '',
        '## R43 — Next evidence requirement',
        '',
        'Prepare a physically traceable calibration and reference '
        'acquisition protocol covering camera intrinsics, sensor '
        'extrinsic transform direction and translation, capture-clock '
        'mapping, mocap reference geometry, reference-file receipts '
        'and independent validation.',
        '',
        'No confirmation-test data, pose factors, health labels '
        'or GitHub changes were authorized.',
        ''
    ]

    with md.open('x') as f:
        f.write('\n'.join(lines))

    print('R42_AUTHENTIC_ROS1_CONNECTION_HEADERS=15_SHA_MATCHED')
    print('R42_CAMERAINFO_TOPIC_COUNT=0')
    print('R42_TF_TFSTATIC_TOPIC_COUNT=0')
    print('R42_MOCAP_REFERENCE_TOPIC_COUNT=0')
    print('R42_REFERENCE_FILE_LOCALLY_DISCOVERED=NO')
    print(
        'R42_PHYSICAL_QUALIFICATION_GATES=%d_CLOSED'
        % len(CLOSED)
    )
    print('R42_SENSOR_MESSAGES_DECOMPRESSED=0')

if __name__ == '__main__':
    run(
        *(pathlib.Path(p) for p in sys.argv[1:8])
    )
