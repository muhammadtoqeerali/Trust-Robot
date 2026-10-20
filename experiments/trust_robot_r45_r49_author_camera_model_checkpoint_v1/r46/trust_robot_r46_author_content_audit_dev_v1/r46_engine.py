"""R46: exact-source numeric comparison, not physical calibration."""
import hashlib,json,pathlib,re,sys,math

UPSTREAM='5db59c1fe38d8f1d2fb3a71f1f8c5581b8de00e5'
BASE='17536d0e9a03eb4f0b4adfb5056dc7ba63df9921'
BAG='ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1'

BLOBS={
 'calibration_results.txt':'f2b1180f9cdef4e665332a09973f9acba9d9d34e',
 'my_params_camera.yaml':'9c429c28dcfc7bea2e59be5529c79ecf46cdf3c6',
 'my_params_lidar.yaml':'a768b1a8f8baa5649009c941817a51ff3f3e00e9'
}

CLOSED=[
 'camera_intrinsics_physically_verified',
 'camera_lidar_extrinsics_physically_verified',
 'camera_imu_extrinsics_physically_verified',
 'mocap_body_to_lidar_physically_verified',
 'reference_capture_clock_physically_verified',
 'cross_sensor_synchronization_physically_verified',
 'raw_reference_available_locally',
 'metric_visual_pose_authorized',
 'real_sensor_factors_authorized',
 'health_training_authorized',
 'm2dgr_ate_rpe_authorized'
]

def need(x,k):
 if not x:raise ValueError('R46_DENIED:'+k)

def sha(blob):
 return hashlib.sha256(blob).hexdigest()

def gitblob(blob):
 return hashlib.sha1(
  b'blob '+str(len(blob)).encode()+b'\x00'+blob
 ).hexdigest()

def load(p):
 return json.loads(pathlib.Path(p).read_text())

def block(text,title):
 match=re.search(
  r'^%%\s*'+re.escape(title)+r'\s*$',
  text,re.M|re.I
 )
 need(match is not None,'SECTION:'+title)
 following=re.search(
  r'^%%\s+',text[match.end():],re.M
 )
 if following:
  return text[match.end():match.end()+following.start()]
 return text[match.end():]

NUM=re.compile(
 r'(?<![\w.])[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[Ee][-+]?\d+)?'
)

def nums(chunk):
 return [float(n) for n in NUM.findall(chunk)]

def datasets(section):
 return [
  nums(value)
  for value in re.findall(
   r'\bdata\s*:\s*\[([^\]]+)\]',section,re.S
  )
 ]

def scalar(text,name):
 found=re.findall(
  r'^[ \t]*'+re.escape(name)+r'\s*:\s*([^\n#]+)',
  text,re.M
 )
 need(len(found)==1,'SCALAR:'+name)
 value=found[0].strip().strip('"')
 try:return float(value)
 except ValueError:return value

def matrixyaml(text,name):
 matched=re.search(
  r'^[ \t]*'+re.escape(name)
  +r':\s*!!opencv-matrix\b(.*?)(?=^\S|\Z)',
  text,re.M|re.S
 )
 need(matched is not None,'MATRIX:'+name)
 data=re.search(
  r'\bdata\s*:\s*\[([^\]]+)\]',
  matched.group(1),re.S
 )
 need(data is not None,'MATRIX_DATA:'+name)
 return nums(data.group(1))

