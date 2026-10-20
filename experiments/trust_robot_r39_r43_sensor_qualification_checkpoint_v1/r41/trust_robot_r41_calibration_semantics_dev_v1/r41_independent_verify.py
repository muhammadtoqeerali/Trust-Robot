"""Independent frozen-config and TRAIN reference-file verification."""

import hashlib
import json
import pathlib
import subprocess
import sys

import r41_semantics as core

def need(ok, reason):
    if not ok:
        raise ValueError('R41_INDEPENDENT_DENIED:' + reason)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def read(path):
    return json.loads(pathlib.Path(path).read_text())

def verify(repo, train, r40p, v40p, r39p,
           reportp, planp, output):

    report = read(reportp)
    core.policy(report)

    previous = read(r40p)
    previous_verification = read(v40p)

    need(
        report['r40_report_sha256'] == sha(r40p.read_bytes())
        and report['r40_independent_sha256'] == sha(v40p.read_bytes())
        and report['r39_report_sha256'] == sha(r39p.read_bytes()),
        'SOURCE_PINS'
    )

    need(
        previous_verification['source_report_sha256'] ==
            sha(r40p.read_bytes())
        and previous_verification[
            'local_candidate_files_verified'
        ] == 10,
        'PRIOR_INDEPENDENCE'
    )

    receipts = {
        item['relative_path']: item
        for item in previous['candidate_files']
    }

    need(
        set(receipts) == set(core.FILES),
        'CANDIDATE_LIST'
    )

    for row in report['configuration_semantics']:
        name = row['relative_config_path']

        need(
            name in core.FILES,
            'CONFIG_NAME'
        )

        path = repo / 'configs' / name

        need(
            path.is_file() and not path.is_symlink(),
            'CONFIG_PRESENT'
        )

        original = subprocess.check_output([
            'git', '-C', str(repo),
            'show', core.BASE + ':configs/' + name
        ])

        need(
            path.read_bytes() == original
            and sha(original) == row['sha256']
            == receipts[name]['sha256_small_file'],
            'GIT_AND_RECEIPT_SHA'
        )

        need(
            row['top_level_fields'] ==
                sorted(json.loads(original))
            and row['role'] == core.classification(name),
            'CONFIG_SEMANTICS'
        )

        need(
            row['physical_sensor_calibration_qualified'] is False,
            'CALIBRATION_NO_PROMOTION'
        )

    # Rebuild bounded TRAIN-only reference search.
    regenerated, visited, skipped = core.search_reference(train)

    need(
        regenerated == report['room_02_reference_file_candidates'],
        'REFERENCE_SEARCH_REPLAY'
    )

    need(
        visited == report['reference_search_nodes_scanned']
        and skipped == report['reference_search_entries_skipped'],
        'SEARCH_BOUNDS'
    )

    need(
        report['matching_frozen_reference_payload_count'] ==
        sum(
            item['matches_frozen_room_02_reference_sha256']
            for item in regenerated
        ),
        'REFERENCE_HASH_COUNTS'
    )

    need(
        report['room_02_reference_source'] == 'mocap'
        and report['room_02_invalid_rotation_records'] == 90,
        'REFERENCE_INVALIDITY'
    )

    need(
        report['qualified_pose_factors'] == 0
        and report['reference_scoring_authorized'] is False,
        'QUALIFICATION_CLOSED'
    )

    text = planp.read_text()

    need(
        'R41' in text
        and 'R42' in text
        and 'does not' in text
        and '90 invalid rotation' in text,
        'PLAN_BOUNDARY'
    )

    outcome = {
        'schema':
            'TRUST_ROBOT_R41_INDEPENDENT_CANDIDATE_SEMANTICS_V1',
        'r41_report_sha256': sha(reportp.read_bytes()),
        'r41_plan_sha256': sha(planp.read_bytes()),
        'git_commit_identical_configs': 10,
        'reference_candidates_rechecked': len(regenerated),
        'room_02_reference_matches_frozen_sha256':
            report['matching_frozen_reference_payload_count'],
        'physical_calibration_qualified': False,
        'real_pose_factors_authorized': False,
        'raw_bag_opened': False,
        'confirmation_test_payload_accessed': False
    }

    with output.open('x') as handle:
        json.dump(
            outcome, handle,
            indent=2,
            sort_keys=True,
            allow_nan=False
        )
        handle.write('\n')

    print('R41_INDEPENDENT_GIT_CONFIG_HASHES=10_MATCHED')
    print(
        'R41_INDEPENDENT_ROOM_02_REFERENCE_SEARCH=REPLAY_MATCH'
    )
    print(
        'R41_INDEPENDENT_PHYSICAL_CALIBRATION=NOT_QUALIFIED'
    )
    print('R41_INDEPENDENT_VALIDATION=PASS')

if __name__ == '__main__':
    verify(
        *(pathlib.Path(p) for p in sys.argv[1:9])
    )
