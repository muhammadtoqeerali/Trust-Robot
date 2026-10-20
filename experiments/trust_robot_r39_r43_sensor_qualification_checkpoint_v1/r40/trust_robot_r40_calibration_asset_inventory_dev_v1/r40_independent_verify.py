"""Independently verify R40 Git-sourced evidence and local file receipts."""
import hashlib,json,os,pathlib,stat,subprocess,sys
import r40_inventory as inv

def need(ok,why):
 if not ok:raise ValueError('R40_INDEPENDENT_DENIED:'+why)
def sha(blob):return hashlib.sha256(blob).hexdigest()
def load(p):return json.loads(pathlib.Path(p).read_text())

def verify(repo,train,workspace,reportp,planp,out):
 r=load(reportp)
 inv.policy(r)
 for name,expected in r['repository_evidence_sha256'].items():
  disk=repo/'manifests'/name
  source=subprocess.check_output(['git','-C',str(repo),'show',inv.BASE+':manifests/'+name])
  need(sha(source)==expected and sha(disk.read_bytes())==expected,'FROZEN_REPO_FILE:'+name)
 manifest=load(repo/'manifests/m2dgr_trajectory_manifest_v1_split_freeze_v1.json')
 room=[a for a in manifest['records'] if a['trajectory_id']=='room_02']
 need(len(room)==1 and room[0]['split']=='train','SPLIT')
 holdout={a['trajectory_id'].lower() for a in manifest['records'] if a['split']=='confirmation_test'}
 need(len(holdout)==7,'HOLDOUT_COUNT')
 excluded={a['trajectory_id'].lower() for a in manifest['records'] if a['trajectory_id']!='room_02'}
 q=load(repo/'manifests/m2dgr_reference_quality_index_v1.json')
 line=[a for a in q['artifacts'] if a['trajectory_id']=='room_02']
 need(len(line)==1 and line[0]['bag_sha256']==inv.BAG and line[0]['reference_source']=='mocap','REF_FAMILY')
 need(r['room_02_reference_provenance']['raw_reference_sha256_provenance_only']==line[0]['raw_reference_sha256'],'REF_HASH')
 expected_streams={a['stream_id']:(a['frame_id'],a['clock_domain']) for a in room[0]['streams']}
 need(len(expected_streams)==4,'EXPECTED_STREAMS')
 for a in r['recorded_stream_clock_domains']:
  need((a['frame_id'],a['clock_domain'])==expected_streams[a['topic']] and a['physically_verified_offset_seconds'] is None,'CLOCK')
 roots={'recorded_m2dgr_train':train}
 roots.update({'workspace_'+n:workspace/n for n in ('calib','calibration','calibrations','groundtruth','ground_truth','reference','references','metadata')})
 roots.update({'repository_'+n:repo/n for n in ('calib','calibration','config','configs')})
 for a in r['candidate_files']:
  tag=a['scope'];rel=pathlib.PurePosixPath(a['relative_path'])
  need(tag in roots and not rel.is_absolute() and '..' not in rel.parts,'CANDIDATE_PATH')
  need(not inv.forbidden(rel,excluded),'NON_ROOM_TRAJECTORY_EXCLUSION')
  p=roots[tag].joinpath(*rel.parts)
  need(p.is_file() and not p.is_symlink(),'CANDIDATE_FILE')
  st=p.stat()
  need(st.st_size==a['size_bytes'] and a['scientific_calibration_verified'] is False,'CANDIDATE_METADATA')
  if a['sha256_small_file'] is not None:
   need(st.st_size<=inv.MAX_BYTES,'HASH_SIZE')
   fd=os.open(str(p),os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
   try:
    fstat=os.fstat(fd)
    need(stat.S_ISREG(fstat.st_mode) and fstat.st_size==st.st_size,'FILE_RACE')
    contents=os.read(fd,inv.MAX_BYTES+1)
    need(sha(contents)==a['sha256_small_file'],'ASSET_HASH')
   finally:os.close(fd)
 for x in r['explicit_room_02_reference_path_receipts']:
  rel=pathlib.PurePosixPath(x['path_relative_to_train'])
  need(not rel.is_absolute() and '..' not in rel.parts,'REFERENCE_PATH')
  p=train.joinpath(*rel.parts)
  need((p.is_file() and not p.is_symlink())==x['present_regular_file'],'REFERENCE_PRESENCE')
 need(len(r['candidate_files'])<=250 and len(r['qualification_requirements'])==9,'COUNTS')
 need(planp.is_file() and 'NOT QUALIFIED' in planp.read_text() and 'R41' in planp.read_text(),'PLAN')
 proof={
  'schema':'TRUST_ROBOT_R40_INDEPENDENT_ASSET_INVENTORY_VALIDATION_V1',
  'source_report_sha256':sha(reportp.read_bytes()),
  'plan_sha256':sha(planp.read_bytes()),
  'repository_manifest_git_snapshots_verified':len(inv.DOCUMENTS),
  'local_candidate_files_verified':len(r['candidate_files']),
  'room_02_reference_source':'mocap',
  'room_02_invalid_rotation_count':90,
  'qualification_requirements_unverified':len(inv.REQUIREMENTS),
  'raw_bag_reopened':False,'confirmation_test_accessed':False,
  'real_pose_factors_authorized':False
 }
 with out.open('x') as h:json.dump(proof,h,sort_keys=True,indent=2,allow_nan=False);h.write('\n')
 print('R40_INDEPENDENT_REPOSITORY_EVIDENCE=%d_COMMIT_MATCH'%len(inv.DOCUMENTS))
 print('R40_INDEPENDENT_LOCAL_ASSET_RECEIPTS=%d_VERIFIED'%len(r['candidate_files']))
 print('R40_INDEPENDENT_ROOM_02_REFERENCE_QUALITY=VERIFIED')
 print('R40_INDEPENDENT_VALIDATION=PASS')

if __name__=='__main__':verify(*(pathlib.Path(x) for x in sys.argv[1:7]))
