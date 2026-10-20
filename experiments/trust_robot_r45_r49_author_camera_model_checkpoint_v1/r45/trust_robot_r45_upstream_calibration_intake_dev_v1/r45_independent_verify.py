"""Independent R45 immutable source-candidate and R43 status verification."""
import hashlib
import json
import pathlib
import sys
import r45_sources as m

def need(condition, reason):
    if not condition:
        raise ValueError('R45_INDEPENDENT_DENIED:' + reason)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verify(r43p, emptyp, v43p, r42p, reportp, planp, outputp):
    report = json.loads(reportp.read_text())
    m.policy(report)
    upstream = json.loads(r43p.read_text())
    receipts = json.loads(emptyp.read_text())
    previous = json.loads(v43p.read_text())
    ros = json.loads(r42p.read_text())
    need(report['r43_source_sha256'] == {
        'protocol': sha(r43p),
        'empty_receipts': sha(emptyp),
        'independent_validation': sha(v43p),
        'r42_connection_report': sha(r42p)
    }, 'SOURCE_SHA')
    need(previous['r43_protocol_sha256'] == sha(r43p)
         and previous['unfilled_receipts_sha256'] == sha(emptyp), 'UPSTREAM_INDEPENDENT')
    need(set(report['r43_gate_statuses']) == set(upstream['requests'])
         == set(receipts['gate_receipts']), 'EVIDENCE_SCOPE')
    for gate in m.GATES:
        row = receipts['gate_receipts'][gate]
        need(row['status'] == 'NO_SOURCE_RECEIVED'
             and row['source_uri'] is None
             and row['source_sha256'] is None
             and row['independent_validation_sha256'] is None
             and row['physical_qualification_authorized'] is False
             and all(value is None for value in row['required_fields'].values()), 'NO_SOURCE:' + gate)
    need(ros['connection_count'] == 15
         and all(ros[k] == 0 for k in ('camera_info_topic_count','tf_topic_count','mocap_or_pose_reference_topic_count')),
         'PRIOR_TOPIC_SCOPE')
    # Reconstruct immutable Git URLs rather than accepting arbitrary URIs.
    for row, source in zip(report['upstream_candidates'], m.SOURCES):
        path, blob, role, note = source
        need(row['path'] == path and row['upstream_git_blob_sha1'] == blob
             and row['role'] == role and row['interpretation'] == note
             and row['immutable_source_url'] ==
             'https://github.com/SJTU-ViSYS/M2DGR/blob/'+m.UPSTREAM_BASE+'/'+path,
             'IMMUTABLE_UPSTREAM_URI')
        need(row['file_bytes_sha256_observed_on_kios'] is None
             and row['physical_calibration_qualified'] is False
             and row['room_02_sensor_applicability_verified'] is False,
             'NO_PHYSICAL_ADMISSION')
    plan = planp.read_text()
    need('R46' in plan and 'no file content downloaded' in plan.lower()
         and 'not been demonstrated' in plan, 'PLAN_SCIENCE')
    result = {
        'schema': 'TRUST_ROBOT_R45_INDEPENDENT_AUTHOR_SOURCE_DISCOVERY_VALIDATION_V1',
        'source_report_sha256': sha(reportp),
        'action_plan_sha256': sha(planp),
        'upstream_immutable_git_blob_candidates': len(m.SOURCES),
        'r43_missing_evidence_gate_receipts_verified': len(m.GATES),
        'upstream_file_content_read_on_kios': False,
        'external_calibration_bytes_sha256_verified_on_kios': False,
        'physical_calibration_admitted': False,
        'real_pose_factors_authorized': False,
        'confirmation_test_used': False,
        'github_modified': False,
    }
    with outputp.open('x') as f:
        json.dump(result, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')
    print('R45_INDEPENDENT_AUTHOR_SOURCE_IDS=4_EXACT')
    print('R45_INDEPENDENT_R43_EMPTY_RECEIPTS=11_CONFIRMED')
    print('R45_INDEPENDENT_CALIBRATION_ADMISSION=DENIED')
    print('R45_INDEPENDENT_VALIDATION=PASS')

if __name__ == '__main__':
    verify(*(pathlib.Path(x) for x in sys.argv[1:8]))
