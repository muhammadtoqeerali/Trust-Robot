"""R55 fail-closed source acquisition contract. No physical admission."""
import hashlib

EXPECTED = (
    '79d2c6d9132ce3cf87bb87445729302cd73709a59344a3dfacc5d7788937589d'
)
BASE = '58e23861811e51c5d00f00f5d22e5cb561c4b43a'
BAG = (
    'ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1'
)
URL = (
    'https://sjtueducn-my.sharepoint.com/:t:/g/'
    'personal/594666_sjtu_edu_cn/'
    'ES-9QFWKEeBNqxyMv5dJe7EB5YxfTzi8v3x2Hf1aLObnAg'
    '?e=ifwPHL'
)
SUCCESS = 'HASH_VERIFIED'
FAILURES = ('NOT_DOWNLOADED', 'HASH_MISMATCH')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def check(record):
    def need(cond, name):
        if not cond:
            raise ValueError(
                'R55_SCIENCE_OR_SOURCE_DENIED:' + name
            )

    need(
        record.get('schema') ==
        'TRUST_ROBOT_R55_AUTHOR_REFERENCE_SHA_ACQUISITION_V1',
        'schema'
    )
    need(
        record.get('trajectory_id') == 'room_02'
        and record.get('split') == 'train',
        'split'
    )
    need(
        record.get('github_baseline') == BASE
        and record.get('raw_bag_sha256') == BAG,
        'lineage'
    )
    need(
        record.get('source_url') == URL
        and record.get('expected_reference_sha256') == EXPECTED,
        'source'
    )
    need(
        record.get('upstream_readme_git_blob') ==
        'c394994a8431426c0bd4b3dcf618faf7b97d119f',
        'readme'
    )

    status = record.get('acquisition_status')
    need(
        status == SUCCESS or status in FAILURES,
        'status'
    )
    need(
        isinstance(record.get('attempts'), list)
        and 1 <= len(record['attempts']) <= 2,
        'attempts'
    )
    need(
        record.get('r43_scientific_gates_closed') == 11
        and record.get('r53_source_receipts_unfilled') == 5,
        'gates'
    )

    for field in (
        'physical_calibration_qualified',
        'physical_clock_qualified',
        'reference_frame_qualified',
        'mocap_time_association_qualified',
        'metric_pose_authorized',
        'health_training_authorized',
        'm2dgr_ate_rpe_authorized',
        'raw_bag_opened',
        'confirmation_test_accessed',
        'github_modified'
    ):
        need(record.get(field) is False, field)

    for field in (
        'qualified_pose_factors',
        'health_labels',
        'ate_rpe_scores'
    ):
        need(
            type(record.get(field)) is int
            and record[field] == 0,
            field
        )

    if status == SUCCESS:
        need(
            record.get('verified_reference_filename') ==
            'room_02_reference_author_bytes.txt',
            'verified_filename'
        )
        need(
            record.get('verified_reference_sha256') == EXPECTED,
            'verified_sha'
        )
        need(
            record.get('next_phase') ==
            'R56_REFERENCE_CONTENT_SCHEMA_AND_TIMESTAMP_DIAGNOSTICS',
            'next'
        )
    else:
        need(
            record.get('verified_reference_filename') is None
            and record.get('verified_reference_sha256') is None,
            'unverified'
        )
        expected_next = (
            'R55_REFERENCE_HASH_DISCREPANCY_INVESTIGATION'
            if status == 'HASH_MISMATCH'
            else 'R55_OFFICIAL_GT_MANUAL_ACCESS_FALLBACK'
        )
        need(
            record.get('next_phase') == expected_next,
            'next'
        )

    return True

def record_template(status, attempts, parents, filename=None):
    if status == SUCCESS:
        next_phase = (
            'R56_REFERENCE_CONTENT_SCHEMA_AND_TIMESTAMP_DIAGNOSTICS'
        )
    elif status == 'HASH_MISMATCH':
        next_phase = (
            'R55_REFERENCE_HASH_DISCREPANCY_INVESTIGATION'
        )
    else:
        next_phase = 'R55_OFFICIAL_GT_MANUAL_ACCESS_FALLBACK'

    result = {
        'schema':
            'TRUST_ROBOT_R55_AUTHOR_REFERENCE_SHA_ACQUISITION_V1',
        'trajectory_id': 'room_02',
        'split': 'train',
        'github_baseline': BASE,
        'raw_bag_sha256': BAG,
        'source_url': URL,
        'expected_reference_sha256': EXPECTED,
        'upstream_readme_git_blob':
            'c394994a8431426c0bd4b3dcf618faf7b97d119f',
        'acquisition_status': status,
        'attempts': attempts,
        'r54_source_sha256': parents,
        'r43_scientific_gates_closed': 11,
        'r53_source_receipts_unfilled': 5,
        'verified_reference_filename':
            filename if status == SUCCESS else None,
        'verified_reference_sha256':
            EXPECTED if status == SUCCESS else None,
        'physical_calibration_qualified': False,
        'physical_clock_qualified': False,
        'reference_frame_qualified': False,
        'mocap_time_association_qualified': False,
        'metric_pose_authorized': False,
        'health_training_authorized': False,
        'm2dgr_ate_rpe_authorized': False,
        'raw_bag_opened': False,
        'confirmation_test_accessed': False,
        'github_modified': False,
        'qualified_pose_factors': 0,
        'health_labels': 0,
        'ate_rpe_scores': 0,
        'next_phase': next_phase
    }
    check(result)
    return result
