"""TRAIN room_02 calibration/reference asset inventory, no ROS bag reading."""
import hashlib,json,os,pathlib,re,stat,subprocess,sys

BASE='df78336320b3b026e448a09d39dfc571f922ae00'
BAG='ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1'
DOCUMENTS=(
 'm2dgr_trajectory_manifest_v1_split_freeze_v1.json',
 'm2dgr_calibration_evidence_v1.json',
 'm2dgr_platform_geometry_evidence_v1.json',
 'm2dgr_reference_quality_index_v1.json',
 'm2dgr_reference_physical_semantics_evidence_v1.json',
 'm2dgr_reference_temporal_association_evidence_v1.json',
 'm2dgr_gt_recording_stream_provenance_evidence_v1.json',
 'm2dgr_synchronization_evidence_v1.json',
 'm2dgr_camera_imu_synchronization_evidence_v1.json',
 'm2dgr_lidar_imu_synchronization_evidence_v1.json',
 'm2dgr_timing_evidence_index_v1.json',
)
REQUIREMENTS=(
 'camera_intrinsics_and_distortion',
 'camera_to_imu_extrinsic',
 'camera_to_lidar_extrinsic',
 'handsfree_imu_to_lidar_extrinsic',
 'imu_bias_noise_and_gravity',
 'physical_capture_clock_and_interstream_offset',
 'lidar_scan_effective_time',
 'mocap_body_origin_to_lidar_transform',
 'room_02_reference_data_quality_and_time_association',
)
TOKENS=re.compile(r'calib|intrinsic|extrinsic|camera.info|transform|ground.?truth|reference|mocap|synchron|timestamp|clock|lever.?arm|imu|velodyne|tf_static|\bgt\b',re.I)
EXTS={'.json','.yaml','.yml','.txt','.csv','.toml','.ini','.xml','.launch','.urdf','.xacro','.cfg','.md','.tf','.conf'}
MAX_NODES=4000
MAX_CANDIDATES=140
MAX_BYTES=2_000_000

def need(ok,why):
 if not ok:raise ValueError('R40_DENIED:'+why)
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(pathlib.Path(p).read_text())
def is_safe(path):
 return not path.is_symlink()

def repo_manifest(repo,name):
 p=repo/'manifests'/name
 need(p.is_file() and is_safe(p) and p.stat().st_size<1_000_000,'MANIFEST_FILE:'+name)
 raw=p.read_bytes()
 committed=subprocess.check_output(['git','-C',str(repo),'show',BASE+':manifests/'+name])
 need(raw==committed,'COMMIT_MANIFEST:'+name)
 return json.loads(raw),sha(raw)

def forbidden(path,holdout):
 parts=[p.lower() for p in path.parts]
 if 'confirmation_test' in parts:return True
 for part in parts:
  stem=pathlib.Path(part).stem.lower()
  if any(stem==h or stem.startswith(h+'_') or stem.startswith(h+'-') for h in holdout):return True
 return False

def scan(root,tag,holdout):
 # At most four levels, no symlink traversal, no entire recording or generated experiments.
 inventory=[];nodes=0;skipped=0
 if not root.is_dir() or root.is_symlink():return [],0,0
 stack=[(root,0)]
 while stack:
  folder,depth=stack.pop()
  with os.scandir(folder) as it:
   entries=sorted(it,key=lambda v:v.name)
  for entry in entries:
   nodes+=1
   need(nodes<=MAX_NODES,'ASSET_SCAN_BOUND:'+tag)
   path=pathlib.Path(entry.path)
   rel=path.relative_to(root)
   if forbidden(rel,holdout):
    skipped+=1;continue
   try:
    metadata=entry.stat(follow_symlinks=False)
   except (PermissionError,FileNotFoundError):
    skipped+=1;continue
   if stat.S_ISLNK(metadata.st_mode):
    skipped+=1;continue
   if stat.S_ISDIR(metadata.st_mode):
    if entry.name.lower() in ('.git','rosbags','bags','experiments','node_modules','__pycache__','.cache','outputs','results'):
     continue
    if depth<4:stack.append((path,depth+1))
    continue
   if not stat.S_ISREG(metadata.st_mode):continue
   if path.suffix.lower() not in EXTS:continue
   if not TOKENS.search(str(rel)):continue
   # Never open huge files; inventory is not a dataset ingestion step.
   obj={'scope':tag,'relative_path':rel.as_posix(),'size_bytes':metadata.st_size,
     'sha256_small_file':None,'scientific_calibration_verified':False}
   if 0<metadata.st_size<=MAX_BYTES:
    fd=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
     fst=os.fstat(fd)
     need(stat.S_ISREG(fst.st_mode) and fst.st_size==metadata.st_size,'ASSET_RACE:'+tag)
     content=os.read(fd,MAX_BYTES+1)
     need(len(content)==fst.st_size,'ASSET_SHORT_READ')
     obj['sha256_small_file']=sha(content)
    finally:os.close(fd)
   inventory.append(obj)
   need(len(inventory)<=MAX_CANDIDATES,'ASSET_CANDIDATE_BOUND:'+tag)
 return sorted(inventory,key=lambda a:a['relative_path']),nodes,skipped

