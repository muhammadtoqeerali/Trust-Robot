"""R58 one-time evidence copier and SHA manifest builder (KIOS/off-Git sources)."""
import hashlib, json, os, pathlib, re, stat, sys
R,E,A=map(pathlib.Path,sys.argv[1:4])
R56=R/'experiments/trust_robot_r51_r55f_evidence_checkpoint_v1'
R56_SHA='37baa2af905a3bb8dcac1a987a602923e8e847e9d39c2aa254598d29f31ddd0f'
EXPECTED={
 'r57a_success/r57a_offline_test_launcher_fixed.py':'ae2e7c09d8c5fdbd716cf5a73792d740575fdfca03fe39b47204fe40ba6d8c20',
 'r57a_success/r57a_resume_tests.py':'5953a0ffaec5751abcb44b30c650ae9091ca27be236882e6a7d1f4ac1da0c89c',
 'r57a_success/r57a_replay_report_v1.json':'9d67f3a133867698a2a6570b557e369d435103b60a9a30a2ed9ddafe4dca8809',
 'r57a_success/r51_replay.txt':'6091d0481d64842898f42d90368b16cd4ea4efac70c0206fa6bfdc3dd1f87f6c',
 'r57a_success/r52_replay.txt':'a4388a3099a36e4090d6afd547122307a0430660d6e589b9a1427ad5510c059b',
 'r57a_success/r53_replay.txt':'67c56afb2c278e810d4252ee68df0f9fc3d2c48a0226040b84b5fe1d8a8c1028',
 'r57a_success/r54_replay.txt':'a5d984cef2d5e8de37aa71ccd9c90da159c4be3e2e07b277cbd1266ffc06d525',
 'r57a_success/r55_replay.txt':'f1002655cb96d91cd3952a73614a99016240c8df9fd063a4c812c2c82c9d8922',
 'r57a_success/r55f_replay.txt':'2169d79117bdf56c7df9b8975147244a0f7993deac9a7003c1d21575e4b85b79'
}
OLD_DEV=E/'trust_robot_r57_checkpoint_independent_replay_dev_v1'
OLD_OUT=E/'trust_robot_r57_checkpoint_independent_replay_result_v1'
NEW_DEV=E/'trust_robot_r57a_argument_forwarding_repair_dev_v1'
NEW_OUT=E/'trust_robot_r57a_argument_forwarding_repair_result_v1'
SOURCES={
 'r57_failure/r57_replay.py':OLD_DEV/'r57_replay.py',
 'r57_failure/r57_offline_test_launcher.py':OLD_OUT/'r57_offline_test_launcher.py',
 'r57_failure/r51_synthetic_negative_replay.txt':OLD_OUT/'test_logs/r51_synthetic_negative_replay.log',
 'r57a_success/r57a_resume_tests.py':NEW_DEV/'r57a_resume_tests.py',
 'r57a_success/r57a_offline_test_launcher_fixed.py':NEW_DEV/'r57a_offline_test_launcher_fixed.py',
 'r57a_success/r57a_replay_report_v1.json':NEW_OUT/'r57a_replay_report_v1.json',
 **{'r57a_success/'+p+'_replay.txt':NEW_OUT/('test_logs/'+p+'_replay.log') for p in ('r51','r52','r53','r54','r55','r55f')}
}
SECRETS=re.compile(rb'(?i)(authorization\s*:\s*bearer\s+\S+|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?:access_token|refresh_token|client_secret)\s*[=:]\s*[\'\"]?[A-Za-z0-9._-]{12,})')
def need(c,msg):
 if not c: raise ValueError('R58_BUILD_DENIED:'+msg)
