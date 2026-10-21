"""R61 bounded, read-only candidate-byte quarantine. Never certifies GT."""
import hashlib
import json
import os
import pathlib
import stat
import sys

HISTORICAL = '79d2c6d9132ce3cf87bb87445729302cd73709a59344a3dfacc5d7788937589d'
LIMIT = 64 * 1024 * 1024


def inspect(path, limit=LIMIT):
    path = pathlib.Path(path)
    try:
        before = path.lstat()
    except FileNotFoundError:
        return {'status': 'ABSENT', 'observed_sha256': None, 'bytes': None,
                'historical_digest_match': None}
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        return {'status': 'REFUSED_NONREGULAR_OR_LINK', 'observed_sha256': None,
                'bytes': None, 'historical_digest_match': None}
    if before.st_size == 0 or before.st_size > limit:
        return {'status': 'REFUSED_SIZE_BOUND', 'observed_sha256': None,
                'bytes': before.st_size, 'historical_digest_match': None}

    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open(str(path), flags)
    digest = hashlib.sha256()
    first = b''
    binary = False
    with os.fdopen(fd, 'rb') as f:
        opened = os.fstat(f.fileno())
        total = 0
        while True:
            block = f.read(1024 * 1024)
            if not block:
                break
            total += len(block)
            if total > limit:
                raise ValueError('FILE_CHANGED_OR_TOO_LARGE')
            if len(first) < 8192:
                first += block[:8192 - len(first)]
            if b'\x00' in block:
                binary = True
            digest.update(block)
        finished = os.fstat(f.fileno())
    after = path.lstat()
    ident = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if not ident(before) == ident(opened) == ident(finished) == ident(after) or total != before.st_size:
        raise ValueError('SOURCE_MUTATED_DURING_READ')

    lowered = first.lstrip().lower()
    if (lowered.startswith((b'<!doctype html', b'<html', b'<?xml', b'%pdf', b'pk\x03\x04'))
            or b'<html' in lowered[:2048] or b'<form' in lowered[:2048]):
        status = 'REFUSED_NON_GT_WEB_OR_CONTAINER_CONTENT'
    elif binary:
        status = 'REFUSED_BINARY_CONTENT'
    else:
        status = 'CANDIDATE_BYTES_PRESENT_UNVERIFIED'
    observed = digest.hexdigest()
    return {'status': status, 'observed_sha256': observed,
            'bytes': total, 'historical_digest_match': observed == HISTORICAL}


def main(stage, author_json, r60_json, gate_json, out):
    auth = json.loads(pathlib.Path(author_json).read_text())
    req = json.loads(pathlib.Path(r60_json).read_text())
    gates = json.loads(pathlib.Path(gate_json).read_text())
    if not (auth['readme_verified'] is True and
            req['draft_status'] == 'PREPARED_NOT_POSTED' and
            req['author_contacted'] is False and
            len(gates['requests']) == 11 and
            all(v['status'] == 'NOT_QUALIFIED' for v in gates['requests'].values())):
        raise RuntimeError('FROZEN_PROVENANCE_OR_SCIENCE_CONTRACT_CHANGED')
    result = inspect(stage)
    report = {
        'schema': 'TRUST_ROBOT_R61_READ_ONLY_GT_QUARANTINE_V1',
        'git_baseline': 'a800ca91326a51fa0cc86972bed08e99b6b459e5',
        'trajectory': 'room_02', 'split': 'train',
        'candidate_path': str(pathlib.Path(stage)),
        'candidate': result,
        'historical_expected_digest_only': HISTORICAL,
        'authenticated_author_readme': True,
        'official_ground_truth_independently_authenticated': False,
        'clock_frame_pose_semantics_qualified': False,
        'author_communication_sent_by_this_phase': False,
        'scientific_gates_closed': sorted(gates['requests']),
        'science_gates_opened': 0,
        'real_pose_factors_authorized': False,
        'health_training_authorized': False,
        'ate_rpe_authorized': False,
        'raw_bag_opened': False,
        'confirmation_test_accessed': False,
        'git_modified': False,
        'quarantine_only_not_gt_ingestion': True,
    }
    p = pathlib.Path(out) / 'r61_quarantine_receipt_v1.json'
    with p.open('x', encoding='utf-8') as f:
        json.dump(report, f, sort_keys=True, indent=2)
        f.write('\n')
    print('R61_CANDIDATE_STATUS=' + result['status'])
    print('R61_SOURCE_OBSERVED_SHA256=' + str(result['observed_sha256']))
    print('R61_HISTORICAL_HASH_MATCH=' + str(result['historical_digest_match']))
    print('R61_INDEPENDENT_GT_AUTHENTICATION=NO')


if __name__ == '__main__':
    main(*sys.argv[1:])
