"""Independent off-Git author-access request and scientific-denial audit."""
import hashlib
import json
import pathlib
import sys

out, readme, inv, proto = map(pathlib.Path, sys.argv[1:])

load = lambda p: json.loads(p.read_text(encoding='utf-8'))

r = load(out / 'r60_access_request_receipt_v1.json')
i = load(inv)
g = load(proto)

raw = readme.read_bytes()
draft = (out / 'r60_author_github_issue_draft_v1.md').read_bytes()

blob = hashlib.sha1(
    b'blob ' + str(len(raw)).encode() + b'\0' + raw
).hexdigest()

assert (
    blob
    == r['immutable_author_readme_git_sha1']
    == i['author_readme_git_blob_sha1']
)

assert hashlib.sha256(raw).hexdigest() == r['author_readme_sha256']
assert hashlib.sha256(draft).hexdigest() == r['draft_sha256']

assert r['draft_status'] == 'PREPARED_NOT_POSTED'
assert r['author_contacted'] is False
assert (
    r['room_02_author_gt_link']
    == i['official_readme_lists_room_02_gt_candidate_url']
)

assert r['original_r55_http_302_attempts'] == 2
assert r['original_r43_scientific_gates_closed'] == len(g['requests']) == 11
assert r['official_ground_truth_acquired'] is False

for key in [
    'physical_frame_or_clock_qualified',
    'real_sensor_pose_factors_authorized',
    'health_training_authorized',
    'ate_rpe_scoring_authorized',
    'raw_bag_opened',
    'confirmation_test_accessed',
    'github_project_modified',
]:
    assert r[key] is False, key

text = draft.decode('utf-8')

for snippet in [
    'room_02',
    'HTTP 302',
    '90 reference rotation',
    'timestamp epoch',
    'quaternion order',
    'GT bytes',
    'base_link',
    '/velodyne_points',
]:
    assert snippet in text, snippet

assert '/home/kios/' not in text
assert 'Authorization:' not in text

assert (
    r['public_support_issue_url']
    == 'https://github.com/SJTU-ViSYS/M2DGR/issues/new'
)

report = {
    'schema': 'TRUST_ROBOT_R60_INDEPENDENT_AUTHOR_PACKET_AUDIT_V1',
    'status': 'PASS',
    'issue_draft_not_sent': True,
    'independent_draft_sha256': r['draft_sha256'],
    'gates_still_closed': 11,
    'ground_truth_acquired': False,
}

(out / 'r60_independent_validation_v1.json').write_text(
    json.dumps(report, sort_keys=True, indent=2) + '\n',
    encoding='utf-8'
)

print('R60_INDEPENDENT_ACCESS_REQUEST_AUDIT=PASS')
print('R60_ELEVEN_SCIENTIFIC_GATES=ALL_CLOSED')
