"""Read-only ROS1 bag v2 index reader. Sensor payloads are not decoded."""
import hashlib
import json
from pathlib import Path
import struct
import sys

MAGIC = b'#ROSBAG V2.0\n'

TOPICS = {
    '/camera/color/image_raw/compressed': 'sensor_msgs/CompressedImage',
    '/camera/imu': 'sensor_msgs/Imu',
    '/handsfree/imu': 'sensor_msgs/Imu',
    '/velodyne_points': 'sensor_msgs/PointCloud2',
}

class BagIndexError(ValueError):
    pass

def need(condition, message):
    if not condition:
        raise BagIndexError('R17_INDEX_ERROR:' + message)

def exact(handle, size):
    data = handle.read(size)
    need(len(data) == size, 'TRUNCATED')
    return data

def u32(data):
    need(len(data) == 4, 'UINT32_LENGTH')
    return struct.unpack('<I', data)[0]

def u64(data):
    need(len(data) == 8, 'UINT64_LENGTH')
    return struct.unpack('<Q', data)[0]

def fields(blob):
    result = {}
    cursor = 0

    while cursor < len(blob):
        need(cursor + 4 <= len(blob), 'FIELD_LENGTH')
        size = u32(blob[cursor:cursor + 4])
        cursor += 4

        need(0 < size <= len(blob) - cursor, 'FIELD_BOUNDS')
        entry = blob[cursor:cursor + size]
        cursor += size

        need(b'=' in entry, 'FIELD_EQUALS')
        key, value = entry.split(b'=', 1)
        need(key and key not in result, 'DUPLICATE_FIELD')
        result[key] = value

    return result

def record(handle, max_data=8 * 1024 * 1024):
    header_size = u32(exact(handle, 4))
    need(0 < header_size <= 2 * 1024 * 1024, 'HEADER_SIZE')
    header = fields(exact(handle, header_size))

    data_size = u32(exact(handle, 4))
    need(data_size <= max_data, 'DATA_SIZE')
    return header, exact(handle, data_size)

def time_ns(data):
    need(len(data) == 8, 'TIME_LENGTH')
    seconds, nanoseconds = struct.unpack('<II', data)
    need(nanoseconds < 1_000_000_000, 'TIME_NANOSECONDS')
    return seconds * 1_000_000_000 + nanoseconds

