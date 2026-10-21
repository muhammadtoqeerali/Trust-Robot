"""Create an off-Git official author support request, without contacting anyone."""
import hashlib
import json
import pathlib
import sys

readme, identity, validation, inv, tracker, r55, protocol, out = map(
    pathlib.Path, sys.argv[1:]
)

sha = lambda data: hashlib.sha256(data).hexdigest()
blob = lambda data: hashlib.sha1(
    b'blob ' + str(len(data)).encode() + b'\0' + data
).hexdigest()

auth = readme.read_bytes()

assert blob(auth) == 'c394994a8431426c0bd4b3dcf618faf7b97d119f'

text = auth.decode('utf-8')
rows = [x for x in text.splitlines() if x.startswith('room_02|')]

assert len(rows) == 1
assert len(rows[0].split('|')) == 7

parts = rows[0].split('|')
load = lambda p: json.loads(p.read_text(encoding='utf-8'))

r, v, i, t, f, g = map(
    load, (identity, validation, inv, tracker, r55, protocol)
)

assert r['readme_verified'] is True and v['status'] == 'PASS'
assert r['verified_readme_details']['readme_sha256'] == sha(auth)
assert parts[0:2] == ['room_02', '2021-07-30']
assert parts[3] == '75s'
assert parts[6] == (
    '[GT]('
    + i['official_readme_lists_room_02_gt_candidate_url']
    + ')'
)

assert i['author_readme_git_blob_sha1'] == blob(auth)

assert f['acquisition_status'] == 'NOT_DOWNLOADED'
assert len(f['attempts']) == 2
assert all(item['http_status'] == 302 for item in f['attempts'])

assert set(t['original_gate_receipts']) == set(g['requests'])
assert len(g['requests']) == 11
assert all(
    x['status'] == 'NOT_QUALIFIED'
    for x in g['requests'].values()
)
assert all(
    x['admission_authorized'] is False
    and x['source_sha256'] is None
    for x in t['original_gate_receipts'].values()
)

assert (
    g['raw_reference_provenance_sha256']
    == i['reference_sha256_from_frozen_r43']
)

issue_url = 'https://github.com/SJTU-ViSYS/M2DGR/issues/new'

subject = (
    'M2DGR room_02: original ground-truth download access '
    'and reference-frame/timebase clarification'
)

body = f"""# {subject}

Hello M2DGR maintainers,

We are working on a reproducible, TRAIN-only scientific audit of the
original M2DGR `room_02` sequence (2021-07-30). We have its published
rosbag, but **we have not obtained the official reference GT file**.

The GT link appears in your immutable README at commit
`{i['author_commit']}` (Git blob `{blob(auth)}`):

{i['official_readme_lists_room_02_gt_candidate_url']}

Two noninteractive HTTPS attempts returned HTTP 302 redirect responses
without GT bytes. Could you confirm whether this download currently works
through a normal authorized browser session, or provide an alternative
official access mechanism for this exact original `room_02` GT export?

We will not circumvent authentication or redistribute the source.

For scientifically correct reference use, could you also clarify:

1. The canonical filename, source SHA-256, version, column schema,
   pose convention, quaternion order, units and timestamp epoch.
2. The tracked Vicon rigid body and its physically measured transform
   to `base_link` / Velodyne LiDAR, including direction and uncertainty.
3. The cause and recommended handling of 90 reference rotation records
   flagged invalid in our earlier frozen diagnostics.
4. The reference export clock and its mapping to `/velodyne_points`,
   `/handsfree/imu`, `/camera/imu` and
   `/camera/color/image_raw/compressed` sensor-header timestamps.
   Are measured clock offset/drift corrections available?
5. Which published physical camera/IMU/LiDAR calibrations apply
   specifically to `room_02`, including hardware identity and version?

Our previously recorded raw reference SHA-256 is
`{i['reference_sha256_from_frozen_r43']}`, but we have not authenticated
that historical value against newly downloaded official GT bytes.
It is not a substitute for a checksum confirmed by the authors.

Thank you for maintaining M2DGR and for any guidance.
"""

path = out / 'r60_author_github_issue_draft_v1.md'
path.write_text(body, encoding='utf-8')

receipt = {
    'schema': 'TRUST_ROBOT_R60_OFFICIAL_AUTHOR_ACCESS_REQUEST_V1',
    'phase': 'R60',
    'author_readme_git_blob_verified': True,
    'immutable_author_readme_git_sha1': blob(auth),
    'author_readme_sha256': sha(auth),
    'room_02_author_gt_link':
        i['official_readme_lists_room_02_gt_candidate_url'],
    'public_support_issue_url': issue_url,
    'draft_title': subject,
    'draft_sha256': sha(path.read_bytes()),
    'draft_status': 'PREPARED_NOT_POSTED',
    'author_contacted': False,
    'original_r55_http_302_attempts': 2,
    'official_ground_truth_acquired': False,
    'original_r43_scientific_gates_closed': 11,
    'physical_frame_or_clock_qualified': False,
    'real_sensor_pose_factors_authorized': False,
    'health_training_authorized': False,
    'ate_rpe_scoring_authorized': False,
    'frozen_split':
        '22_train_7_validation_calibration_7_confirmation_test',
    'raw_bag_opened': False,
    'confirmation_test_accessed': False,
    'github_project_modified': False,
    'next':
        'USER_REVIEW_AND_MANUALLY_POST_ISSUE_OR_AUTHOR_CONTACT_'
        'THEN_WAIT_FOR_OFFICIAL_SOURCE_OR_RESPONSE',
}

(out / 'r60_access_request_receipt_v1.json').write_text(
    json.dumps(receipt, sort_keys=True, indent=2) + '\n',
    encoding='utf-8'
)

print('R60_AUTHOR_ISSUE_DRAFT=PREPARED_NOT_POSTED')
print('R60_AUTHOR_SUPPORT_LINK=' + issue_url)
print('R60_GROUND_TRUTH=NOT_ACQUIRED')
