#!/usr/bin/env python3
"""Synthetic README/blob invalidity controls; no external data used."""

import hashlib
from r59_primary import validate_author

LINK = (
    'https://sjtueducn-my.sharepoint.com/:t:/g/'
    'personal/594666_sjtu_edu_cn/'
    'ES-9QFWKEeBNqxyMv5dJe7EB5YxfTzi8v3x2Hf1aLObnAg?e=ifwPHL'
)

row = (
    'room_02|2021-07-30|15.2g|75s|room,bright|'
    '[Rosbag](https://example.invalid/bag)|[GT](' + LINK + ')'
)

raw = ('# Synthetic test README\n' + row + '\n').encode()

def sha(b):
    return hashlib.sha1(
        b'blob ' + str(len(b)).encode() + b'\0' + b
    ).hexdigest()

assert (
    validate_author(raw, expected=sha(raw))['git_blob_sha1']
    == sha(raw)
)

negative = [
    (raw, '0' * 40, LINK),
    (raw, sha(raw), LINK + 'wrong'),
    (raw.replace(b'2021-07-30', b'2020-07-30'), None, LINK),
    (raw.replace(b'75s', b'76s'), None, LINK),
    (raw + row.encode() + b'\n', None, LINK),
    (b'<html>redirect 1234</html>', None, LINK),
    (b'\xff' + raw, None, LINK),
    (b'header_without_room_02\n', None, LINK),
]

for data, expected, link in negative:
    try:
        validate_author(
            data,
            expected=expected or sha(data),
            link=link
        )
    except (ValueError, UnicodeError):
        pass
    else:
        raise AssertionError('MUTANT_WAS_ACCEPTED')

print('R59_SYNTHETIC_POSITIVE=1_PASS')
print('R59_NEGATIVE_SOURCE_CONTROLS=8_REJECTED')