def policy(r):
 need(
  r.get('schema')==
  'TRUST_ROBOT_R46_GIT_BLOB_AUTHOR_CALIBRATION_CONTENT_AUDIT_V1'
  and r.get('trajectory_id')=='room_02'
  and r.get('split')=='train',
  'SCOPE'
 )
 need(
  r.get('github_parent')==BASE
  and r.get('bag_sha256')==BAG
  and r.get('upstream_commit')==UPSTREAM,
  'PARENTS'
 )
 need(
  set(r.get('source_sha256',{}))==set(BLOBS)
  and r.get('source_git_blobs')==BLOBS
  and r.get('upstream_source_bytes_verified_with_git_sha1') is True,
  'EXACT_BYTES'
 )
 need(
  r.get('transport')==
  'OFFLINE_PASTED_LZW12_SOURCE_CONTENT_NO_KIOS_NETWORK'
  and r.get('raw_bag_opened') is False
  and r.get('confirmation_test_accessed') is False
  and r.get('github_modified') is False,
  'BOUNDARY'
 )
 need(
  r.get('source_content_integrity_not_physical_calibration') is True
  and r.get('physical_calibration_qualified') is False
  and r.get('calibrated_sensor_factors_authorized') is False
  and r.get('health_training_authorized') is False
  and r.get('m2dgr_scoring_authorized') is False,
  'SCIENCE'
 )
 need(
  all(type(r.get(k)) is int and r[k]==0
      for k in (
       'qualified_pose_factors',
       'health_labels',
       'ate_rpe_scores'
      )),
  'SCIENCE_COUNTS'
 )
 need(
  r.get('qualification_gates')==
  {k:'NOT_QUALIFIED' for k in CLOSED},
  'ELEVEN_GATES'
 )
 need(
  r.get('next_phase')==
  'R47_AUTHOR_PARAMETER_SEMANTICS_AND_RECORDER_APPLICABILITY',
  'NEXT'
 )
 p=r.get('comparisons',{})
 need(
  p.get('realsense_intrinsics_numeric_agreement') is True
  and p.get('realsense_distortion_numeric_agreement') is True,
  'INTRINSICS_NUMERIC'
 )
 need(
  p.get('realsense_intrinsics_author_storage')==
  'TRANSPOSED_RELATIVE_TO_STANDARD_ROW_MAJOR_K'
  and p.get('realsense_resolution')==[640,480],
  'TRANSPOSED_K'
 )
 need(
  p.get('handsfree_noise_lidar_config_equal') is True
  and p.get('camera_config_imu_topic')=='/handsfree/imu'
  and p.get('camera_noise_matches_xsens_scaled_10x') is True,
  'IMU_NOISE_AMBIGUITY'
 )
 need(
  p.get(
   'lidar_to_cam_parameters_match_inverse_handsfree_to_lidar_translation'
  ) is True
  and p.get(
   'lidar_to_cam_params_match_inverse_realsense_camera_to_lidar_translation'
  ) is False,
  'EXTRINSIC_AMBIGUITY'
 )
 need(
  p.get('td_is_default_not_physical_clock_proof') is True
  and p.get('author_calibration_document_not_globally_parseable_as_yaml')
   is True,
  'CALIBRATION_FORMAT'
 )

