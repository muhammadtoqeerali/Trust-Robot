"""R74: fail-closed scientific evidence review.

Inputs remain private; only sanitized derived decisions are emitted.
"""

import hashlib
import json
import math
import pathlib
import sys

BASE = '6873da42fda57f23a46c0ecb2c788489802faa8c'
GT = '79d2c6d9132ce3cf87bb87445729302cd73709a59344a3dfacc5d7788937589d'
QUALITY = '8b27f25c02d04e838a88eb62980b1f2e94d0e1ed13defd0c6fa0f0b07c6bed49'

PINS = {
    'r70': 'ae0ff5e201f449d34d749b0b6f22254e4455fb0b5422862cc127103e84eba5a0',
    'r71a': 'c0b5264a70ca708d7b532b77388dfe6ce90d71ebba4b47011e48f522d25661e5',
    'r72': 'efcbcbc85dc02732e1fd130c840b921d0abdab72dfda494dd3490b8609fb3d74',
    'r73': 'a90b3bbd9de75e2c6a50a6121eec1779b40a8e48362e38308480d736f6a877c0',
}

def need(ok, msg):
    if not ok:
        raise ValueError('R74_SCIENCE_REVIEW_DENIED:' + msg)

def read_json(path):
    return json.loads(pathlib.Path(path).read_text(encoding='utf-8'))