def sha(data): return hashlib.sha256(data).hexdigest()
def read_safe(p):
 first=p.lstat()
 need(stat.S_ISREG(first.st_mode) and first.st_nlink==1 and 0<first.st_size<1048576,'UNSAFE_SOURCE:'+str(p))
 fd=os.open(str(p),os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
 with os.fdopen(fd,'rb') as f:
  during=os.fstat(f.fileno()); data=f.read(1048577); after=os.fstat(f.fileno())
 last=p.lstat()
 identity=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
 need(identity(first)==identity(during)==identity(after)==identity(last) and len(data)==first.st_size,'MUTATED_SOURCE:'+str(p))
 need(b'\x00' not in data and not SECRETS.search(data),'BINARY_OR_PRIVATE:'+str(p))
 data.decode('utf-8')
 return data
need(sha(read_safe(R56/'manifest.json'))==R56_SHA,'R56_MANIFEST_SHA')
need(set(SOURCES)==set(EXPECTED)|{'r57_failure/r57_replay.py','r57_failure/r57_offline_test_launcher.py','r57_failure/r51_synthetic_negative_replay.txt'},'SOURCE_SET')
for rel,p in sorted(SOURCES.items()):
 data=read_safe(p)
 if rel in EXPECTED: need(sha(data)==EXPECTED[rel],'R57A_SOURCE_SHA:'+rel)
 target=A/'sources'/rel
 target.parent.mkdir(parents=True,exist_ok=True)
 if target.exists():
  need(read_safe(target)==data,'PARTIAL_COPY_MISMATCH:'+rel)
 else:
  with target.open('xb') as f: f.write(data)
 need(read_safe(target)==data,'COPY_MISMATCH:'+rel)
old=(A/'sources/r57_failure/r57_offline_test_launcher.py').read_text()
fixed=(A/'sources/r57a_success/r57a_offline_test_launcher_fixed.py').read_text()
needle='sys.path.insert(0,str(target.parent));sys.argv=[str(target)]'
replacement='sys.path.insert(0,str(target.parent));sys.argv=[str(target),str(target.parent),str(pathlib.Path(sys.argv[2]).resolve()),str(target.parent.parent)]'
need(old.count(needle)==1 and fixed==old.replace(needle,replacement),'ONLY_ARGV_PATCH')
failure=(A/'sources/r57_failure/r51_synthetic_negative_replay.txt').read_text()
need('IndexError: list index out of range' in failure and 'test_r51.py' in failure and 'sys.argv[1]' in failure,'ORIGINAL_FAILURE')
report=json.loads((A/'sources/r57a_success/r57a_replay_report_v1.json').read_text())
need(report.get('status')=='PASS' and report.get('original_failure_preserved') is True,'REPAIR_STATUS')
need(report.get('patched_launcher_sha256')==EXPECTED['r57a_success/r57a_offline_test_launcher_fixed.py'],'PATCH_SHA')
orig=report.get('original_r57_evidence_sha256')
need(isinstance(orig,dict) and len(orig)==3,'ORIGINAL_PROVENANCE')
for rel,p in SOURCES.items():
 if not rel.startswith('r57_failure/'): continue
 need(orig.get(str(p))==sha(read_safe(A/'sources'/rel)),'R57_ORIGINAL_PROVENANCE:'+rel)
phase=report.get('tests_completed')
need(isinstance(phase,dict) and set(phase)=={'r51','r52','r53','r54','r55','r55f'},'PHASE_SET')
r56=json.loads((R56/'manifest.json').read_text())
for key,v in phase.items():
 rel='r57a_success/'+key+'_replay.txt'
 need(type(v.get('exit_code')) is int and v['exit_code']==0,'TEST_RC:'+key)
 need(v.get('log_sha256')==EXPECTED[rel] and v.get('log_bytes')==(A/'sources'/rel).stat().st_size,'TEST_LOG:'+key)
 matches=[x for x in r56['files'] if x.endswith('/test_'+key+'.py')]
 need(len(matches)==1 and v.get('original_test_sha256')==r56['files'][matches[0]]['sha256'],'TEST_SOURCE:'+key)
for prop,expected in [('official_gt_status','NOT_ACQUIRED'),('r43_eleven_gates','CLOSED'),('real_pose_factors_health_ate_rpe','DENIED')]: need(report.get(prop)==expected,'SCIENCE:'+prop)
for prop in ['raw_bag_opened_by_repair','confirmation_test_accessed_by_repair','git_modified_by_repair']: need(report.get(prop) is False,'SCOPE:'+prop)
files={}
for p in sorted(A.rglob('*')):
 if p.is_dir(): need(not p.is_symlink(),'DIR_SYMLINK');continue
 relative=p.relative_to(A).as_posix()
 need(relative!='checkpoint_manifest_v1.json','MANIFEST_EXISTS')
 need(p.suffix in {'.py','.txt','.json','.md'},'BAD_SUFFIX:'+relative)
 files[relative]=sha(read_safe(p))
need(len(files)==15 and set(files)==set('sources/'+k for k in SOURCES)|{'README.md','build_checkpoint.py','verify_checkpoint.py'},'ARCHIVE_FILE_LIST')
docs={}
for rel in ('AGENTS.md','docs/TRUST_ROBOT_PROJECT_STATE.md','docs/audits/trust_robot/TRUST_ROBOT_KIOS_R51_R55F_EVIDENCE_V1.md'):
 docs[rel]=sha(read_safe(R/rel))
m={
 'schema':'TRUST_ROBOT_R57_R57A_REPLAY_CHECKPOINT_V1',
 'parent_commit':'58e23861811e51c5d00f00f5d22e5cb561c4b43a',
 'branch':'kios-isaacsim-v15-integration',
 'r56_archive_manifest_sha256':R56_SHA,
 'r56_artifacts_byte_replayed':39,
 'r57_tamper_controls_rejected':2,
 'r57_original_launcher_failed':True,
 'r57a_synthetic_negative_test_replays_passed':6,
 'ground_truth_acquired':False,
 'scientific_gates_opened':0,
 'real_pose_factors_authorized':False,
 'health_training_authorized':False,
 'ate_rpe_authorized':False,
 'raw_bag_archived':False,
 'confirmation_test_accessed':False,
 'files_sha256':files,
 'documentation_sha256':docs,
}
with (A/'checkpoint_manifest_v1.json').open('x',encoding='utf-8') as f:
 json.dump(m,f,indent=2,sort_keys=True);f.write('\n')
print('R58_R57_R57A_SOURCE_ARTIFACTS=12_VERIFIED')
print('R58_REPLAY_LOGS=6_HASH_PINNED')
print('R58_ORIGINAL_LAUNCHER_FAILURE_AND_EXACT_REPAIR=PRESERVED')
print('R58_R57_R57A_ARCHIVE_FILES=16')