def policy(report):
 need(report.get('schema')=='TRUST_ROBOT_R40_TRAIN_CALIBRATION_REFERENCE_ASSET_INVENTORY_V1' and report.get('trajectory_id')=='room_02' and report.get('split')=='train' and report.get('github_baseline')==BASE,'SCOPE')
 need(report.get('source_bag_sha256')==BAG and report.get('raw_bag_opened') is False and report.get('confirmation_test_accessed') is False and report.get('github_modified') is False,'SOURCE_DENIAL')
 need(report.get('qualified_real_sensor_factors')==0 and report.get('health_labels')==0 and report.get('m2dgr_scoring_authorized') is False,'FACTORS')
 need(set(report.get('qualification_requirements',{}))==set(REQUIREMENTS) and all(v['status']=='UNVERIFIED' for v in report['qualification_requirements'].values()),'GATES')
 need(set(report.get('repository_evidence_sha256',{}))==set(DOCUMENTS),'EVIDENCE_INPUTS')
 need(report.get('room_02_reference_provenance',{}).get('reference_source')=='mocap' and report['room_02_reference_provenance']['rotation_invalid_count']==90,'REFERENCE_QUALITY')
 need(len(report.get('recorded_stream_clock_domains',[]))==4 and all(x['synchronization_status']=='unverified' for x in report['recorded_stream_clock_domains']),'CLOCKS')
 need(report.get('next_phase')=='R41_TRAIN_CALIBRATION_CANDIDATE_SEMANTICS_AND_REFERENCE_CONTENT','NEXT')

