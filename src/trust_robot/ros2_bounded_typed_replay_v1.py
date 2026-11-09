"""Bounded, read-only ROS 2 SQLite typed replay *engineering* index.

No raw measurements are returned. Recorder-envelope timestamps and ROS header
stamps are separate unverified axes. This module cannot admit physical factors.
ROS 2 imports are lazy: unit tests can inject a synthetic decoder.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
from pathlib import Path
from urllib.parse import quote

MAX_MESSAGE_BYTES = 24 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_SAMPLES = 7
FIELD_WIDTHS = {1: 1, 2: 1, 3: 2, 4: 2, 5: 4, 6: 4, 7: 4, 8: 8}
SUPPORTED = frozenset((
    'sensor_msgs/msg/Imu',
    'sensor_msgs/msg/CameraInfo',
    'sensor_msgs/msg/Image',
    'sensor_msgs/msg/PointCloud2',
))


class ReplayError(ValueError):
    """Invalid input or an explicit fail-closed replay refusal."""


def need(ok, why):
    if not ok:
        raise ReplayError(why)


def integer(value, low, high, label):
    need(type(value) is int and low <= value <= high, 'Invalid ' + label)
    return value


def safe_regular(path, *, directory=False):
    path = Path(os.path.abspath(os.fspath(path)))
    need(not path.is_symlink() and all(not p.is_symlink() for p in path.parents),
         'Symlink recording path refused')
    need(path.is_dir() if directory else path.is_file(), 'Recording path missing')
    return path


def validate_plan(plan):
    need(type(plan) in (list, tuple), 'Plan must be a list or tuple')
    need(0 < len(plan) <= MAX_SAMPLES, 'Plan length outside sample budget')
    clean = []
    for item in plan:
        need(type(item) in (tuple, list) and len(item) == 3, 'Invalid plan item')
        topic, msgtype, take = item
        need(type(topic) is str and 0 < len(topic.encode('utf-8')) <= 256
             and topic.startswith('/') and '\x00' not in topic,
             'Invalid topic name')
        need(type(msgtype) is str and msgtype in SUPPORTED,
             'Unsupported typed message')
        integer(take, 1, MAX_SAMPLES, 'sample take count')
        clean.append((topic, msgtype, take))
    need(len({x[0] for x in clean}) == len(clean), 'Duplicate planned topic')
    need(sum(x[2] for x in clean) <= MAX_SAMPLES, 'Total sample budget exceeded')
    return tuple(clean)


def ros_decoder(plan):
    """Resolve only caller-requested ROS types, never interact with ROS graph."""
    plan = validate_plan(plan)
    try:
        from rclpy.serialization import deserialize_message
        from rosidl_runtime_py.utilities import get_message
        resolved = {typ: get_message(typ) for _, typ, _ in plan}
    except Exception as exc:
        return None, 'ROS_TYPED_DECODER_UNAVAILABLE_' + type(exc).__name__
    return lambda blob, typ: deserialize_message(blob, resolved[typ]), 'ROS_TYPED_DECODER_AVAILABLE'


def extract_record(msg, typ, recorder_ns):
    """Structural and two-clock facts only; omit measurement and calibration arrays."""
    integer(recorder_ns, 0, 2**63 - 1, 'recorder timestamp')
    header = msg.header
    sec = integer(header.stamp.sec, -(2**31), 2**31 - 1, 'header second')
    nsec = integer(header.stamp.nanosec, 0, 999_999_999, 'header nanosecond')
    frame = header.frame_id
    need(type(frame) is str and len(frame.encode('utf-8')) <= 256, 'Invalid frame ID')
    stamp = sec * 1_000_000_000 + nsec
    result = {
        'recorder_timestamp_ns_unverified': recorder_ns,
        'ros_header_timestamp_ns_unverified': stamp,
        'recorder_minus_header_ns_unverified': recorder_ns - stamp,
        'frame_id_sha256': hashlib.sha256(frame.encode('utf-8')).hexdigest(),
        'frame_id_present': bool(frame),
        'frame_id_length_bytes': len(frame.encode('utf-8')),
    }
    if typ == 'sensor_msgs/msg/Imu':
        result['kind'] = 'ImuHeaderOnly'
    elif typ == 'sensor_msgs/msg/CameraInfo':
        w = integer(msg.width, 1, 100_000, 'CameraInfo width')
        h = integer(msg.height, 1, 100_000, 'CameraInfo height')
        result.update(kind='CameraInfoHeaderOnly', width=w, height=h)
    elif typ == 'sensor_msgs/msg/Image':
        w = integer(msg.width, 1, 100_000, 'Image width')
        h = integer(msg.height, 1, 100_000, 'Image height')
        step = integer(msg.step, 1, MAX_MESSAGE_BYTES, 'Image row stride')
        encoding = msg.encoding
        need(type(encoding) is str and len(encoding.encode('utf-8')) <= 64,
             'Invalid image encoding')
        size = len(msg.data)
        need(size == h * step and size <= MAX_MESSAGE_BYTES, 'Image data/stride mismatch')
        if encoding == 'rgb8':
            need(step >= w * 3, 'RGB8 row stride short')
        result.update(kind='ImageStructure', width=w, height=h,
                      step_bytes=step, encoding_reported=encoding, data_byte_count=size)
    elif typ == 'sensor_msgs/msg/PointCloud2':
        w = integer(msg.width, 1, MAX_MESSAGE_BYTES, 'Cloud width')
        h = integer(msg.height, 1, MAX_MESSAGE_BYTES, 'Cloud height')
        point_step = integer(msg.point_step, 1, MAX_MESSAGE_BYTES, 'Cloud point stride')
        row_step = integer(msg.row_step, 1, MAX_MESSAGE_BYTES, 'Cloud row stride')
        size = len(msg.data)
        need(w * h <= MAX_MESSAGE_BYTES // point_step, 'Cloud point byte budget exceeded')
        need(row_step >= w * point_step and size == h * row_step
             and size <= MAX_MESSAGE_BYTES, 'Cloud row/data mismatch')
        need(0 < len(msg.fields) <= 64, 'Cloud PointField count')
        for field in msg.fields:
            dtype = integer(field.datatype, 1, 8, 'PointField datatype')
            offset = integer(field.offset, 0, MAX_MESSAGE_BYTES, 'PointField offset')
            count = integer(field.count, 1, 100_000, 'PointField count')
            need(offset + count * FIELD_WIDTHS[dtype] <= point_step,
                 'Cloud PointField outside point stride')
        result.update(kind='PointCloud2Structure', width=w, height=h,
                      point_step=point_step, row_step=row_step,
                      data_byte_count=size, point_field_count=len(msg.fields))
    else:
        raise ReplayError('Unsupported ROS type')
    return result


def inspect(bag, decoder, plan, *, expected_shard_bytes=None,
            expected_metadata_sha256=None, expected_topics=None):
    """Inspect up to seven selected messages, never saving their raw CDR bytes.

    ``plan`` consists of (topic_name, ROS_type, samples_to_take) entries.
    Optional caller-provided integrity constraints allow real-data pinning,
    without embedding private recording locations or device identifiers.
    """
    plan = validate_plan(plan)
    bag = safe_regular(bag, directory=True)
    db = safe_regular(bag / 'bag_0.db3')
    st0 = db.stat()
    need(0 < st0.st_size <= 30_000_000_000, 'SQLite shard outside size budget')
    if expected_shard_bytes is not None:
        need(type(expected_shard_bytes) is int and st0.st_size == expected_shard_bytes,
             'Expected shard size mismatch')
    if expected_metadata_sha256 is not None:
        need(type(expected_metadata_sha256) is str
             and len(expected_metadata_sha256) == 64
             and all(c in '0123456789abcdef' for c in expected_metadata_sha256),
             'Invalid metadata hash pin')
        metadata = safe_regular(bag / 'metadata.yaml')
        need(0 < metadata.stat().st_size <= 2_000_000, 'Metadata file size outside budget')
        need(hashlib.sha256(metadata.read_bytes()).hexdigest() == expected_metadata_sha256,
             'Expected recording metadata mismatch')
    if expected_topics is not None:
        need(type(expected_topics) is dict, 'Expected topic inventory must be a dictionary')
    with db.open('rb') as handle:
        need(handle.read(16) == b'SQLite format 3\x00', 'Invalid SQLite header')
    url = 'file:' + quote(os.fspath(db), safe='/') + '?mode=ro&immutable=1'
    total_read = 0
    samples = []
    try:
        conn = sqlite3.connect(url, uri=True, timeout=2)
        try:
            conn.execute('PRAGMA query_only=ON')
            conn.execute('PRAGMA trusted_schema=OFF')
            conn.execute('PRAGMA temp_store=MEMORY')
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            need({'messages', 'topics'} <= tables, 'Missing rosbag2 SQLite tables')
            schemas = {name: {r[1] for r in conn.execute('PRAGMA table_info(' + name + ')')}
                       for name in ('messages', 'topics')}
            need({'id', 'topic_id', 'timestamp', 'data'} <= schemas['messages'],
                 'Unexpected messages table schema')
            need({'id', 'name', 'type', 'serialization_format'} <= schemas['topics'],
                 'Unexpected topics table schema')
            n = conn.execute('SELECT COUNT(*) FROM messages').fetchone()[0]
            records = conn.execute('''SELECT t.id,t.name,t.type,t.serialization_format,COUNT(m.id)
                       FROM topics t LEFT JOIN messages m ON t.id=m.topic_id
                       GROUP BY t.id,t.name,t.type,t.serialization_format''').fetchall()
            need(sum(row[4] for row in records) == n, 'Orphan or unaccounted messages')
            need(all(row[3] == 'cdr' for row in records), 'Non-CDR serialization detected')
            actual_topics = {row[1]: (row[2], row[4]) for row in records}
            need(len(actual_topics) == len(records), 'Duplicate topic identity')
            if expected_topics is not None:
                need(actual_topics == expected_topics, 'Expected topic inventory mismatch')
            selected = []
            for topic, msgtype, take in plan:
                matches = [row for row in records if row[1] == topic and row[2] == msgtype]
                need(len(matches) == 1, 'Planned topic absent or type differs')
                tid = matches[0][0]
                rows = conn.execute('''SELECT id,timestamp,LENGTH(data) FROM messages
                               WHERE topic_id=? ORDER BY timestamp,id LIMIT ?''',
                                    (tid, take)).fetchall()
                need(len(rows) == take, 'Insufficient selected envelopes')
                for rid, stamp, size in rows:
                    integer(stamp, 0, 2**63 - 1, 'recorder timestamp')
                    integer(size, 0, 2**63 - 1, 'serialized length')
                    selected.append((stamp, topic, msgtype, rid, tid, size))
            selected.sort(key=lambda row: (row[0], row[1], row[3]))
            need(len(selected) == sum(item[2] for item in plan), 'Unexpected sample count')
            for stamp, topic, msgtype, rid, tid, size in selected:
                item = {'topic_name': topic, 'message_type': msgtype,
                        'serialized_bytes': size,
                        'recorder_timestamp_ns_unverified': stamp,
                        'recorder_envelope_row_id': rid}
                if decoder is None:
                    item['status'] = 'NOT_DECODED_MISSING_TYPED_ROS'
                elif size > MAX_MESSAGE_BYTES or total_read + size > MAX_TOTAL_BYTES:
                    item['status'] = 'SKIPPED_STRICT_CDR_BYTE_BUDGET'
                else:
                    fetched = conn.execute('''SELECT data FROM messages
                              WHERE id=? AND topic_id=? AND LENGTH(data)<=?''',
                                           (rid, tid, MAX_MESSAGE_BYTES)).fetchone()
                    need(fetched is not None and len(fetched[0]) == size,
                         'Bounded CDR fetch mismatch')
                    total_read += size
                    try:
                        msg = decoder(bytes(fetched[0]), msgtype)
                        item.update(extract_record(msg, msgtype, stamp))
                        item['status'] = 'DECODED_UNQUALIFIED'
                    except Exception as exc:
                        item['status'] = 'REJECTED_TYPED_' + type(exc).__name__
                samples.append(item)
        finally:
            conn.close()
    except sqlite3.Error as exc:
        raise ReplayError('Unreadable SQLite recorder metadata') from exc
    st1 = db.stat()
    need((st0.st_size, st0.st_ino, st0.st_mtime_ns)
         == (st1.st_size, st1.st_ino, st1.st_mtime_ns),
         'SQLite shard changed during read-only inspection')
    return {
        'schema': 'TRUST_ROBOT_A35_BOUNDED_TYPED_REPLAY_PUBLIC_V1',
        'status': 'UNQUALIFIED_REPLAY_INDEX_ONLY',
        'sqlite_access': 'READ_ONLY_IMMUTABLE',
        'recording_shard_bytes': st0.st_size,
        'envelope_count': n,
        'topic_count': len(records),
        'sample_count': len(samples),
        'decoded_count': sum(row['status'] == 'DECODED_UNQUALIFIED' for row in samples),
        'cdr_bytes_read_in_process_memory': total_read,
        'timestamp_provenance': {
            'recorder': 'ROSBAG_SQLITE_ENVELOPE_UNVERIFIED',
            'ros_header': 'ROS_MESSAGE_HEADER_UNVERIFIED',
        },
        'recorder_order_monotonic': all(
            a['recorder_timestamp_ns_unverified'] <= b['recorder_timestamp_ns_unverified']
            for a, b in zip(samples, samples[1:])),
        'samples': samples,
        'raw_measurements_exported': False,
        'camera_pixels_or_lidar_points_exported': False,
        'imu_numeric_values_exported': False,
        'physical_event_time_verified': False,
        'physical_calibration_verified': False,
        'independent_reference_verified': False,
        'independent_qualifying_receipts': 0,
        'm2dgr_gates': '11_CLOSED',
        'real_factor_count': 0,
        'real_factor_admission': 'DENIED',
    }
