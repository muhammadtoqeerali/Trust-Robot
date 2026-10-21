#!/usr/bin/env python3
"""Negative fixtures and synthetic exact-content control; never authentic GT."""
import hashlib, os, pathlib, tempfile
from r55f_manual import classify

def main():
    n = 0

    with tempfile.TemporaryDirectory(
        prefix='r55f_controls_',
        dir=str(pathlib.Path(__file__).parent)
    ) as root:
        d = pathlib.Path(root)
        p = d / 'sample.txt'

        def probe(data, status, reason=None, matching=False):
            nonlocal n
            p.write_bytes(data)

            want = (
                hashlib.sha256(data).hexdigest()
                if matching else '0' * 64
            )
            result = classify(p, expected=want)
            assert result['status'] == status, result

            if reason:
                assert result['reason'] == reason, result

            n += 1

        missing = classify(p)
        assert missing['status'] == 'ABSENT'
        n += 1

        probe(b'123', 'REJECTED', 'BOUNDS')

        probe(
            b'<html><body>login 123</body></html>' * 4,
            'REJECTED', 'WRAPPER_OR_BINARY_NOT_GT_TEXT', True
        )
        probe(
            b'<!doctype html> redirect 123 ' * 3,
            'REJECTED', 'WRAPPER_OR_BINARY_NOT_GT_TEXT', True
        )
        probe(
            b'PK\x03\x04' + b'1234' * 16,
            'REJECTED', 'WRAPPER_OR_BINARY_NOT_GT_TEXT', True
        )
        probe(
            b'123\x00' + b'456' * 20,
            'REJECTED', 'WRAPPER_OR_BINARY_NOT_GT_TEXT', True
        )
        probe(
            b'example numbers 123 456 789\n' * 4,
            'REJECTED', 'FROZEN_SHA256_MISMATCH_NO_NORMALIZATION'
        )
        probe(
            b'example numbers 123 456 789\n' * 4,
            'MATCH', matching=True
        )
        probe(
            b'\xff' * 70,
            'REJECTED', 'NON_UTF8_TEXT', True
        )
        probe(
            b'header without numeric values ' * 4,
            'REJECTED', 'NO_NUMERIC_TEXT_HEADER', True
        )

        p.unlink()
        link = d / 'link.txt'
        link.symlink_to(d / 'sample.txt')
        assert classify(link)['status'] == 'REJECTED'
        n += 1

        p.write_bytes(b'123' * 24)
        link2 = d / 'hardlink.txt'
        os.link(p, link2)
        assert classify(p)['status'] == 'REJECTED'
        n += 1
        link2.unlink()
        p.unlink()

        with p.open('wb') as f:
            f.truncate(128 * 1024 * 1024 + 1)

        assert classify(p)['reason'] == 'BOUNDS'
        n += 1

    print(
        'R55F_SYNTHETIC_AND_NEGATIVE_CONTROLS='
        + str(n) + '_PASS'
    )

if __name__ == '__main__':
    main()