def digest(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()

def close(a, b):
    return math.isclose(
        float(a), float(b), rel_tol=1e-9, abs_tol=1e-9
    )

def validate(r70, r71, r72, r73, quality, indoor, physical):
    schemas = {
        'r70': 'TRUST_ROBOT_R70_VERONA_PHYSICAL_SOURCE_INVENTORY_V1',
        'r71a': 'TRUST_ROBOT_R71A_AUTHOR_SOURCE_REVIEW_V1',
        'r72': 'TRUST_ROBOT_R72_VERONA_SOURCE_ADMISSIBILITY_V1',
        'r73': 'TRUST_ROBOT_R73_VERONA_KIOS_EVIDENCE_HANDOFF_V1',
    }

    reports = {
        'r70': r70,
        'r71a': r71,
        'r72': r72,
        'r73': r73,
    }

    for name, obj in reports.items():
        need(obj.get('schema') == schemas[name], name + '_SCHEMA')
        need(obj.get('scientific_gates_closed') == 11, name + '_GATES')

    for name in ('r70', 'r71a', 'r72'):
        need(
            reports[name].get('trajectory') == 'room_02'
            and reports[name].get('split') == 'train',
            name + '_TRAIN_IDENTITY'
        )

    need(r73.get('status') == 'PASS', 'HANDOFF_STATUS')
    need(r73.get('git_baseline') == BASE, 'HANDOFF_GIT_BASE')
    need(r73.get('evidence_files') == 3, 'HANDOFF_COUNT')
    need(r73.get('all_source_checksums_verified') is True,
         'HANDOFF_HASHES')
    need(r73.get('cross_report_lineage_verified') is True,
         'HANDOFF_LINEAGE')

    expected_receipt_pins = {
        'r70_verona_physical_source_inventory_v1.json': PINS['r70'],
        'r71a_author_source_review_v1.json': PINS['r71a'],
        'r72_verona_source_admissibility_v1.json': PINS['r72'],
    }

    need(
        r73.get('evidence_sha256') == expected_receipt_pins,
        'TRANSFER_HASH_MANIFEST'
    )

    need(r70.get('raw_gt_sha256_from_historical_index') == GT,
         'R70_GT_LINEAGE')
    need(r71.get('gt_historical_sha256') == GT,
         'R71_GT_LINEAGE')

    need(r71.get('r70_sha256') == PINS['r70'],
         'R70_R71_LINEAGE')

    need(r72.get('source_pins', {}).get('r70_inventory') == PINS['r70'],
         'R70_R72_LINEAGE')

    need(r72.get('source_pins', {}).get('r71a_review') == PINS['r71a'],
         'R71_R72_LINEAGE')

    need(
        r72.get('source_pins', {}).get(
            'historical_reference_quality'
        ) == QUALITY,
        'R72_HISTORICAL_QUALITY_LINEAGE'
    )

    need(
        r70.get('readable_candidates') == 91
        and isinstance(r70.get('candidates'), list)
        and len(r70['candidates']) == 91,
        'R70_CANDIDATE_POPULATION'
    )

    need(
        r71.get('vicon_configuration_candidates') == [],
        'R71_CONFIG_CANDIDATES'
    )

    need(
        r71.get('calibration_matching_line_count') == 31
        and r71.get('sensor_description_matching_line_count') == 35,
        'R71_LINE_COUNTS'
    )

    sources = r71.get('original_author_sources', {})

    need(
        sources.get('author_calibration', {}).get('sha256')
        == 'e515207fcf53668953a21a2e4d990643007a3a12ad54b91c456a8ee8a8100a90',
        'AUTHOR_CALIBRATION_PROVENANCE'
    )

    need(
        sources.get('author_sensor_description', {}).get('sha256')
        == '394792f5ebf338527bc8a9fdd88930bbcd32ba9197a545b0bad49337ac7d5f6e',
        'AUTHOR_SENSOR_PROVENANCE'
    )

    need(r72.get('author_calibration_extrinsic_section_count') == 15,
         'CALIBRATION_SECTION_COUNT')
    need(r72.get('author_calibration_mocap_terms') == 0,
         'CALIBRATION_MOCAP_TERMS')
    need(close(r72.get('author_vicon_nominal_rate_hz'), 50.0),
         'VICON_RATE')

    claims = r72.get('claims', {})

    expected_claims = {
        'room_reference_family_is_mocap':
            'SUPPORTED_BY_MAINTAINER',
        'vicon_vero_2p2_nominal_50hz':
            'SUPPORTED_BY_AUTHOR_DESCRIPTION',
        'lidar_relative_extrinsics_published_for_other_sensors':
            'SOURCE_SECTIONS_OBSERVED',
        'mocap_tracking_failure_can_affect_quaternions':
            'REPORTED_BY_MAINTAINER',
        'gt_structural_quality':
            'EXACT_HISTORICAL_REPORT_REPRODUCED',
        'mocap_body_origin': 'UNVERIFIED',
        'mocap_to_lidar_se3': 'UNVERIFIED',
        'gt_timestamp_event_and_timebase': 'UNVERIFIED',
        'gt_to_ros_clock_mapping': 'UNVERIFIED',
        'invalid_rotation_handling': 'NOT_AUTOMATICALLY_AUTHORIZED',
    }

    need(set(claims) == set(expected_claims), 'CLAIM_NAMES')

    for name, status in expected_claims.items():
        need(
            claims[name].get('status') == status,
            'CLAIM_STATUS:' + name
        )

    need(
        quality.get('sample_count') == 3831
        and quality['source']['sha256'] == GT
        and quality['reference_source'] == 'mocap',
        'HISTORICAL_REFERENCE'
    )

    need(
        quality['rotation_validity']['invalid_count'] == 90
        and quality['rotation_validity']['valid_count'] == 3741
        and len(quality['rotation_validity']['invalid_sample_runs']) == 61
        and quality['translation_validity']['invalid_count'] == 0,
        'HISTORICAL_QUALITY_MASK'
    )

    t0 = quality['timestamp_start_seconds']
    t1 = quality['timestamp_end_seconds']
    dt = quality['timestamp_checks']['median_dt_seconds']
    span = t1 - t0

    need(close(r72.get('reference_time_span_seconds'), span),
         'TIMESTAMP_SPAN')

    need(
        close(
            r72.get('reference_mean_interval_rate_hz'),
            3830 / span
        ),
        'MEAN_SAMPLING_RATE'
    )

    need(
        close(
            r72.get('reference_median_interval_rate_hz'),
            1.0 / dt
        ),
        'MEDIAN_SAMPLING_RATE'
    )

    need(
        quality['quality_summary']['evaluation_ready'] is False
        and quality['quality_summary']['physical_quality_verified'] is False
        and quality['quality_summary']['synchronization_verified'] is False
        and quality['continuous_time_coverage']['verified'] is False,
        'HISTORICAL_SCIENCE_DENIAL'
    )

    need(
        indoor['interpretation']['mocap_to_lidar_transform_verified']
        is False
        and indoor['interpretation']['mocap_tracked_body_origin_verified']
        is False
        and indoor['interpretation']['reference_timestamp_physical_measurement_event_verified']
        is False,
        'INDOOR_SEMANTICS_DENIAL'
    )

    need(
        physical['interpretation']['mocap_to_lidar_transform_verified']
        is False
        and physical['interpretation']['reference_timestamp_physical_measurement_event_verified']
        is False
        and physical['interpretation']['synchronization_verified']
        is False,
        'PHYSICAL_SEMANTICS_DENIAL'
    )

    for key in (
        'source_documents_are_capture_clock_receipts',
        'published_mocap_transform_independently_verified',
        'physical_reference_clock_verified',
        'clock_synchronization_verified',
        'physical_calibration_verified',
        'mocap_rotation_failures_all_explained',
        'automatic_filter_or_repair_authorized',
        'evaluation_alignment_selected',
        'reference_interpolation_authorized',
        'association_tolerance_selected',
        'real_pose_factors_authorized',
        'health_training_authorized',
        'ate_rpe_authorized',
        'raw_gt_opened',
        'raw_rosbag_opened',
        'confirmation_test_accessed',
        'original_data_modified',
        'git_modified',
    ):
        need(r72.get(key) is False, 'R72_DENIAL:' + key)

    for obj, keys in (
        (r70, (
            'raw_gt_file_opened_in_this_phase',
            'raw_rosbag_opened',
            'confirmation_test_accessed',
            'git_modified',
        )),
        (r71, (
            'raw_gt_opened',
            'raw_rosbag_opened',
            'confirmation_test_accessed',
            'git_modified',
        )),
        (r73, (
            'original_gt_transferred',
            'rosbags_transferred',
            'physical_frame_qualified',
            'physical_clock_qualified',
            'confirmation_test_accessed',
            'git_modified',
            'github_push_performed',
        )),
    ):
        for key in keys:
            need(obj.get(key) is False, 'PRESERVATION:' + key)

    # No source paths, raw excerpts, or private dataset contents
    # are copied into this derived GitHub-safe decision.
    return {
        'schema': 'TRUST_ROBOT_R74_SANITIZED_EVIDENCE_DECISION_V1',
        'trajectory': 'room_02',
        'split': 'train',
        'git_parent_commit': BASE,
        'source_report_sha256': dict(PINS),
        'historical_gt_sha256': GT,
        'historical_quality_sha256': QUALITY,
        'r70_discovered_metadata_candidates': 91,
        'r71a_dedicated_vicon_config_candidates': 0,
        'author_calibration_lidar_extrinsic_headings': 15,
        'author_calibration_explicit_mocap_terms': 0,
        'author_vicon_nominal_rate_hz': 50,
        'historical_gt_records': 3831,
        'historical_gt_span_seconds': span,
        'gt_mean_interval_rate_hz': 3830 / span,
        'gt_median_interval_rate_hz': 1.0 / dt,
        'structurally_valid_rotations': 3741,
        'structurally_invalid_rotations': 90,
        'invalid_rotation_sample_runs': 61,
        'structurally_invalid_translations': 0,
        'author_provenance_support': {
            'indoor_mocap_source': True,
            'vicon_nominal_rate_description': True,
            'published_non_mocap_sensor_calibration_sections': True,
            'mocap_tracking_failure_reported': True,
        },
        'physical_qualification': {
            'mocap_body_origin_verified': False,
            'mocap_to_lidar_se3_verified': False,
            'gt_capture_event_verified': False,
            'gt_timebase_export_verified': False,
            'gt_to_ros_clock_mapping_verified': False,
            'physical_sensor_calibration_verified': False,
            'continuous_reference_coverage_verified': False,
            'rotation_filter_authorized': False,
            'alignment_mode_selected': False,
            'association_tolerance_selected': False,
        },
        'sampling_rate_is_clock_verification': False,
        'author_evo_alignment_is_extrinsic_calibration': False,
        'automatic_quaternion_repair_authorized': False,
        'real_pose_factors_authorized': False,
        'health_training_authorized': False,
        'ate_rpe_authorized': False,
        'scientific_gates_closed': 11,
        'raw_gt_read_in_r74': False,
        'raw_rosbag_read_in_r74': False,
        'confirmation_test_accessed': False,
        'git_modified_during_r74': False,
        'pending_authoritative_evidence': [
            'mocap_rigid_body_and_marker_set_origin',
            'mocap_body_to_lidar_transform_direction_and_units',
            'reference_capture_event_and_export_timebase',
            'physical_cross_sensor_clock_mapping_and_uncertainty',
            'prospective_invalid_rotation_policy',
        ],
    }

def main(argv):
    root = pathlib.Path(argv[1])
    repo = pathlib.Path(argv[2])
    output = pathlib.Path(argv[3])

    paths = {
        'r70': root/'r70_verona_physical_source_inventory_v1.json',
        'r71a': root/'r71a_author_source_review_v1.json',
        'r72': root/'r72_verona_source_admissibility_v1.json',
        'r73': root/'r73_transfer_receipt_v1.json',
    }

    for name, path in paths.items():
        need(digest(path) == PINS[name], 'INPUT_SHA:' + name)

    r70, r71, r72, r73 = (
        read_json(paths[name])
        for name in ('r70','r71a','r72','r73')
    )

    quality_path = (
        repo/'experiments/'
        'trust_robot_r64_r68_original_gt_recovery_checkpoint_v1/'
        'evidence/r67/result/'
        'r67_rebuilt_room_02_reference_quality_v1.json'
    )

    quality = read_json(quality_path)
    indoor = read_json(
        repo/'manifests/'
        'm2dgr_indoor_reference_origin_semantics_evidence_v1.json'
    )
    physical = read_json(
        repo/'manifests/'
        'm2dgr_reference_physical_semantics_evidence_v1.json'
    )

    result = validate(
        r70, r71, r72, r73, quality, indoor, physical
    )

    target = output/'r74_scientific_admissibility_v1.json'

    with target.open('x', encoding='utf-8') as f:
        json.dump(result, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')

    print('R74_CROSS_REPORT_LINEAGE=PASS')
    print('R74_HISTORICAL_QUALITY_COMPARISON=PASS')
    print('R74_PHYSICAL_ADMISSION=DENIED')
    print('R74_SANITIZED_SCIENTIFIC_REPORT=CREATED')

if __name__ == '__main__':
    main(sys.argv)