def run(src,r45p,v45p,r43p,reportp,planp):
 previous=load(r45p)
 independent=load(v45p)
 r43=load(r43p)

 need(
  previous['schema']==
  'TRUST_ROBOT_R45_AUTHOR_UPSTREAM_CALIBRATION_INTAKE_READINESS_V1'
  and previous['author_repository_commit']==UPSTREAM
  and len(previous['upstream_candidates'])==4,
  'R45_SCOPE'
 )
 need(
  independent['source_report_sha256']==sha(r45p.read_bytes())
  and independent['upstream_immutable_git_blob_candidates']==4,
  'R45_INDEPENDENT'
 )
 need(
  r43['unresolved_gate_count']==11
  and r43['source_acquisition_status']=='NOT_ACQUIRED',
  'R43_SCIENCE'
 )

 data={}
 hashes={}

 for name,expected in BLOBS.items():
  path=src/name
  need(
   path.is_file()
   and not path.is_symlink()
   and path.stat().st_nlink==1
   and 0<path.stat().st_size<100000,
   'FILE:'+name
  )
  contents=path.read_bytes()
  need(gitblob(contents)==expected,'GIT_BLOB:'+name)
  hashes[name]=sha(contents)
  data[name]=contents.decode('utf-8')

 cal=data['calibration_results.txt']
 cam=data['my_params_camera.yaml']
 lid=data['my_params_lidar.yaml']

 real=datasets(block(cal,'Cam-pinhole-color realsense d435i'))
 hands=datasets(block(cal,'Handsfree IMU'))
 xsens=datasets(block(cal,'Xsens IMU'))

 need(
  len(real)==4
  and [len(values) for values in real]==[16,9,4,2],
  'REAL_SECTION_DATA'
 )
 need(
  len(hands)>=1 and len(hands[0])==12
  and len(xsens)>=1 and len(xsens[0])==12,
  'IMU_SECTION_DATA'
 )

 t_real=[real[0][i] for i in (3,7,11)]
 t_hands=[hands[0][i] for i in (3,7,11)]

 expected_cam_to_imu=[
  t_real[i]-t_hands[i] for i in range(3)
 ]

 app_cam_to_imu=matrixyaml(
  cam,'extrinsicTranslation'
 )
 app_cam_r=matrixyaml(
  cam,'extrinsicRotation'
 )

 need(
  len(app_cam_r)==9 and len(app_cam_to_imu)==3,
  'CAMERA_IMU_SHAPES'
 )

 intr=[
  scalar(cam,k)
  for k in ('fx','fy','cx','cy')
 ]
 actual_intr=[
  real[1][i] for i in (0,4,6,7)
 ]
 dist=[
  scalar(cam,k)
  for k in ('k1','k2','p1','p2')
 ]

 def approx(a,b):
  return (
   len(a)==len(b)
   and all(
    math.isclose(x,y,rel_tol=0,abs_tol=1e-11)
    for x,y in zip(a,b)
   )
  )

 need(
  approx(intr,actual_intr)
  and approx(dist,real[2]),
  'REALSENSE_NUMERIC'
 )
 need(
  real[1][2]==real[1][5]==0
  and real[1][6]>0 and real[1][7]>0,
  'NONCANONICAL_INTRINSICS'
 )
 need(
  [int(v) for v in real[3]]==
  [
   int(scalar(cam,'image_width')),
   int(scalar(cam,'image_height'))
  ]==[640,480],
  'IMAGE_DIMENSIONS'
 )

 names=('acc_n','acc_w','gyr_n','gyr_w')

 hand_noise={
  k:scalar(block(cal,'Handsfree IMU'),k)
  for k in names
 }
 xsens_noise={
  k:scalar(block(cal,'Xsens IMU'),k)
  for k in names
 }
 lidar_noise={
  'acc_n':scalar(lid,'imuAccNoise'),
  'acc_w':scalar(lid,'imuAccBiasN'),
  'gyr_n':scalar(lid,'imuGyrNoise'),
  'gyr_w':scalar(lid,'imuGyrBiasN')
 }
 cam_noise={
  k:scalar(cam,k)
  for k in names
 }

 need(
  approx(
   list(hand_noise.values()),
   list(lidar_noise.values())
  ),
  'HANDSFREE_LIDAR_NOISE'
 )
 need(
  approx(
   list(cam_noise.values()),
   [10*xsens_noise[k] for k in names]
  ),
  'CAMERA_XSENS_TIMES_TEN'
 )

 inverse_hands=[-v for v in t_hands]
 app_lidar=[
  scalar(cam,k)
  for k in (
   'lidar_to_cam_tx',
   'lidar_to_cam_ty',
   'lidar_to_cam_tz'
  )
 ]

 need(
  approx(app_lidar,inverse_hands),
  'APP_LIDAR_ALIAS'
 )
 need(
  not approx(app_lidar,[-v for v in t_real]),
  'NOT_REALSENSE'
 )

 need(
  scalar(cam,'imu_topic')=='/handsfree/imu'
  and scalar(lid,'imuTopic')=='handsfree/imu',
  'IMU_TOPICS'
 )
 need(
  scalar(cam,'td')==0
  and scalar(cam,'estimate_td')==0,
  'TD_SETTINGS'
 )

 delta=[
  a-b for a,b in zip(
   app_cam_to_imu,
   expected_cam_to_imu
  )
 ]

 ratios={
  k:cam_noise[k]/hand_noise[k]
  for k in names
 }

 comparison={
  'realsense_intrinsics_numeric_agreement':True,
  'realsense_distortion_numeric_agreement':True,
  'realsense_intrinsics_author_storage':
   'TRANSPOSED_RELATIVE_TO_STANDARD_ROW_MAJOR_K',
  'realsense_intrinsics_fx_fy_cx_cy':actual_intr,
  'realsense_distortion_k1_k2_p1_p2':real[2],
  'realsense_resolution':[640,480],
  'handsfree_noise_lidar_config_equal':True,
  'camera_config_imu_topic':scalar(cam,'imu_topic'),
  'camera_noise_matches_xsens_scaled_10x':True,
  'camera_noise_to_handsfree_noise_ratios':ratios,
  'lidar_to_cam_parameters_match_inverse_handsfree_to_lidar_translation':
   True,
  'lidar_to_cam_params_match_inverse_realsense_camera_to_lidar_translation':
   False,
  'author_realsense_to_lidar_translation_m':t_real,
  'author_handsfree_to_lidar_translation_m':t_hands,
  'app_camera_to_imu_translation_m':app_cam_to_imu,
  'translation_implied_by_author_sensor_offsets_m':
   expected_cam_to_imu,
  'translation_difference_app_minus_author_m':delta,
  'translation_difference_norm_m':
   math.sqrt(sum(v*v for v in delta)),
  'td_is_default_not_physical_clock_proof':True,
  'author_calibration_document_not_globally_parseable_as_yaml':
   True,
  'lidar_point_topic_setting':
   scalar(lid,'pointCloudTopic'),
  'camera_image_topic_setting':
   scalar(cam,'image_topic')
 }

 result={
  'schema':
   'TRUST_ROBOT_R46_GIT_BLOB_AUTHOR_CALIBRATION_CONTENT_AUDIT_V1',
  'trajectory_id':'room_02',
  'split':'train',
  'github_parent':BASE,
  'bag_sha256':BAG,
  'upstream_commit':UPSTREAM,
  'source_git_blobs':BLOBS,
  'source_sha256':hashes,
  'source_content_integrity_not_physical_calibration':True,
  'upstream_source_bytes_verified_with_git_sha1':True,
  'transport':
   'OFFLINE_PASTED_LZW12_SOURCE_CONTENT_NO_KIOS_NETWORK',
  'upstream_sources_acquired_as_off_git_text_files':3,
  'comparisons':comparison,
  'qualification_gates':{
   k:'NOT_QUALIFIED' for k in CLOSED
  },
  'physical_calibration_qualified':False,
  'calibrated_sensor_factors_authorized':False,
  'health_training_authorized':False,
  'm2dgr_scoring_authorized':False,
  'qualified_pose_factors':0,
  'health_labels':0,
  'ate_rpe_scores':0,
  'raw_bag_opened':False,
  'confirmation_test_accessed':False,
  'github_modified':False,
  'next_phase':
   'R47_AUTHOR_PARAMETER_SEMANTICS_AND_RECORDER_APPLICABILITY'
 }

 policy(result)

 with reportp.open('x') as f:
  json.dump(
   result,f,sort_keys=True,indent=2,
   allow_nan=False
  )
  f.write('\n')

 lines=[
  '# R46 — Official author parameter content audit',
  '',
  'Exact bytes of three published files were reconstructed offline '
  'and matched to their immutable Git blob SHA1 identifiers. '
  'Source integrity is not physical calibration certification.',
  '',
  '## Source-level numerical comparisons',
  '',
  '- RealSense 640×480 intrinsics: fx='+str(intr[0])
  +', fy='+str(intr[1])
  +', cx='+str(intr[2])
  +', cy='+str(intr[3])
  +'; distortion coefficients match the camera YAML.',
  '- Author intrinsics have cx/cy in the last row under row-major '
  'reading; automatic standard OpenCV matrix interpretation '
  'would be unsafe.',
  '- Author RealSense-to-LiDAR translation: '
  +str(t_real)+' m.',
  '- Author HandsFree-IMU-to-LiDAR translation: '
  +str(t_hands)+' m.',
  '- Camera YAML lidar_to_cam translation numerically matches '
  'the inverse HandsFree-to-LiDAR translation, not RealSense-to-LiDAR.',
  '- Camera YAML uses HandsFree IMU topic but its four noise '
  'parameters are 10 times the author Xsens values.',
  '- LiDAR YAML noise values match the author HandsFree IMU values.',
  '- Camera-to-IMU translation discrepancy against the arithmetic '
  'difference of author sensor offsets is '
  +str(delta)+' m, norm '
  +str(comparison['translation_difference_norm_m'])
  +' m. This does not validate a 6DoF transform.',
  '- Camera application td=0 and estimate_td=0 are defaults, '
  'not physical synchronization evidence.',
  '- The author calibration document contains formatting '
  'irregularities; do not parse the entire document as valid YAML.',
  '',
  '## Scientific admission',
  '',
  'All 11 physical qualification gates remain NOT QUALIFIED. '
  'No real pose factor, health label, ATE/RPE score, physical clock '
  'mapping or mocap reference qualification was produced.',
  '',
  '## Next R47',
  '',
  'Investigate frame direction, exact RealSense model and '
  'recorded topic applicability, sensor-to-body mappings and '
  'clock/IMU parameter provenance using independent receipts.',
  ''
 ]

 with planp.open('x') as f:
  f.write('\n'.join(lines))

 print('R46_AUTHOR_TEXT_BLOBS=3_GIT_SHA1_EXACT')
 print('R46_REALSENSE_INTRINSICS_AND_DISTORTION=NUMERIC_MATCH')
 print('R46_CAMERA_IMU_NOISE=XSENS_10X_NOT_HANDSFREE')
 print('R46_LIDAR_IMU_NOISE=HANDSFREE_MATCH')
 print(
  'R46_TRANSLATION_DISCREPANCY_NORM_M=%.9f'
  % comparison['translation_difference_norm_m']
 )
 print('R46_PHYSICAL_CALIBRATION_AND_FACTORS=NOT_QUALIFIED')

if __name__=='__main__':
 run(
  *(pathlib.Path(x) for x in sys.argv[1:7])
 )
