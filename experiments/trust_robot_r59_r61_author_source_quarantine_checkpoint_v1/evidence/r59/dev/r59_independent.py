#!/usr/bin/env python3
"""Independent replay of author Git identity and frozen science gates."""

import hashlib
import json
import pathlib
import sys

BLOB = 'c394994a8431426c0bd4b3dcf618faf7b97d119f'

GT = (
    'https://sjtueducn-my.sharepoint.com/:t:/g/'
    'personal/594666_sjtu_edu_cn/'
    'ES-9QFWKEeBNqxyMv5dJe7EB5YxfTzi8v3x2Hf1aLObnAg?e=ifwPHL'
)

OUT = pathlib.Path(sys.argv[1])
INV = pathlib.Path(sys.argv[2])
R43 = pathlib.Path(sys.argv[3])

r = json.loads(
    (OUT / 'r59_source_identity_report_v1.json').read_text()
)
i = json.loads(INV.read_text())
g = json.loads(R43.read_text())

assert r['schema'] == 'TRUST_ROBOT_R59_AUTHOR_README_IDENTITY_V1'

assert (
    r['gt_link_from_frozen_inventory']
    == i['official_readme_lists_room_02_gt_candidate_url']
    == GT
)

assert (
    r['expected_author_git_blob_sha1']
    == i['author_readme_git_blob_sha1']
    == BLOB
)

assert r['r43_gate_count_closed'] == 11
assert r['r43_gates_closed'] == sorted(g['requests'])

assert len(r['public_github_attempts']) in (1, 2)
assert r['sharepoint_gt_requests_made_in_r59'] == 0
assert r['official_gt_bytes_acquired_in_r59'] is False
assert r['raw_bag_opened'] is False
assert r['confirmation_test_accessed'] is False
assert r['github_modified'] is False
assert r['physical_frame_clock_qualified'] is False

for k in (
    'real_pose_factors_authorized',
    'health_training_authorized',
    'ate_rpe_authorized'
):
    assert r[k] is False

readme = OUT / 'r59_official_readme_original_bytes_v1.md'

if r['readme_verified']:
    data = readme.read_bytes()

    got = hashlib.sha1(
        b'blob ' + str(len(data)).encode() + b'\0' + data
    ).hexdigest()

    assert got == BLOB
    assert (
        r['verified_readme_details']['readme_sha256']
        == hashlib.sha256(data).hexdigest()
    )

    lines = [
        z for z in data.decode('utf-8').splitlines()
        if z.startswith('room_02|')
    ]

    assert len(lines) == 1
    assert lines[0] == r['verified_readme_details']['row']

    x = lines[0].split('|')

    assert len(x) == 7
    assert x[1] == '2021-07-30'
    assert x[3] == '75s'
    assert x[6] == '[GT](' + GT + ')'

    assert r['readme_retrieval_method'] in (
        'GITHUB_RAW_COMMIT',
        'GITHUB_GIT_BLOB_API'
    )

    assert (
        r['public_github_attempts'][-1]['result']
        == 'VERIFIED_AUTHOR_README_GIT_BLOB'
    )

    state = 'VERIFIED_AUTHOR_BLOB_ONLY'
else:
    assert not readme.exists()
    assert r['verified_readme_details'] is None
    assert r['readme_retrieval_method'] is None

    assert all(
        v['result'] == 'NOT_VERIFIED'
        for v in r['public_github_attempts']
    )

    state = 'NOT_VERIFIED'

result = {
    'schema': 'TRUST_ROBOT_R59_INDEPENDENT_SOURCE_REPLAY_V1',
    'status': 'PASS',
    'author_readme_identity': state,
    'official_gt_bytes_acquired': False,
    'r43_11_gates': 'CLOSED',
    'real_factors_health_ate_rpe': 'DENIED',
    'original_bag_or_confirmation_test_opened': False
}

with (
    OUT / 'r59_independent_validation_v1.json'
).open('x', encoding='utf-8') as h:
    json.dump(result, h, indent=2, sort_keys=True)
    h.write('\n')

print('R59_INDEPENDENT_PROVENANCE_REPLAY=PASS')
print('R59_INDEPENDENT_AUTHOR_README=' + state)
