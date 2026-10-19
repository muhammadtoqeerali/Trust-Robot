"""Independently recompute ROS1 topic counts from source index records."""
import hashlib
import json
from pathlib import Path
import struct
import sys

EXPECTED = {
    '/camera/color/image_raw/compressed': 'sensor_msgs/CompressedImage',
    '/camera/imu': 'sensor_msgs/Imu',
    '/handsfree/imu': 'sensor_msgs/Imu',
    '/velodyne_points': 'sensor_msgs/PointCloud2',
}

def want(ok, reason):
    if not ok:
        raise ValueError('R17_INDEPENDENT_FAIL:' + reason)

def exact(handle, n):
    b = handle.read(n)
    want(len(b) == n, 'TRUNCATED')
    return b

def v4(b):
    want(len(b) == 4, 'UINT32')
    return int.from_bytes(b, 'little')

def v8(b):
    want(len(b) == 8, 'UINT64')
    return int.from_bytes(b, 'little')

def unpack_fields(blob):
    result = {}
    cursor = 0

    while cursor < len(blob):
        want(cursor + 4 <= len(blob), 'FIELD_PREFIX')
        size = v4(blob[cursor:cursor + 4])
        cursor += 4
        want(0 < size <= len(blob) - cursor, 'FIELD_SIZE')

        field = blob[cursor:cursor + size]
        cursor += size
        key, marker, value = field.partition(b'=')
        want(marker and key not in result, 'BAD_FIELD')
        result[key] = value

    return result

def read_record(handle):
    length = v4(exact(handle, 4))
    want(0 < length <= 2 * 1024 * 1024, 'HEADER_BOUND')

    header = unpack_fields(exact(handle, length))
    data_length = v4(exact(handle, 4))
    want(data_length <= 8 * 1024 * 1024, 'DATA_BOUND')

    return header, exact(handle, data_length)

def independent_index(file):
    with file.open('rb') as handle:
        want(exact(handle, 13) == b'#ROSBAG V2.0\n', 'FORMAT')

        h, _ = read_record(handle)
        want(h.get(b'op') == b'\x03', 'BAG_HEADER')

        offset = v8(h[b'index_pos'])
        nconn = v4(h[b'conn_count'])
        nchunk = v4(h[b'chunk_count'])

        want(
            0 < nconn <= 10000
            and 0 < nchunk <= 1000000
            and handle.tell() < offset < file.stat().st_size,
            'INDEX_OFFSETS'
        )

        handle.seek(offset)
        connections = {}

        for _ in range(nconn):
            h, data = read_record(handle)
            want(h.get(b'op') == b'\x07', 'CONNECTION')

            cid = v4(h[b'conn'])
            want(cid not in connections, 'DUPLICATE_CONNECTION')

            info = unpack_fields(data)
            connections[cid] = (
                h[b'topic'].decode(),
                info[b'type'].decode()
            )

        counts = dict.fromkeys(connections, 0)

        for _ in range(nchunk):
            h, data = read_record(handle)
            want(h.get(b'op') == b'\x06', 'CHUNK_INFO')

            n = v4(h[b'count'])
            want(
                len(data) == 8 * n
                and v4(h[b'ver']) == 1,
                'CHUNK_COUNTS'
            )

            seen = set()

            for j in range(n):
                cid, count = struct.unpack_from('<II', data, 8 * j)
                want(
                    cid in counts
                    and cid not in seen
                    and count > 0,
                    'CHUNK_ENTRY'
                )
                seen.add(cid)
                counts[cid] += count

        want(handle.tell() == file.stat().st_size, 'TRAILING')

    summary = {}

    for cid, (topic, msg_type) in connections.items():
        item = summary.setdefault(
            topic, {'count': 0, 'types': set()}
        )
        item['count'] += counts[cid]
        item['types'].add(msg_type)

    for topic, msg_type in EXPECTED.items():
        want(
            topic in summary
            and summary[topic]['count'] > 0
            and summary[topic]['types'] == {msg_type},
            'REQUIRED_SENSOR'
        )

    return nconn, nchunk, {
        topic: item['count']
        for topic, item in summary.items()
    }

def main():
    bag, manifest, report = map(Path, sys.argv[1:4])
    result = json.loads(report.read_text())
    original = json.loads(manifest.read_text())

    records = [
        r for r in original['records']
        if r['trajectory_id'] == 'room_02'
    ]
    want(len(records) == 1 and records[0]['split'] == 'train', 'TRAIN')

    pins = [
        a['sha256']
        for a in records[0]['calibration_artifacts']
        if a.get('source_path') == 'raw/rosbags/room_02.bag'
    ]

    want(
        len(pins) == 1
        and result['file_sha256'] == pins[0],
        'SOURCE_SHA_PIN'
    )

    want(
        result['frozen_manifest_sha256'] ==
        hashlib.sha256(manifest.read_bytes()).hexdigest(),
        'MANIFEST_BINDING'
    )

    want(
        result['schema'] == 'TRUST_ROBOT_R17_ROS1_INDEX_READONLY_V1'
        and result['trajectory_id'] == 'room_02'
        and result['split'] == 'train',
        'REPORT_IDENTITY'
    )

    nconn, nchunk, counts = independent_index(bag)

    want(
        result['connection_count'] == nconn
        and result['chunk_count'] == nchunk,
        'CONNECTION_CHUNK_COUNTS'
    )

    want(
        {
            topic: item['record_count']
            for topic, item in result['topic_inventory'].items()
        } == counts,
        'TOPIC_COUNTS'
    )

    want(
        result['required_stream_counts'] == {
            topic: counts[topic]
            for topic in EXPECTED
        },
        'SENSOR_COUNTS'
    )

    want(result['size_bytes'] == bag.stat().st_size, 'SOURCE_SIZE')

    for key in (
        'recorded_sensor_payload_decoded',
        'bag_record_time_is_capture_time_proof',
        'physical_sync_verified',
        'physical_extrinsics_verified',
        'git_modified',
        'source_file_modified',
    ):
        want(result[key] is False, 'SCIENTIFIC_BOUNDARY:' + key)

    for key in (
        'real_pose_factors_generated',
        'messages_decompressed',
        'health_labels',
    ):
        want(
            type(result[key]) is int and result[key] == 0,
            'ZERO_COUNT:' + key
        )

    print('R17_INDEPENDENT_CONNECTIONS=' + str(nconn))
    print('R17_INDEPENDENT_CHUNKS=' + str(nchunk))
    print('R17_INDEPENDENT_TOPIC_COUNTS=VERIFIED')
    print('R17_INDEPENDENT_VERIFICATION=PASS')

if __name__ == '__main__':
    main()