def review(repo,train,workspace,out,md):
 docs={};hashes={}
 for name in DOCUMENTS:docs[name],hashes[name]=repo_manifest(repo,name)
 frozen=docs[DOCUMENTS[0]]
 room=[x for x in frozen['records'] if x['trajectory_id']=='room_02']
 need(len(room)==1 and room[0]['split']=='train','ROOM_SPLIT')
 row=room[0]
 holdout={x['trajectory_id'].lower() for x in frozen['records'] if x['split']=='confirmation_test'}
 need(len(holdout)==7,'FROZEN_TEST_SPLIT_COUNT')
 excluded={x['trajectory_id'].lower() for x in frozen['records'] if x['trajectory_id']!='room_02'}
 quality=docs['m2dgr_reference_quality_index_v1.json']
 ref=[x for x in quality['artifacts'] if x['trajectory_id']=='room_02']
 need(len(ref)==1 and ref[0]['bag_sha256']==BAG and ref[0]['reference_source']=='mocap','REFERENCE_PROVENANCE')
 ref=ref[0]
 need(ref['rotation_invalid_count']==90 and ref['translation_invalid_count']==0,'REFERENCE_INVALIDITY')
 calibration=docs['m2dgr_calibration_evidence_v1.json']['interpretation']
 refsem=docs['m2dgr_reference_physical_semantics_evidence_v1.json']['interpretation']
 need(calibration['camera_intrinsics_verified'] is False and calibration['handsfree_lidar_full_extrinsic_verified'] is False and calibration['dataset_calibration_verified'] is False,'CALIBRATION_CONSERVATIVE')
 need(refsem['mocap_reference_body_origin_verified'] is False and refsem['reference_timestamp_physical_measurement_event_verified'] is False,'MOCAP_CONSERVATIVE')
 streams=[]
 for a in row['streams']:
  synch=[s for s in row['synchronization'] if s['stream_id']==a['stream_id']]
  need(len(synch)==1 and synch[0]['verification_status']=='unverified' and synch[0]['fixed_offset_seconds'] is None,'CLOCK_CONSERVATIVE')
  streams.append({'topic':a['stream_id'],'frame_id':a['frame_id'],'clock_domain':a['clock_domain'],
   'header_timestamp_unit':a['timestamp_unit'],'synchronization_status':'unverified','physically_verified_offset_seconds':None})
 need(len(streams)==4,'STREAM_COUNT')
 roots=[(train,'recorded_m2dgr_train')]
 for name in ('calib','calibration','calibrations','groundtruth','ground_truth','reference','references','metadata'):
  roots.append((workspace/name,'workspace_'+name))
 for name in ('calib','calibration','config','configs'):
  roots.append((repo/name,'repository_'+name))
 assets=[];scanned={};skipped={}
 for root,tag in roots:
  found,count,denied=scan(root,tag,excluded)
  assets+=found;scanned[tag]=count;skipped[tag]=denied
 need(len(assets)<=250,'TOTAL_CANDIDATE_BOUND')
 known_paths=['raw/groundtruth/room_02.txt','raw/ground_truth/room_02.txt','groundtruth/room_02.txt',
  'ground_truth/room_02.txt','raw/gt/room_02.txt','audit/reference_quality/room_02_reference_quality.json',
  'checksums/room_02.txt.sha256']
 direct=[]
 for rel in known_paths:
  p=train/rel
  direct.append({'path_relative_to_train':rel,'present_regular_file':p.is_file() and not p.is_symlink(),
   'scientific_reference_qualified':False})
 req={k:{'status':'UNVERIFIED','present_candidate_is_not_qualification':True} for k in REQUIREMENTS}
 result={
  'schema':'TRUST_ROBOT_R40_TRAIN_CALIBRATION_REFERENCE_ASSET_INVENTORY_V1',
  'trajectory_id':'room_02','split':'train','github_baseline':BASE,'source_bag_sha256':BAG,
  'repository_evidence_sha256':hashes,'existing_calibration_interpretation':calibration,
  'existing_reference_semantics':{'mocap_reference_body_origin_verified':refsem['mocap_reference_body_origin_verified'],
    'mocap_to_lidar_transform_verified':refsem['mocap_to_lidar_transform_verified'],
    'reference_timestamp_physical_measurement_event_verified':refsem['reference_timestamp_physical_measurement_event_verified']},
  'room_02_reference_provenance':{'reference_source':ref['reference_source'],
   'rotation_invalid_count':ref['rotation_invalid_count'],
   'translation_invalid_count':ref['translation_invalid_count'],
   'raw_reference_sha256_provenance_only':ref['raw_reference_sha256'],
   'reference_quality_artifact_relative_path':ref['artifact_relative_path']},
  'recorded_stream_clock_domains':streams,'candidate_files':assets,
  'explicit_room_02_reference_path_receipts':direct,
  'filesystem_scan_nodes_by_scope':scanned,'filesystem_skipped_items_by_scope':skipped,
  'qualification_requirements':req,'physical_calibration_verified':False,
  'reference_to_sensor_transform_verified':False,'physical_capture_time_verified':False,
  'raw_bag_opened':False,'confirmation_test_accessed':False,'github_modified':False,
  'qualified_real_sensor_factors':0,'health_labels':0,'m2dgr_scoring_authorized':False,
  'next_phase':'R41_TRAIN_CALIBRATION_CANDIDATE_SEMANTICS_AND_REFERENCE_CONTENT'
 }
 policy(result)
 with out.open('x') as h:json.dump(result,h,sort_keys=True,indent=2,allow_nan=False);h.write('\n')
 lines=['# R40 — Existing calibration and reference evidence inventory','',
  'All findings are provenance or candidate inventory only; NOT QUALIFIED as physical calibration.',
  '','## Frozen room_02 reference','',
  f"- Reference family: {ref['reference_source']} (mocap).",
  f"- Source reference-quality index reports {ref['rotation_invalid_count']} invalid rotation records and {ref['translation_invalid_count']} invalid translation records.",
  '- Reference body origin, mocap-to-LiDAR transform and reference timestamp physical-event semantics remain unverified.','',
  '## Existing timing evidence','']
 for a in streams:lines.append(f"- `{a['topic']}` uses `{a['frame_id']}` / `{a['clock_domain']}`; physical clock offset unverified.")
 lines+=['','## Local asset observations','',f'- Candidate files discovered: {len(assets)}',
  f"- Explicit room_02 reference path receipts found: {sum(x['present_regular_file'] for x in direct)} of {len(direct)}",'']
 for a in assets[:80]:lines.append(f"- `{a['scope']}/{a['relative_path']}`: {a['size_bytes']} bytes; SHA256={a['sha256_small_file'] or 'not-read-large'}; NOT QUALIFIED")
 lines+=['','## Blocking qualifications','']
 for k in REQUIREMENTS:lines.append('- '+k.replace('_',' ')+': UNVERIFIED')
 lines+=['','## Next — R41','',
  'Inspect the actual in-scope candidate file structure, units, transform direction, clock origin and TRAIN reference validity; preserve all prior frozen judgments and do not infer physical calibration from file presence.','',
  'No confirmation-test data or original bag bytes were opened.','']
 with md.open('x') as h:h.write('\n'.join(lines))
 print('R40_EXISTING_REPOSITORY_EVIDENCE_MANIFESTS=%d_COMMIT_VERIFIED'%len(DOCUMENTS))
 print('R40_ROOM_02_REFERENCE=mocap ROTATION_INVALID=%d TRANSLATION_INVALID=%d'%(ref['rotation_invalid_count'],ref['translation_invalid_count']))
 print('R40_LOCAL_CANDIDATE_FILES=%d'%len(assets))
 print('R40_EXPLICIT_REFERENCE_PATHS_PRESENT=%d'%sum(x['present_regular_file'] for x in direct))
 print('R40_PHYSICAL_QUALIFICATION_REQUIREMENTS=%d_UNVERIFIED'%len(REQUIREMENTS))
 print('R40_RAW_BAG_OPENED=NO')

if __name__=='__main__':
 review(*(pathlib.Path(x) for x in sys.argv[1:6]))
