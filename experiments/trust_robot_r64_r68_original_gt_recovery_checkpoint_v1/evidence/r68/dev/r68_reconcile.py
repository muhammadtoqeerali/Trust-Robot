import hashlib
import json
import pathlib
import sys

gt, r43p, r53p, physicalp, qualityp, r67p, r66p, out = (
    pathlib.Path(x) for x in sys.argv[1:]
)

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected='79d2c6d9132ce3cf87bb87445729302cd73709a59344a3dfacc5d7788937589d'
quality_sha='8b27f25c02d04e838a88eb62980b1f2e94d0e1ed13defd0c6fa0f0b07c6bed49'

assert sha(gt)==expected
assert sha(qualityp)==quality_sha

r43=json.loads(r43p.read_text())
r53=json.loads(r53p.read_text())
physical=json.loads(physicalp.read_text())
quality=json.loads(qualityp.read_text())
r67=json.loads(r67p.read_text())
r66=json.loads(r66p.read_text())

assert r43['schema']=='TRUST_ROBOT_R43_EMPTY_EVIDENCE_RECEIPTS_V1'
assert r53['schema']=='TRUST_ROBOT_R53_UNFILLED_PHYSICAL_SOURCE_RECEIPTS_V1'
assert len(r43['gate_receipts'])==11
assert len(r53['receipts'])==5

assert all(
    x['status']=='NO_SOURCE_RECEIVED'
    and x['physical_qualification_authorized'] is False
    and x['source_sha256'] is None
    for x in r43['gate_receipts'].values()
)

assert all(
    x['status']=='NO_PHYSICAL_SOURCE_RECEIVED'
    and x['physical_measurement_qualified'] is False
    and x['independently_validated'] is False
    for x in r53['receipts'].values()
)

assert physical['interpretation']['mocap_to_lidar_transform_verified'] is False
assert physical['interpretation']['reference_timestamp_physical_measurement_event_verified'] is False
assert physical['observations']['mocap_reference']['tracked_body_origin_verified'] is False
assert physical['observations']['mocap_reference']['author_reports_occasional_tracking_failure'] is True

assert r67['exact_historical_quality_reproduction'] is True
assert r67['source_gt_sha256']==expected
assert r67['record_count']==3831
assert r67['invalid_rotation_count']==90
assert r67['invalid_rotation_run_count']==61
assert r67['scientific_gates_closed']==11

assert quality['sample_count']==3831
assert quality['source']['sha256']==expected
assert quality['rotation_validity']['invalid_count']==90
assert quality['rotation_validity']['valid_count']==3741
assert quality['translation_validity']['invalid_count']==0
assert quality['quality_summary']['evaluation_ready'] is False

indices=r66['original_audit']['invalid_rotation_sample_indices']
assert len(indices)==90
runs=quality['rotation_validity']['invalid_sample_runs']

expanded=[
    i for entry in runs
    for i in range(entry['start_sample_index'],
                   entry['end_sample_index']+1)
]
assert expanded==indices and len(runs)==61

required_raw=set(
    r43['gate_receipts']['raw_reference_available_locally']
    ['required_fields']
)
assert 'raw_bytes_sha256' in required_raw
assert 'license_and_provenance' in required_raw
assert 'file_format_and_timestamp_units' in required_raw

mocap=r53['receipts']['mocap_reference']['fields']
for name in (
    'mocap_tracked_body_origin_definition',
    'mocap_to_lidar_transform_and_direction',
    'reference_timestamp_export_semantics',
    'clock_mapping_method_and_parameters',
    'invalid_rotation_resolution_evidence_sha256',
):
    assert name in mocap and mocap[name] is None

receipt={
    'schema':'TRUST_ROBOT_R68_RECOVERED_GT_PHYSICAL_GATE_RECONCILIATION_V1',
    'trajectory':'room_02',
    'split':'train',
    'original_dataset_workstation':'iot4care-workstation',
    'original_dataset_path':'/mnt/hdd16T/ToqeerHomeBackup/toqeer/datasets/TRUST_ROBOT/M2DGR/raw/ground_truth/room_02.txt',
    'kios_staging_path':str(gt),
    'gt_sha256':expected,
    'gt_file_size_bytes':504403,
    'historical_quality_sha256':quality_sha,
    'dataset_bytes_recovered_and_verified':True,
    'historical_quality_report_byte_reproduced':True,
    'reference_numeric_structure_reproduced':True,
    'reference_sample_count':3831,
    'invalid_rotation_count':90,
    'invalid_rotation_run_count':61,
    'valid_rotation_count':3741,
    'invalid_translation_count':0,
    'historical_r43_receipts_remain_immutable':True,
    'historical_r53_receipts_remain_immutable':True,
    'historical_r43_closed_gate_count':11,
    'historical_r53_unfilled_sensor_receipts':5,
    'raw_reference_access_question_resolved_locally':True,
    'raw_reference_complete_scientific_qualification':False,
    'author_confirmed_gt_checksum':False,
    'reference_event_and_timebase_verified':False,
    'reference_to_sensor_clock_mapping_verified':False,
    'mocap_tracked_body_origin_verified':False,
    'mocap_to_lidar_transform_verified':False,
    'physical_sensor_calibration_verified':False,
    'invalid_quaternions_repaired':False,
    'automatic_reference_filter_authorized':False,
    'physical_qualification_authorizations_opened':0,
    'scientific_gates_closed':11,
    'real_pose_factors_authorized':False,
    'health_training_authorized':False,
    'ate_rpe_authorized':False,
    'raw_bag_opened':False,
    'confirmation_test_accessed':False,
    'original_gt_modified':False,
    'git_modified':False,
    'source_receipt_sha256':{
        'r43':sha(r43p),
        'r53':sha(r53p),
        'physical_semantics':sha(physicalp),
        'r67_quality':sha(qualityp),
        'r67_receipt':sha(r67p),
        'r66_rule':sha(r66p),
    },
    'remaining_independent_evidence':[
        'mocap_tracked_rigid_body_and_marker_origin',
        'mocap_body_to_lidar_metric_transform_and_direction',
        'reference_timestamp_physical_capture_event',
        'reference_timestamp_epoch_timebase_and_export_semantics',
        'reference_to_camera_imu_lidar_clock_mapping_with_uncertainty',
        'physically_verified_sensor_calibrations',
        'prospectively_declared_rotation_anomaly_handling',
        'predeclared_evaluation_association_and_alignment_protocol'
    ],
}

assert receipt['physical_qualification_authorizations_opened']==0
assert len(receipt['remaining_independent_evidence'])==8

p=out/'r68_physical_gate_reconciliation_v1.json'
with p.open('x',encoding='utf-8') as f:
    json.dump(receipt,f,indent=2,sort_keys=True)
    f.write('\n')

print('R68_ORIGINAL_REFERENCE_BYTES=VERIFIED')
print('R68_HISTORICAL_QUALITY_REPRODUCTION=VERIFIED')
print('R68_R43_FROZEN_GATES=11')
print('R68_R53_UNFILLED_SENSOR_RECEIPTS=5')
print('R68_LOCAL_RAW_GT_RECOVERY=RESOLVED')
print('R68_PHYSICAL_ORIGIN_AND_CLOCK=STILL_UNVERIFIED')
print('R68_NEW_SCIENCE_AUTHORIZATIONS=0')
