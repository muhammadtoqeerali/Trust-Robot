"""Independent reparse of author calibration and application configurations."""
import hashlib,json,pathlib,re,sys,math

UPSTREAM='5db59c1fe38d8f1d2fb3a71f1f8c5581b8de00e5'

BLOBS={
 'calibration_results.txt':'f2b1180f9cdef4e665332a09973f9acba9d9d34e',
 'my_params_camera.yaml':'9c429c28dcfc7bea2e59be5529c79ecf46cdf3c6',
 'my_params_lidar.yaml':'a768b1a8f8baa5649009c941817a51ff3f3e00e9'
}

def need(ok,reason):
 if not ok:
  raise ValueError('R46_INDEPENDENT_DENIED:'+reason)

def sha(blob):
 return hashlib.sha256(blob).hexdigest()

def gitblob(blob):
 return hashlib.sha1(
  b'blob '+str(len(blob)).encode()+b'\x00'+blob
 ).hexdigest()

def section(text,label):
 chunks=re.split(r'(?m)^%%\s*',text)
 found=[
  x for x in chunks
  if x.strip() and x.splitlines()[0].strip().lower()==label.lower()
 ]
 need(len(found)==1,'SECTION:'+label)
 return found[0]

NUM=r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[Ee][-+]?\d+)?'

def numbers(text):
 return [
  float(x)
  for x in re.findall(NUM,text)
 ]

def data_lines(text):
 return [
  numbers(value)
  for value in re.findall(
   r'\bdata\s*:\s*\[([^\]]*)\]',
   text,re.S
  )
 ]

def numeric_key(text,key):
 matched=re.findall(
  r'(?m)^\s*'+re.escape(key)
  +r':\s*('+NUM+r')(?=\s|\Z|#)',
  text
 )
 need(len(matched)==1,'SCALAR:'+key)
 return float(matched[0])

def matrix(text,name):
 pieces=text.split(name+':',1)
 need(len(pieces)==2,'MATRIX:'+name)
 row=re.search(
  r'\bdata\s*:\s*\[([^\]]*)\]',
  pieces[1],re.S
 )
 need(row is not None,'MATRIX_VALUES')
 return numbers(row.group(1))

