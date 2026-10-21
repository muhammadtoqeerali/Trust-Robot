#!/usr/bin/env python3
"""Separate offline replay with fresh byte reads, not the primary classifier."""
import hashlib, json, os, pathlib, stat, sys

EXPECTED = '79d2c6d9132ce3cf87bb87445729302cd73709a59344a3dfacc5d7788937589d'

def main():
    candidate, output, inv, tracker = map(
        pathlib.Path, sys.argv[1:5]
    )

    report_path = output / 'r55f_manual_acquisition_receipt_v1.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    obs = report['observed']

    assert report['expected_raw_source_sha256'] == EXPECTED
    assert report['r54_inventory_sha256'] == hashlib.sha256(
        inv.read_bytes()
    ).hexdigest()
    assert report['r54_tracker_sha256'] == hashlib.sha256(
        tracker.read_bytes()
    ).hexdigest()

    assert report['source_candidate'] == str(candidate)
    assert report['split'] == 'TRAIN'
    assert report['trajectory'] == 'room_02'
    assert report['r43_eleven_scientific_gates'] == 'ALL_CLOSED_UNCHANGED'
    assert report['real_sensor_factors_health_ate_rpe'] == 'DENIED'
    assert report['confirmation_test_accessed'] is False
    assert report['raw_rosbag_accessed'] is False
    assert report['downloaded_gt_copied_into_git'] is False

    if not candidate.exists() and not candidate.is_symlink():
        assert obs['status'] == 'ABSENT'
        assert obs['sha256'] is None
        independently_observed = 'ABSENT'
    else:
        s = candidate.lstat()

        if (
            not stat.S_ISREG(s.st_mode)
            or s.st_nlink != 1
            or not 32 <= s.st_size <= 128 * 1024 * 1024
        ):
            assert obs['status'] == 'REJECTED'
            assert obs['sha256'] is None
            independently_observed = 'REJECTED_UNSAFE'
        else:
            fd = os.open(
                str(candidate),
                os.O_RDONLY | os.O_NOFOLLOW |
                os.O_CLOEXEC | os.O_NONBLOCK
            )
            with os.fdopen(fd, 'rb') as handle:
                h = hashlib.sha256()
                sample = b''
                n = 0

                while True:
                    block = handle.read(1024 * 1024)
                    if not block:
                        break

                    if len(sample) < 4096:
                        sample += block[:4096 - len(sample)]

                    n += len(block)
                    assert n <= 128 * 1024 * 1024
                    h.update(block)

                sf = os.fstat(handle.fileno())

            new = candidate.lstat()

            a = (
                s.st_dev, s.st_ino, s.st_size,
                s.st_mtime_ns, s.st_ctime_ns
            )
            b = (
                sf.st_dev, sf.st_ino, sf.st_size,
                sf.st_mtime_ns, sf.st_ctime_ns
            )
            c = (
                new.st_dev, new.st_ino, new.st_size,
                new.st_mtime_ns, new.st_ctime_ns
            )

            assert a == b == c

            digest = h.hexdigest()
            assert obs['sha256'] == digest
            assert obs['bytes'] == n

            head = sample.lstrip(b'\xef\xbb\xbf\x20\t\r\n').lower()

            wrapper = (
                b'\x00' in sample
                or head.startswith((
                    b'<!doctype', b'<html', b'<?xml',
                    b'pk\x03\x04', b'%pdf-', b'\x1f\x8b'
                ))
                or b'<html' in head
                or b'login.microsoftonline.com' in head
                or (
                    head.startswith(b'{')
                    and (
                        b'"access_token"' in head
                        or b'"error"' in head
                    )
                )
            )

            try:
                sample.decode('utf-8-sig')
                utf8 = True
            except UnicodeError:
                utf8 = False

            text_plausible = (
                not wrapper
                and utf8
                and any(48 <= b <= 57 for b in sample)
            )

            if digest == EXPECTED and text_plausible:
                assert obs['status'] == 'MATCH'
                assert report['admission'] == (
                    'FROZEN_BYTE_IDENTITY_ONLY_NOT_PHYSICAL_QUALIFICATION'
                )
                independently_observed = 'MATCH'
            else:
                assert obs['status'] == 'REJECTED'
                assert report['admission'] == 'DENIED'
                independently_observed = 'REJECTED_FORMAT_OR_SHA'

    result = {
        'schema': 'trust_robot_r55f_independent_replay_v1',
        'status': 'PASS',
        'independent_candidate_state': independently_observed,
        'source_content_sha256_matched':
            independently_observed == 'MATCH',
        'eleven_scientific_gates': 'ALL_CLOSED',
        'original_r55_untouched': True,
        'raw_bag_opened': False,
        'confirmation_test_accessed': False
    }

    with (
        output / 'r55f_independent_validation_v1.json'
    ).open('x', encoding='utf-8') as fp:
        json.dump(result, fp, indent=2, sort_keys=True)
        fp.write('\n')
        fp.flush()
        os.fsync(fp.fileno())

    print('R55F_INDEPENDENT_REPLAY=PASS')
    print('R55F_INDEPENDENT_SOURCE_STATE=' + independently_observed)

if __name__ == '__main__':
    main()
