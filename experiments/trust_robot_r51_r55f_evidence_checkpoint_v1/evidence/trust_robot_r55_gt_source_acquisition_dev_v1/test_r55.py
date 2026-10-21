import ast
import copy
import pathlib
import sys

import r55_core as core
import r55_fetch as fetch

root = pathlib.Path(sys.argv[1])

for name in (
    'r55_core.py',
    'r55_fetch.py',
    'r55_independent.py',
    'test_r55.py'
):
    ast.parse(
        (root / name).read_text(),
        filename=name
    )

assert fetch.safe_url(core.URL) == (
    'sjtueducn-my.sharepoint.com'
)

bad_urls = (
    'http://sjtueducn-my.sharepoint.com/a',
    'https://evil.example/a',
    'https://sjtueducn-my.sharepoint.com.evil.example/',
    'file:///etc/passwd',
    'https://user:pass@sjtueducn-my.sharepoint.com/'
)

for url in bad_urls:
    try:
        fetch.safe_url(url)
    except ValueError:
        pass
    else:
        raise AssertionError('Unsafe redirect accepted')

rec = core.record_template(
    'NOT_DOWNLOADED',
    [{'classification': 'NO_RESPONSE'}],
    {}
)

rejected = 0

changes = (
    ('trajectory_id', 'room_03'),
    ('split', 'confirmation_test'),
    ('github_baseline', '0' * 40),
    ('raw_bag_sha256', '0' * 64),
    ('source_url', 'https://example.org/fake'),
    ('expected_reference_sha256', '0' * 64),
    ('upstream_readme_git_blob', '0' * 40),
    ('acquisition_status', 'HASH_VERIFIED'),
    ('acquisition_status', 'UNKNOWN'),
    ('r43_scientific_gates_closed', 10),
    ('r53_source_receipts_unfilled', 4),
    ('next_phase', 'R56_SCORE_NOW'),
    ('verified_reference_filename', 'fake.bin'),
    ('verified_reference_sha256', core.EXPECTED),
    ('qualified_pose_factors', 1),
    ('health_labels', 1),
    ('ate_rpe_scores', 1)
)

for key, change in changes:
    altered = copy.deepcopy(rec)
    altered[key] = change

    try:
        core.check(altered)
    except ValueError:
        rejected += 1
    else:
        raise AssertionError(
            'Unsafe source/science promotion: ' + key
        )

for key in (
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
    altered = copy.deepcopy(rec)
    altered[key] = True

    try:
        core.check(altered)
    except ValueError:
        rejected += 1
    else:
        raise AssertionError(
            'Unsafe science gate: ' + key
        )

assert rejected == 27

print('R55_PYTHON_AST=4_PASS')
print('R55_NEGATIVE_SOURCE_SCIENCE_AND_REDIRECT_CONTROLS=32_REJECTED')