def verify(source_dir,r45p,reportp,planp,out):
 report=json.loads(reportp.read_text())
 r45=json.loads(r45p.read_text())
 parsed={}

 need(
  report['upstream_commit']==UPSTREAM
  and report['source_git_blobs']==BLOBS,
  'UPSTREAM_ID'
 )
 need(
  r45['author_repository_commit']==UPSTREAM
  and len(r45['upstream_candidates'])==4,
  'R45_BINDING'
 )

 for name,blob in BLOBS.items():
  p=source_dir/name
  need(
   p.is_file() and not p.is_symlink()
   and p.stat().st_nlink==1,
   'FILE:'+name
  )
  raw=p.read_bytes()

  need(
   gitblob(raw)==blob
   and report['source_sha256'][name]==sha(raw),
   'CONTENT_SHA:'+name
  )
  parsed[name]=raw.decode('utf-8')

 cal=parsed['calibration_results.txt']
 cam=parsed['my_params_camera.yaml']
 lid=parsed['my_params_lidar.yaml']

 c=data_lines(
  section(cal,'Cam-pinhole-color realsense d435i')
 )
 h=section(cal,'Handsfree IMU')
 hs=data_lines(h)
 x=section(cal,'Xsens IMU')

 need(
  [len(row) for row in c]==[16,9,4,2]
  and len(hs[0])==12,
  'CALIBRATION_SHAPES'
 )

 close=lambda a,b:math.isclose(
  a,b,abs_tol=1e-10,rel_tol=0
 )

 actual=[numeric_key(cam,k) for k in (
  'fx','fy','cx','cy'
 )]
 expected=[c[1][i] for i in (0,4,6,7)]

 need(
  all(close(a,b) for a,b in zip(actual,expected)),
  'INTRINSICS'
 )
 need(
  all(
   close(a,b)
   for a,b in zip(
    c[2],
    [
     numeric_key(cam,k)
     for k in ('k1','k2','p1','p2')
    ]
   )
  ),
  'DISTORTION'
 )

 need(
  [int(v) for v in c[3]]==[640,480],
  'IMAGE_SIZE'
 )

 names=('acc_n','acc_w','gyr_n','gyr_w')
 hf={k:numeric_key(h,k) for k in names}
 xf={k:numeric_key(x,k) for k in names}
 cc={k:numeric_key(cam,k) for k in names}
 lc={
  'acc_n':numeric_key(lid,'imuAccNoise'),
  'acc_w':numeric_key(lid,'imuAccBiasN'),
  'gyr_n':numeric_key(lid,'imuGyrNoise'),
  'gyr_w':numeric_key(lid,'imuGyrBiasN')
 }

 need(
  all(close(hf[k],lc[k]) for k in names),
  'HANDSFREE_NOISE'
 )
 need(
  all(close(cc[k],10*xf[k]) for k in names),
  'CAMERA_XSENS_NOISE'
 )

 hands=[hs[0][j] for j in (3,7,11)]
 real=[c[0][j] for j in (3,7,11)]

 camera_lidar=[
  numeric_key(cam,'lidar_to_cam_t'+axis)
  for axis in 'xyz'
 ]

 need(
  all(
   close(value,-hands[i])
   for i,value in enumerate(camera_lidar)
  ),
  'HANDFREE_ALIAS'
 )

 need(
  any(
   abs(value+real[i])>1e-4
   for i,value in enumerate(camera_lidar)
  ),
  'NOT_REALSENSE'
 )

 trans=matrix(cam,'extrinsicTranslation')
 need(len(trans)==3,'IMU_TRANSLATION')

 diff=[
  trans[i]-(real[i]-hands[i])
  for i in range(3)
 ]
 norm=math.sqrt(sum(value*value for value in diff))

 need(
  close(
   norm,
   report['comparisons']['translation_difference_norm_m']
  ),
  'TRANSLATION_DIFF'
 )

 need(
  report['comparisons']['camera_config_imu_topic']
   =='/handsfree/imu'
  and report['physical_calibration_qualified'] is False,
  'NONFACTOR'
 )

 need(
  len(report['qualification_gates'])==11
  and all(
   status=='NOT_QUALIFIED'
   for status in report['qualification_gates'].values()
  ),
  'GATES'
 )

 need(
  report['raw_bag_opened'] is False
  and report['confirmation_test_accessed'] is False
  and report['github_modified'] is False,
  'SOURCE_RESTRICTIONS'
 )

 need(
  'R47' in planp.read_text()
  and 'NOT QUALIFIED' in planp.read_text(),
  'PLAN'
 )

 proof={
  'schema':
   'TRUST_ROBOT_R46_INDEPENDENT_AUTHOR_GIT_BLOB_AND_NUMERIC_VALIDATION_V1',
  'source_report_sha256':sha(reportp.read_bytes()),
  'plan_sha256':sha(planp.read_bytes()),
  'author_git_blob_files_verified':3,
  'reparsed_numeric_groups':6,
  'noise_source_ambiguity_reproduced':True,
  'physical_calibration_authorized':False,
  'real_pose_factors_authorized':False,
  'raw_bag_opened':False,
  'confirmation_test_used':False,
  'github_modified':False
 }

 with out.open('x') as f:
  json.dump(
   proof,f,indent=2,
   sort_keys=True,allow_nan=False
  )
  f.write('\n')

 print('R46_INDEPENDENT_GIT_BLOBS=3_SHA1_AND_SHA256_MATCH')
 print('R46_INDEPENDENT_CAMERA_LIDAR_IMU_NUMERICS=REPRODUCED')
 print('R46_INDEPENDENT_PHYSICAL_CALIBRATION=NOT_QUALIFIED')
 print('R46_INDEPENDENT_VALIDATION=PASS')

if __name__=='__main__':
 verify(
  *(pathlib.Path(x) for x in sys.argv[1:6])
 )
