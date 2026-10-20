"""Independent binary ROS1 connection parser; no sensor messages."""

import hashlib
import json
import pathlib
import struct
import sys

BASE = 'df78336320b3b026e448a09d39dfc571f922ae00'

def need(ok, reason):
    if not ok:
        raise ValueError('R42_INDEPENDENT_DENIED:' + reason)

def sha(blob):
    return hashlib.sha256(blob).hexdigest()

def load(path):
    return json.loads(pathlib.Path(path).read_text())

def parse_fields(data):
    cursor = 0
    fields = {}

    while cursor < len(data):
        need(
            cursor + 4 <= len(data),
            'FIELD_TRUNCATED'
        )

        size, = struct.unpack_from(
            '<I', data, cursor
        )

        cursor += 4

        need(
            0 < size <= len(data) - cursor,
            'FIELD_SIZE'
        )

        field = data[cursor:cursor+size]
        cursor += size

        key, separator, value = field.partition(b'=')

        need(
            bool(separator)
            and bool(key)
            and key not in fields,
            'FIELD_FORMAT'
        )

        fields[key] = value

    return fields

def next_record(f, limit):
    header_size = f.read(4)

    need(
        len(header_size) == 4,
        'RECORD_HEADER_SIZE'
    )

    n, = struct.unpack('<I', header_size)

    need(
        0 < n <= 100000,
        'HEADER_BOUNDS'
    )

    header = f.read(n)

    need(
        len(header) == n,
        'HEADER_TRUNCATED'
    )

    data_size = f.read(4)

    need(
        len(data_size) == 4,
        'DATA_SIZE_TRUNCATED'
    )

    size, = struct.unpack('<I', data_size)

    need(
        size <= limit,
        'DATA_BOUNDS'
    )

    body = f.read(size)

    need(
        len(body) == size,
        'DATA_TRUNCATED'
    )

    return parse_fields(header), body

def verify(bag, r17p, r40p, r41p, sourcep, planp, out):
    prior = load(r17p)
    r40 = load(r40p)
    r41 = load(r41p)
    result = load(sourcep)

    need(
        result['schema'] ==
        'TRUST_ROBOT_R42_TRAIN_ROS_CONNECTION_CALIBRATION_GAP_V1'
        and result['split'] == 'train'
        and result['trajectory_id'] == 'room_02'
        and result['github_baseline'] == BASE,
        'REPORT_SCOPE'
    )

    need(
        result['source_sha256']['r17'] == sha(r17p.read_bytes())
        and result['source_sha256']['r40'] == sha(r40p.read_bytes())
        and result['source_sha256']['r41'] == sha(r41p.read_bytes()),
        'SOURCE_LINK'
    )

    records = []

    with bag.open('rb') as f:
        need(
            f.read(13) == b'#ROSBAG V2.0\n',
            'BAG_MAGIC'
        )

        header, _ = next_record(f, 8192)

        need(
            header.get(b'op') == b'\x03',
            'FILE_HEADER'
        )

        position, = struct.unpack(
            '<Q', header[b'index_pos']
        )

        need(
            position == prior['index_position'],
            'INDEX_POSITION'
        )

        f.seek(position)

        for _ in range(15):
            h, data = next_record(f, 250000)

            need(
                h.get(b'op') == b'\x07',
                'CONNECTION_OP'
            )

            cid, = struct.unpack(
                '<I', h[b'conn']
            )

            metadata = parse_fields(data)

            need(
                cid in range(15),
                'CONNECTION_ID'
            )

            records.append({
                'connection_id': cid,
                'topic': h[b'topic'].decode('utf-8'),
                'message_type':
                    metadata[b'type'].decode('utf-8'),
                'message_definition_sha256':
                    sha(metadata[b'message_definition']),
                'connection_metadata_keys': sorted(
                    key.decode('ascii')
                    for key in metadata
                ),
                'physical_calibration_values_qualified': False
            })

    records.sort(
        key=lambda item: item['connection_id']
    )

    need(
        records == result['connections'],
        'INDEPENDENT_CONNECTION_REPLAY'
    )

    need(
        len(records) == prior['connection_count'] == 15,
        'CONNECTION_COUNT'
    )

    for record, frozen in zip(
        records, prior['connections']
    ):
        need(
            record['topic'] == frozen['topic']
            and record['message_type'] == frozen['message_type']
            and record['message_definition_sha256']
                == frozen['message_definition_sha256'],
            'FROZEN_CONNECTION_BINDING'
        )

    need(
        result['camera_info_topic_count'] == 0
        and result['tf_topic_count'] == 0
        and result['mocap_or_pose_reference_topic_count'] == 0,
        'CALIBRATION_TOPIC_COUNTS'
    )

    need(
        len(r40['candidate_files']) == 10
        and len(r41['configuration_semantics']) == 10
        and r41['matching_frozen_reference_payload_count'] == 0
        and len(r41['room_02_reference_file_candidates']) == 0,
        'UPSTREAM_DISCOVERY'
    )

    need(
        result['sensor_payload_decompressed'] is False
        and result['sensor_messages_decoded'] == 0
        and result['confirmation_test_accessed'] is False
        and result['github_modified'] is False,
        'SCIENCE_GATES'
    )

    need(
        result['qualified_pose_factors'] == 0
        and result['health_labels'] == 0
        and result['ate_rpe_scores'] == 0,
        'ZERO_FACTORS'
    )

    need(
        len(result['unresolved_requirements']) == 11
        and all(
            value == 'NOT_PHYSICALLY_QUALIFIED'
            for value in result['unresolved_requirements'].values()
        ),
        'ELEVEN_CLOSED_GATES'
    )

    need(
        planp.is_file()
        and 'NOT PHYSICALLY QUALIFIED' in planp.read_text()
        and 'R43' in planp.read_text(),
        'ACTION_PLAN'
    )

    evidence = {
        'schema':
            'TRUST_ROBOT_R42_INDEPENDENT_CONNECTION_METADATA_VALIDATION_V1',
        'source_report_sha256': sha(sourcep.read_bytes()),
        'plan_sha256': sha(planp.read_bytes()),
        'independently_parsed_original_connection_headers': len(records),
        'frozen_connection_source_match': True,
        'calibration_topics_revealed': 0,
        'sensor_payload_decompressed': False,
        'real_sensor_factors_authorized': False,
        'confirmation_test_accessed': False
    }

    with out.open('x') as f:
        json.dump(
            evidence, f,
            sort_keys=True,
            indent=2,
            allow_nan=False
        )
        f.write('\n')

    print('R42_INDEPENDENT_CONNECTION_HEADERS=15_BYTE_AND_SHA_MATCH')
    print('R42_INDEPENDENT_CALIBRATION_REFERENCE_TOPICS=0')
    print('R42_INDEPENDENT_VALIDATION=PASS')

if __name__ == '__main__':
    verify(
        *(pathlib.Path(p) for p in sys.argv[1:8])
    )
