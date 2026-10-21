#!/usr/bin/env python3
"""R55F offline manual source-byte identity check. No network or GT parsing."""
import hashlib, json, os, pathlib, stat, sys

EXPECTED = '79d2c6d9132ce3cf87bb87445729302cd73709a59344a3dfacc5d7788937589d'
MAX_BYTES = 128 * 1024 * 1024
MIN_BYTES = 32

def classify(path, expected=EXPECTED):
    p = pathlib.Path(path)
    try:
        initial = p.lstat()
    except FileNotFoundError:
        return dict(
            status='ABSENT',
            reason='MANUAL_FILE_NOT_YET_STAGED',
            bytes=None, sha256=None
        )

    if not stat.S_ISREG(initial.st_mode) or initial.st_nlink != 1:
        return dict(
            status='REJECTED',
            reason='NOT_EXCLUSIVE_REGULAR_FILE',
            bytes=None, sha256=None
        )

    if initial.st_size < MIN_BYTES or initial.st_size > MAX_BYTES:
        return dict(
            status='REJECTED', reason='BOUNDS',
            bytes=initial.st_size, sha256=None
        )

    try:
        fd = os.open(
            str(p),
            os.O_RDONLY | os.O_NOFOLLOW |
            os.O_CLOEXEC | os.O_NONBLOCK
        )
        with os.fdopen(fd, 'rb', closefd=True) as stream:
            start = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(start.st_mode)
                or start.st_nlink != 1
                or (start.st_dev, start.st_ino)
                   != (initial.st_dev, initial.st_ino)
            ):
                return dict(
                    status='REJECTED',
                    reason='RACED_OR_NONREGULAR_FILE',
                    bytes=None, sha256=None
                )

            h = hashlib.sha256()
            count = 0
            head = b''

            while True:
                block = stream.read(1024 * 1024)
                if not block:
                    break
                count += len(block)
                if count > MAX_BYTES:
                    return dict(
                        status='REJECTED',
                        reason='GROWING_TOO_LARGE',
                        bytes=count, sha256=None
                    )
                if len(head) < 4096:
                    head += block[:4096 - len(head)]
                h.update(block)

            end = os.fstat(stream.fileno())

        post = p.lstat()

    except (OSError, ValueError) as ex:
        return dict(
            status='REJECTED',
            reason='UNSAFE_OR_UNREADABLE_FILE_' + type(ex).__name__,
            bytes=None, sha256=None
        )

    identity = lambda s: (
        s.st_dev, s.st_ino, s.st_size,
        s.st_mtime_ns, s.st_ctime_ns
    )

    if (
        not (
            identity(initial) == identity(start)
            == identity(end) == identity(post)
        )
        or count != initial.st_size
    ):
        return dict(
            status='REJECTED',
            reason='CHANGED_DURING_HASH',
            bytes=count, sha256=None
        )

    sha = h.hexdigest()
    sample = head.lstrip(b'\xef\xbb\xbf\x20\t\r\n').lower()

    if (
        b'\x00' in head
        or sample.startswith((
            b'<!doctype', b'<html', b'<?xml',
            b'pk\x03\x04', b'%pdf-', b'\x1f\x8b'
        ))
        or b'<html' in sample
        or b'login.microsoftonline.com' in sample
        or (
            sample.startswith(b'{')
            and (
                b'"access_token"' in sample
                or b'"error"' in sample
            )
        )
    ):
        return dict(
            status='REJECTED',
            reason='WRAPPER_OR_BINARY_NOT_GT_TEXT',
            bytes=count, sha256=sha
        )

    try:
        head.decode('utf-8-sig')
    except UnicodeError:
        return dict(
            status='REJECTED',
            reason='NON_UTF8_TEXT',
            bytes=count, sha256=sha
        )

    if not any(48 <= b <= 57 for b in head):
        return dict(
            status='REJECTED',
            reason='NO_NUMERIC_TEXT_HEADER',
            bytes=count, sha256=sha
        )

    if sha != expected:
        return dict(
            status='REJECTED',
            reason='FROZEN_SHA256_MISMATCH_NO_NORMALIZATION',
            bytes=count, sha256=sha
        )

    return dict(
        status='MATCH',
        reason='EXACT_FROZEN_CONTENT_SHA256_TEXT_PLAUSIBLE',
        bytes=count, sha256=sha
    )

def main():
    candidate, out, inv, tracker = map(
        pathlib.Path, sys.argv[1:5]
    )

    result = classify(candidate)

    report = {
        'schema': 'trust_robot_r55f_offline_browser_source_receipt_v1',
        'trajectory': 'room_02',
        'split': 'TRAIN',
        'official_link_provenance':
            'upstream_M2DGR_README_git_commit_5db59c1f_R54_inventory_candidate_only',
        'browser_authorship_provenance':
            'NOT_INDEPENDENTLY_ESTABLISHED',
        'download_method':
            'USER_BROWSER_MANUAL_STAGING_ONLY_NO_NETWORK_BY_THIS_PHASE',
        'source_candidate': str(candidate),
        'expected_raw_source_sha256': EXPECTED,
        'r54_inventory_sha256':
            hashlib.sha256(inv.read_bytes()).hexdigest(),
        'r54_tracker_sha256':
            hashlib.sha256(tracker.read_bytes()).hexdigest(),
        'observed': result,
        'admission':
            'FROZEN_BYTE_IDENTITY_ONLY_NOT_PHYSICAL_QUALIFICATION'
            if result['status'] == 'MATCH' else 'DENIED',
        'r43_eleven_scientific_gates': 'ALL_CLOSED_UNCHANGED',
        'physical_reference_frame_and_clock': 'NOT_QUALIFIED',
        'real_sensor_factors_health_ate_rpe': 'DENIED',
        'confirmation_test_accessed': False,
        'raw_rosbag_accessed': False,
        'downloaded_gt_copied_into_git': False,
        'next':
            'R55F_GT_TEXT_AND_REFERENCE_SCHEMA_AUDIT'
            if result['status'] == 'MATCH'
            else 'MANUALLY_SAVE_OFFICIAL_GT_TO_STAGING_THEN_REQUEST_TARGETED_CHECK'
    }

    with (
        out / 'r55f_manual_acquisition_receipt_v1.json'
    ).open('x', encoding='utf-8') as fp:
        json.dump(report, fp, indent=2, sort_keys=True)
        fp.write('\n')
        fp.flush()
        os.fsync(fp.fileno())

    print('R55F_OFFICIAL_GT_STATUS=' + result['status'])
    print('R55F_SOURCE_REASON=' + result['reason'])
    print('R55F_OBSERVED_SHA256=' + str(result['sha256']))
    print('R55F_FILE_BYTES=' + str(result['bytes']))

if __name__ == '__main__':
    main()
