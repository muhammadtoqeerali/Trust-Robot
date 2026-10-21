"""Independent review of the original reports versus sanitized result."""
import hashlib
import json
import math
import pathlib
import sys

I, R, O = map(pathlib.Path, sys.argv[1:])

def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

r70p = I/'r70_verona_physical_source_inventory_v1.json'
r71p = I/'r71a_author_source_review_v1.json'
r72p = I/'r72_verona_source_admissibility_v1.json'
r73p = I/'r73_transfer_receipt_v1.json'

r70, r71, r72, r73 = map(load, (r70p,r71p,r72p,r73p))

quality = load(
    R/'experiments/'
    'trust_robot_r64_r68_original_gt_recovery_checkpoint_v1/'
    'evidence/r67/result/'
    'r67_rebuilt_room_02_reference_quality_v1.json'
)

result_path = O/'r74_scientific_admissibility_v1.json'
report = load(result_path)

assert report['schema'] == 'TRUST_ROBOT_R74_SANITIZED_EVIDENCE_DECISION_V1'

assert report['source_report_sha256'] == {
    'r70': sha(r70p),
    'r71a': sha(r71p),
    'r72': sha(r72p),
    'r73': sha(r73p),
}

assert report['historical_gt_sha256'] == quality['source']['sha256']
assert report['historical_gt_records'] == quality['sample_count'] == 3831

assert report['structurally_invalid_rotations'] == (
    quality['rotation_validity']['invalid_count']
) == 90

assert report['structurally_valid_rotations'] == (
    quality['rotation_validity']['valid_count']
) == 3741

assert report['invalid_rotation_sample_runs'] == len(
    quality['rotation_validity']['invalid_sample_runs']
) == 61

assert report['author_calibration_lidar_extrinsic_headings'] == (
    r72['author_calibration_extrinsic_section_count']
) == 15

assert report['author_calibration_explicit_mocap_terms'] == (
    r72['author_calibration_mocap_terms']
) == 0

assert report['r70_discovered_metadata_candidates'] == (
    len(r70['candidates'])
) == 91

assert report['r71a_dedicated_vicon_config_candidates'] == (
    len(r71['vicon_configuration_candidates'])
) == 0

assert math.isclose(
    report['gt_mean_interval_rate_hz'],
    (quality['sample_count']-1) /
    (quality['timestamp_end_seconds'] -
     quality['timestamp_start_seconds']),
    rel_tol=1e-12
)

assert math.isclose(
    report['gt_median_interval_rate_hz'],
    1.0/quality['timestamp_checks']['median_dt_seconds'],
    rel_tol=1e-12
)

assert r73['status'] == 'PASS'
assert r73['scientific_gates_closed'] == 11

assert report['scientific_gates_closed'] == 11

assert all(
    value is False
    for value in report['physical_qualification'].values()
)

for key in (
    'sampling_rate_is_clock_verification',
    'author_evo_alignment_is_extrinsic_calibration',
    'automatic_quaternion_repair_authorized',
    'real_pose_factors_authorized',
    'health_training_authorized',
    'ate_rpe_authorized',
    'raw_gt_read_in_r74',
    'raw_rosbag_read_in_r74',
    'confirmation_test_accessed',
    'git_modified_during_r74',
):
    assert report[key] is False, key

# Verify the future publication candidate contains no private absolute
# workstation paths, report excerpts or source inventory listings.
serialized = result_path.read_text(encoding='utf-8')

for forbidden in (
    '/home/kios/',
    '/mnt/hdd16T/',
    'C:\\Users\\',
    '"matching_excerpt_samples"',
    '"candidates"',
    '"path":',
):
    assert forbidden not in serialized, forbidden

validation = {
    'schema':'TRUST_ROBOT_R74_INDEPENDENT_EVIDENCE_VALIDATION_V1',
    'status':'PASS',
    'primary_report_sha256':sha(result_path),
    'r70_r71a_r72_r73_integrity':True,
    'historical_quality_comparison':True,
    'sensor_cadence_crosscheck':True,
    'sanitized_publication_boundary':True,
    'physical_frame_or_clock_qualified':False,
    'raw_gt_or_rosbag_opened':False,
    'confirmation_test_accessed':False,
    'scientific_gates_closed':11,
}

with (O/'r74_independent_validation_v1.json').open(
    'x',encoding='utf-8'
) as f:
    json.dump(validation,f,sort_keys=True,indent=2)
    f.write('\n')

print('R74_INDEPENDENT_REPORT_COMPARISON=PASS')
print('R74_INDEPENDENT_SOURCE_LINEAGE=PASS')
print('R74_SANITIZATION_REVIEW=PASS')
print('R74_INDEPENDENT_SCIENCE_DENIAL=PASS')