def read_index(path):
    path = Path(path)

    need(
        path.is_file()
        and not path.is_symlink()
        and path.stat().st_nlink == 1,
        'UNSAFE_SOURCE'
    )

    file_size = path.stat().st_size

    with path.open('rb') as handle:
        need(exact(handle, len(MAGIC)) == MAGIC, 'BAG_VERSION')

        header, _ = record(handle, max_data=8192)
        need(header.get(b'op') == b'\x03', 'FILE_HEADER_OP')

        index_pos = u64(header[b'index_pos'])
        connection_count = u32(header[b'conn_count'])
        chunk_count = u32(header[b'chunk_count'])

        need(
            0 < connection_count <= 10000
            and 0 < chunk_count <= 1000000,
            'INDEX_LIMITS'
        )

        need(
            handle.tell() < index_pos < file_size,
            'UNINDEXED_OR_INVALID_OFFSET'
        )

        handle.seek(index_pos)
        connections = {}

        for _ in range(connection_count):
            h, data = record(handle)
            need(h.get(b'op') == b'\x07', 'CONNECTION_OP')

            connection = u32(h[b'conn'])
            need(connection not in connections, 'DUPLICATE_CONNECTION')

            topic = h[b'topic'].decode('utf-8')
            metadata = fields(data)
            message_type = metadata[b'type'].decode('utf-8')

            need(
                topic.startswith('/')
                and len(topic) <= 512
                and len(message_type) <= 512,
                'TOPIC_IDENTITY'
            )

            need(
                b'md5sum' in metadata
                and b'message_definition' in metadata,
                'MESSAGE_DEFINITION'
            )

            connections[connection] = {
                'id': connection,
                'topic': topic,
                'message_type': message_type,
                'md5sum': metadata[b'md5sum'].decode('ascii'),
                'message_definition_sha256': hashlib.sha256(
                    metadata[b'message_definition']
                ).hexdigest(),
            }

        counts = {key: 0 for key in connections}
        earliest = None
        latest = None
        previous_chunk = -1

        for _ in range(chunk_count):
            h, data = record(handle)
            need(h.get(b'op') == b'\x06', 'CHUNK_INFO_OP')
            need(u32(h[b'ver']) == 1, 'CHUNK_INFO_VERSION')

            position = u64(h[b'chunk_pos'])
            n = u32(h[b'count'])

            need(
                previous_chunk < position < index_pos,
                'CHUNK_POSITION'
            )
            previous_chunk = position

            start = time_ns(h[b'start_time'])
            end = time_ns(h[b'end_time'])
            need(start <= end, 'CHUNK_TIME_ORDER')

            earliest = start if earliest is None else min(earliest, start)
            latest = end if latest is None else max(latest, end)

            need(len(data) == 8 * n, 'CHUNK_COUNTS_SIZE')
            seen = set()

            for j in range(n):
                connection, count = struct.unpack_from('<II', data, 8 * j)
                need(
                    connection in counts
                    and connection not in seen
                    and count > 0,
                    'CHUNK_CONNECTION'
                )
                seen.add(connection)
                counts[connection] += count

        need(handle.tell() == file_size, 'INDEX_TRAILING_BYTES')

    topics = {}

    for connection, metadata in connections.items():
        name = metadata['topic']
        item = topics.setdefault(
            name,
            {'record_count': 0, 'types': set(), 'connections': []}
        )

        item['record_count'] += counts[connection]
        item['types'].add(metadata['message_type'])
        item['connections'].append(connection)

    for name, expected_type in TOPICS.items():
        need(
            name in topics
            and topics[name]['record_count'] > 0,
            'MISSING_REQUIRED_TOPIC:' + name
        )
        need(
            topics[name]['types'] == {expected_type},
            'UNEXPECTED_MESSAGE_TYPE:' + name
        )

    for item in topics.values():
        item['types'] = sorted(item['types'])
        item['connections'].sort()

    return {
        'bag_version': '2.0',
        'size_bytes': file_size,
        'index_position': index_pos,
        'connection_count': connection_count,
        'chunk_count': chunk_count,
        'bag_record_window_start_ns': earliest,
        'bag_record_window_end_ns': latest,
        'bag_record_time_is_capture_time_proof': False,
        'connections': sorted(
            connections.values(), key=lambda item: item['id']
        ),
        'topic_inventory': dict(sorted(topics.items())),
        'required_stream_counts': {
            name: topics[name]['record_count']
            for name in TOPICS
        },
    }

def full_sha(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(
            lambda: handle.read(8 * 1024 * 1024), b''
        ):
            digest.update(block)
    return digest.hexdigest()

def main():
    bag = Path(sys.argv[1])
    manifest = Path(sys.argv[2])
    expected = sys.argv[3]
    output = Path(sys.argv[4])

    source = json.loads(manifest.read_text())

    selected = [
        item for item in source['records']
        if item['trajectory_id'] == 'room_02'
    ]

    need(
        len(selected) == 1
        and selected[0]['split'] == 'train',
        'FROZEN_TRAIN'
    )

    artifacts = [
        item for item in selected[0]['calibration_artifacts']
        if item.get('source_path') == 'raw/rosbags/room_02.bag'
    ]

    need(
        len(artifacts) == 1
        and artifacts[0]['sha256'] == expected,
        'FROZEN_SOURCE_PIN'
    )

    actual = full_sha(bag)
    need(actual == expected, 'BAG_SHA256_MISMATCH')

    result = read_index(bag)

    result.update({
        'schema': 'TRUST_ROBOT_R17_ROS1_INDEX_READONLY_V1',
        'trajectory_id': 'room_02',
        'split': 'train',
        'file_sha256': actual,
        'frozen_manifest_sha256': full_sha(manifest),
        'recorded_sensor_payload_decoded': False,
        'messages_decompressed': 0,
        'real_pose_factors_generated': 0,
        'physical_sync_verified': False,
        'physical_extrinsics_verified': False,
        'health_labels': 0,
        'git_modified': False,
        'source_file_modified': False,
    })

    with output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write('\n')

    print('R17_BAG_SHA256=VERIFIED')
    print('R17_ROS1_INDEX=READ_ONLY_VALIDATED')
    print('R17_CONNECTIONS=' + str(result['connection_count']))
    print('R17_CHUNKS=' + str(result['chunk_count']))
    print('R17_TOTAL_TOPICS=' + str(len(result['topic_inventory'])))

    for name, count in result['required_stream_counts'].items():
        print('R17_REQUIRED_TOPIC=' + name + ' COUNT=' + str(count))

    print('R17_REAL_POSE_FACTORS=0')

if __name__ == '__main__':
    main()
