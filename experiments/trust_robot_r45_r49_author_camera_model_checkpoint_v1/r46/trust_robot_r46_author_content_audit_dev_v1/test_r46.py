import ast,copy,pathlib,sys
import r46_engine as e
import r46_decode as decoder

root=pathlib.Path(sys.argv[1])

for name in (
 'r46_decode.py',
 'r46_engine.py',
 'r46_independent.py',
 'test_r46.py'
):
 ast.parse((root/name).read_text(),filename=name)

mock={
 'schema':'TRUST_ROBOT_R46_GIT_BLOB_AUTHOR_CALIBRATION_CONTENT_AUDIT_V1',
 'trajectory_id':'room_02',
 'split':'train',
 'github_parent':e.BASE,
 'bag_sha256':e.BAG,
 'upstream_commit':e.UPSTREAM,
 'source_git_blobs':e.BLOBS,
 'source_sha256':{k:'a'*64 for k in e.BLOBS},
 'upstream_source_bytes_verified_with_git_sha1':True,
 'transport':'OFFLINE_PASTED_LZW12_SOURCE_CONTENT_NO_KIOS_NETWORK',
 'source_content_integrity_not_physical_calibration':True,
 'raw_bag_opened':False,
 'confirmation_test_accessed':False,
 'github_modified':False,
 'physical_calibration_qualified':False,
 'calibrated_sensor_factors_authorized':False,
 'health_training_authorized':False,
 'm2dgr_scoring_authorized':False,
 'qualified_pose_factors':0,
 'health_labels':0,
 'ate_rpe_scores':0,
 'qualification_gates':{k:'NOT_QUALIFIED' for k in e.CLOSED},
 'next_phase':'R47_AUTHOR_PARAMETER_SEMANTICS_AND_RECORDER_APPLICABILITY',
 'comparisons':{
  'realsense_intrinsics_numeric_agreement':True,
  'realsense_distortion_numeric_agreement':True,
  'realsense_intrinsics_author_storage':
   'TRANSPOSED_RELATIVE_TO_STANDARD_ROW_MAJOR_K',
  'realsense_resolution':[640,480],
  'handsfree_noise_lidar_config_equal':True,
  'camera_config_imu_topic':'/handsfree/imu',
  'camera_noise_matches_xsens_scaled_10x':True,
  'lidar_to_cam_parameters_match_inverse_handsfree_to_lidar_translation':True,
  'lidar_to_cam_params_match_inverse_realsense_camera_to_lidar_translation':False,
  'td_is_default_not_physical_clock_proof':True,
  'author_calibration_document_not_globally_parseable_as_yaml':True
 }
}

e.policy(mock)
rejected=0

for key in (
 'raw_bag_opened',
 'confirmation_test_accessed',
 'github_modified',
 'physical_calibration_qualified',
 'calibrated_sensor_factors_authorized',
 'health_training_authorized',
 'm2dgr_scoring_authorized'
):
 altered=copy.deepcopy(mock)
 altered[key]=True
 try:e.policy(altered)
 except ValueError:rejected+=1
 else:raise AssertionError('UNSAFE:'+key)

for key in (
 'qualified_pose_factors','health_labels','ate_rpe_scores'
):
 altered=copy.deepcopy(mock)
 altered[key]=1
 try:e.policy(altered)
 except ValueError:rejected+=1
 else:raise AssertionError('NONZERO:'+key)

for key,value in (
 ('split','confirmation_test'),
 ('trajectory_id','room_03'),
 ('github_parent','0'*40),
 ('bag_sha256','0'*64),
 ('upstream_commit','0'*40),
 ('source_git_blobs',{}),
 ('source_sha256',{}),
 ('transport','NETWORK_DOWNLOAD'),
 ('next_phase','SCORE_NOW')
):
 altered=copy.deepcopy(mock)
 altered[key]=value
 try:e.policy(altered)
 except ValueError:rejected+=1
 else:raise AssertionError('SOURCE_PROMOTION:'+key)

for change in (
 'qualify_gate',
 'approve_intrinsics',
 'approve_source',
 'change_noise',
 'change_transform'
):
 altered=copy.deepcopy(mock)
 if change=='qualify_gate':
  altered['qualification_gates'][e.CLOSED[0]]='QUALIFIED'
 elif change=='approve_intrinsics':
  altered['comparisons']['realsense_intrinsics_numeric_agreement']=False
 elif change=='approve_source':
  altered['source_content_integrity_not_physical_calibration']=False
 elif change=='change_noise':
  altered['comparisons']['camera_noise_matches_xsens_scaled_10x']=False
 else:
  altered['comparisons'][
   'lidar_to_cam_params_match_inverse_realsense_camera_to_lidar_translation'
  ]=True
 try:e.policy(altered)
 except ValueError:rejected+=1
 else:raise AssertionError('PARAMETER_PROMOTION:'+change)

assert rejected==24

print('R46_PYTHON_AST=4_PASS')
print('R46_NEGATIVE_SCIENCE_AND_PROVENANCE_CONTROLS=24_REJECTED')
