"""Pure synthetic quarantine controls; never reads the original GT or rosbag."""
import hashlib
import pathlib
import tempfile
from r61_quarantine import inspect

with tempfile.TemporaryDirectory(prefix='r61_quarantine_control_') as tmp:
    d = pathlib.Path(tmp)
    absent = d/'missing.txt'
    assert inspect(absent)['status'] == 'ABSENT'
    text = d/'synthetic_example.txt'
    text.write_bytes(b'# synthetic candidate, NOT ground truth\n0 1 2 3 4\n')
    eligible = inspect(text)
    assert eligible['status'] == 'CANDIDATE_BYTES_PRESENT_UNVERIFIED'
    assert eligible['historical_digest_match'] is False
    assert eligible['observed_sha256'] == hashlib.sha256(text.read_bytes()).hexdigest()
    assert eligible['bytes'] == text.stat().st_size

    cases = [
        (b'', 'REFUSED_SIZE_BOUND'),
        (b'<!DOCTYPE html><html>login</html>', 'REFUSED_NON_GT_WEB_OR_CONTAINER_CONTENT'),
        (b' \n<html>Sign in</html>', 'REFUSED_NON_GT_WEB_OR_CONTAINER_CONTENT'),
        (b'<?xml version="1.0"?><Response/>', 'REFUSED_NON_GT_WEB_OR_CONTAINER_CONTENT'),
        (b'PK\x03\x04not-a-text-file', 'REFUSED_NON_GT_WEB_OR_CONTAINER_CONTENT'),
        (b'%PDF-1.7 invalid reference', 'REFUSED_NON_GT_WEB_OR_CONTAINER_CONTENT'),
        (b'1 2 3\x00 4', 'REFUSED_BINARY_CONTENT'),
    ]
    for index, (data, reason) in enumerate(cases):
        path = d/('negative_' + str(index) + '.txt')
        path.write_bytes(data)
        assert inspect(path)['status'] == reason, index
    link = d/'symlink.txt'
    link.symlink_to(text)
    assert inspect(link)['status'] == 'REFUSED_NONREGULAR_OR_LINK'
    assert inspect(d)['status'] == 'REFUSED_NONREGULAR_OR_LINK'
    large = d/'too_large.txt'
    with large.open('wb') as stream:
        stream.truncate(1024)
    assert inspect(large, limit=500)['status'] == 'REFUSED_SIZE_BOUND'

print('R61_SYNTHETIC_QUARANTINE_POSITIVE=1_UNVERIFIED_ONLY')
print('R61_NEGATIVE_CONTROLS=10_REJECTED')
print('R61_ABSENT_SOURCE_CONTROL=PASS')
