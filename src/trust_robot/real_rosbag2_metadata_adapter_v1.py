"""Read-only ROS 2 sqlite3 recorder-envelope inventory candidate (not qualified physical data).

No serialized ROS message payloads, ROS header stamps, frame transforms, or estimator
factors are read or inferred. The original recording is never opened for writing.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from urllib.parse import quote


class BagInventoryError(ValueError):
    pass


def require(ok: bool, why: str):
    if not ok:
        raise BagInventoryError(why)


def _safe_existing_directory(folder: Path) -> Path:
    folder = Path(os.path.abspath(os.fspath(folder)))
    require(folder.is_dir() and not folder.is_symlink(), 'Recording directory unavailable or symlinked')
    for item in folder.parents:
        require(not item.is_symlink(), 'Recording path contains symlink ancestor')
    return folder


def _safe_regular_file(path: Path) -> None:
    require(path.is_file() and not path.is_symlink(), 'Recording shard missing or symlinked')
    require(0 < path.stat().st_size <= 30_000_000_000, 'Recording shard outside bounded size limits')


def inspect_sqlite_shard(path: Path) -> dict:
    path = Path(path)
    _safe_regular_file(path)
    with path.open('rb') as handle:
        require(handle.read(16) == b'SQLite format 3\x00', 'Unexpected SQLite header')
    url = 'file:' + quote(os.fspath(path), safe='/') + '?mode=ro&immutable=1'
    try:
        conn = sqlite3.connect(url, uri=True, timeout=2)
        try:
            conn.execute('PRAGMA query_only=ON')
            conn.execute('PRAGMA trusted_schema=OFF')
            conn.execute('PRAGMA busy_timeout=2000')
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            require({'topics', 'messages'}.issubset(tables), 'Missing rosbag2 SQLite tables')
            schemas = {
                t: {r[1] for r in conn.execute('PRAGMA table_info(' + t + ')')}
                for t in ('topics', 'messages')
            }
            require({'id', 'name', 'type'}.issubset(schemas['topics']), 'Invalid topic table')
            require({'id', 'topic_id', 'timestamp', 'data'}.issubset(schemas['messages']), 'Invalid messages table')
            invalid_timestamps = conn.execute(
                "SELECT count(*) FROM messages WHERE typeof(timestamp) != 'integer' OR timestamp < 0"
            ).fetchone()[0]
            require(invalid_timestamps == 0, 'Non-integer or negative recorder timestamps')
            orphans = conn.execute(
                'SELECT count(*) FROM messages m LEFT JOIN topics t ON t.id=m.topic_id WHERE t.id IS NULL'
            ).fetchone()[0]
            require(orphans == 0, 'Messages have unknown topic IDs')
            rows = conn.execute('''
                SELECT t.name, t.type, count(m.id), min(m.timestamp), max(m.timestamp)
                FROM topics t LEFT JOIN messages m ON m.topic_id=t.id
                GROUP BY t.id, t.name, t.type ORDER BY t.name, t.type
            ''').fetchall()
            count_total = conn.execute('SELECT count(*) FROM messages').fetchone()[0]
            require(sum(r[2] for r in rows) == count_total, 'Topic and message counts inconsistent')
            topics = [
                {'name': name, 'type': msgtype, 'message_count': count,
                 'first_recorder_timestamp_ns': first, 'last_recorder_timestamp_ns': last}
                for name, msgtype, count, first, last in rows
            ]
            require(all(type(t['name']) is str and type(t['type']) is str for t in topics),
                    'Invalid topic metadata')
            return {'shard_filename': path.name, 'shard_size_bytes': path.stat().st_size,
                    'message_count': count_total, 'topics': topics}
        finally:
            conn.close()
    except sqlite3.Error as exc:
        raise BagInventoryError('Unreadable or unsupported SQLite recorder metadata') from exc


def inventory_bag(folder: Path) -> dict:
    folder = _safe_existing_directory(folder)
    entries = list(folder.iterdir())
    require(len(entries) <= 256, 'Too many recording directory entries')
    shards = sorted(
        (p for p in entries if p.name.endswith('.db3')),
        key=lambda p: p.name,
    )
    require(0 < len(shards) <= 100, 'No bounded SQLite .db3 shards found')
    require(all(p.is_file() and not p.is_symlink() for p in shards), 'Symlink or invalid SQLite shard')
    metadata = folder / 'metadata.yaml'
    if metadata.exists() or metadata.is_symlink():
        require(metadata.is_file() and not metadata.is_symlink(), 'Unsafe ROS bag metadata file')
    individual = [inspect_sqlite_shard(p) for p in shards]
    merged = {}
    for shard in individual:
        for topic in shard['topics']:
            key = (topic['name'], topic['type'])
            if key not in merged:
                merged[key] = {
                    'name': key[0], 'type': key[1], 'message_count': 0,
                    'first_recorder_timestamp_ns': None,
                    'last_recorder_timestamp_ns': None,
                }
            target = merged[key]
            target['message_count'] += topic['message_count']
            if topic['message_count']:
                first = topic['first_recorder_timestamp_ns']
                last = topic['last_recorder_timestamp_ns']
                for label, value, operator in (
                    ('first_recorder_timestamp_ns', first, min),
                    ('last_recorder_timestamp_ns', last, max),
                ):
                    old = target[label]
                    target[label] = value if old is None else operator(old, value)
    result = {
        'schema': 'TRUST_ROBOT_R135_A34_4_D2_ROSBAG2_ENVELOPE_V1',
        'status': 'UNQUALIFIED_RECORDER_ENVELOPE_ONLY',
        'metadata_yaml_present': metadata.is_file() and not metadata.is_symlink(),
        'sqlite_shard_count': len(individual),
        'total_messages': sum(x['message_count'] for x in individual),
        'topics': sorted(merged.values(), key=lambda x: (x['name'], x['type'])),
        'shards': individual,
        'physical_event_time_verified': False,
        'real_factor_admission': 'DENIED',
        'real_factor_count': 0,
    }
    require(sum(x['message_count'] for x in result['topics']) == result['total_messages'],
            'Combined count mismatch')
    return result
