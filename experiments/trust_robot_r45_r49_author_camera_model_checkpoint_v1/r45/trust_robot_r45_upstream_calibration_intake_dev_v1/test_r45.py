import ast
import copy
import pathlib
import sys
import r45_sources as m

paths = list(pathlib.Path(sys.argv[1]).glob('*.py'))
assert len(paths) == 3
for path in paths:
    ast.parse(path.read_text(), filename=str(path))

mock = {
    'schema': 'TRUST_ROBOT_R45_AUTHOR_UPSTREAM_CALIBRATION_INTAKE_READINESS_V1',
    'trajectory_id': 'room_02',
    'split': 'train',
    'local_github_parent': m.LOCAL_BASE,
    'source_bag_sha256': m.BAG,
    'author_repository': m.AUTHOR,
    'author_repository_commit': m.UPSTREAM_BASE,
    'upstream_candidates': m.registry(),
    'candidate_evidence_status': 'UPSTREAM_DISCOVERED_NOT_ACQUIRED_OR_QUALIFIED',
    'r43_gate_statuses': {gate:'NOT_QUALIFIED' for gate in m.GATES},
    'unfilled_r43_source_receipts': 11,
    'real_pose_factors_generated': 0,
    'health_labels_generated': 0,
    'ate_rpe_scores_generated': 0,
    'new_external_source_files': 0,
    'next_phase': 'R46_UPSTREAM_CALIBRATION_CONTENT_PROVENANCE_AUDIT',
    **{key:False for key in m.DENIED}
}

m.policy(mock)
count = 0
for key in m.DENIED:
    bad = copy.deepcopy(mock)
    bad[key] = True
    try:
        m.policy(bad)
    except ValueError:
        count += 1
    else:
        raise AssertionError('PROMOTION_ACCEPTED:'+key)

for key in ('real_pose_factors_generated','health_labels_generated',
            'ate_rpe_scores_generated','new_external_source_files'):
    bad = copy.deepcopy(mock)
    bad[key] = 1
    try:
        m.policy(bad)
    except ValueError:
        count += 1
    else:
        raise AssertionError('NONZERO_ACCEPTED:'+key)

for name,value in (
    ('split','confirmation_test'),
    ('local_github_parent','0'*40),
    ('source_bag_sha256','0'*64),
    ('author_repository','other/fork'),
    ('author_repository_commit','0'*40),
    ('candidate_evidence_status','CALIBRATED'),
    ('r43_gate_statuses',{}),
    ('unfilled_r43_source_receipts',10),
    ('next_phase','SCORE_NOW'),
):
    bad = copy.deepcopy(mock)
    bad[name] = value
    try:
        m.policy(bad)
    except ValueError:
        count += 1
    else:
        raise AssertionError('SOURCE_PROMOTION_ACCEPTED:'+name)

for method in ('url','blob','qualified','content','role'):
    bad=copy.deepcopy(mock)
    first=bad['upstream_candidates'][0]
    if method=='url': first['immutable_source_url']='https://evil.example/calibration'
    elif method=='blob': first['upstream_git_blob_sha1']='f'*40
    elif method=='qualified': first['physical_calibration_qualified']=True
    elif method=='content': first['file_bytes_sha256_observed_on_kios']='f'*64
    else: first['role']='QUALIFIED_FULL_EXTRINSIC'
    try:
        m.policy(bad)
    except ValueError:
        count+=1
    else:
        raise AssertionError('CANDIDATE_PROMOTION_ACCEPTED:'+method)

assert count == len(m.DENIED)+4+9+5 == 30
print('R45_PYTHON_AST=3_PASS')
print('R45_NEGATIVE_SCIENCE_SOURCE_URI_CONTROLS=30_REJECTED')
