"""Standalone, offline, commit-scoped R57/R57A replay checkpoint verifier."""
import ast,hashlib,json,pathlib,stat,subprocess
A=pathlib.Path(__file__).resolve().parent
R=A.parents[1]
def need(x,msg):
 if not x: raise RuntimeError('R58_STANDALONE_DENIED:'+msg)
def sha(p):
 need(p.is_file() and not p.is_symlink() and p.stat().st_nlink==1,'UNSAFE:'+str(p))
 return hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((A/'checkpoint_manifest_v1.json').read_text())
need(m['schema']=='TRUST_ROBOT_R57_R57A_REPLAY_CHECKPOINT_V1','SCHEMA')
need(m['parent_commit']=='58e23861811e51c5d00f00f5d22e5cb561c4b43a','BASE')
need(m['branch']=='kios-isaacsim-v15-integration','BRANCH')
need(m['r56_artifacts_byte_replayed']==39 and m['r57_tamper_controls_rejected']==2,'R57')
need(m['r57_original_launcher_failed'] is True and m['r57a_synthetic_negative_test_replays_passed']==6,'REPAIR')
need(m['ground_truth_acquired'] is False and m['scientific_gates_opened']==0,'SCIENCE')
for key in ('real_pose_factors_authorized','health_training_authorized','ate_rpe_authorized','raw_bag_archived','confirmation_test_accessed'):need(m[key] is False,'SCIENCE_'+key)
need(sha(R/'experiments/trust_robot_r51_r55f_evidence_checkpoint_v1/manifest.json')==m['r56_archive_manifest_sha256'],'R56_SHA')
need(sha(R/'manifests/m2dgr_trajectory_manifest_v1_split_freeze_v1.json')=='017a388ef1ce4ad30812669632a022ca37c084871bc949693fd9c0541014238f','SPLIT')
pins=m['files_sha256']
need(len(pins)==15,'FILE_COUNT')
actual=set()
for p in A.rglob('*'):
 need(not p.is_symlink(),'SYMLINK')
 if p.is_file(): actual.add(p.relative_to(A).as_posix())
need(actual==set(pins)|{'checkpoint_manifest_v1.json'},'EXACT_FILES')
for rel,h in pins.items():
 parts=pathlib.PurePosixPath(rel)
 need(not parts.is_absolute() and '..' not in parts.parts,'PATH')
 need(sha(A/rel)==h,'SHA:'+rel)
 if rel.endswith('.py'):ast.parse((A/rel).read_bytes(),filename=rel)
 if rel.endswith('.json'):json.loads((A/rel).read_text())
report=json.loads((A/'sources/r57a_success/r57a_replay_report_v1.json').read_text())
need(report['status']=='PASS' and report['original_failure_preserved'] is True,'REPORT')
need(report['patched_launcher_sha256']==sha(A/'sources/r57a_success/r57a_offline_test_launcher_fixed.py'),'PATCH')
old=(A/'sources/r57_failure/r57_offline_test_launcher.py').read_text()
new=(A/'sources/r57a_success/r57a_offline_test_launcher_fixed.py').read_text()
needle='sys.path.insert(0,str(target.parent));sys.argv=[str(target)]'
replacement='sys.path.insert(0,str(target.parent));sys.argv=[str(target),str(target.parent),str(pathlib.Path(sys.argv[2]).resolve()),str(target.parent.parent)]'
need(old.count(needle)==1 and new==old.replace(needle,replacement),'PATCH_SCOPE')
log=(A/'sources/r57_failure/r51_synthetic_negative_replay.txt').read_text()
need('IndexError: list index out of range' in log and 'test_r51.py' in log and 'sys.argv[1]' in log,'FAILURE_SIGNATURE')
orig=report['original_r57_evidence_sha256']
need(len(orig)==3,'R57_ORIGINAL_LIST')
for name in ('r57_replay.py','r57_offline_test_launcher.py','r51_synthetic_negative_replay.txt'):
 source_name='r51_synthetic_negative_replay.log' if name.endswith('.txt') else name
 matches=[x for x in orig if x.endswith('/'+source_name)]
 need(len(matches)==1 and orig[matches[0]]==sha(A/'sources/r57_failure'/name),'R57_FAILURE_SHA:'+name)
r56=json.loads((R/'experiments/trust_robot_r51_r55f_evidence_checkpoint_v1/manifest.json').read_text())
phases=report['tests_completed']
need(set(phases)=={'r51','r52','r53','r54','r55','r55f'},'PHASE_SET')
for phase,receipt in phases.items():
 p=A/'sources/r57a_success'/(phase+'_replay.txt')
 need(type(receipt['exit_code']) is int and receipt['exit_code']==0,'REPLAY_EXIT:'+phase)
 need(receipt['log_sha256']==sha(p) and receipt['log_bytes']==p.stat().st_size,'REPLAY_LOG:'+phase)
 matches=[x for x in r56['files'] if x.endswith('/test_'+phase+'.py')]
 need(len(matches)==1 and receipt['original_test_sha256']==r56['files'][matches[0]]['sha256'],'TEST_SHA:'+phase)
need(report['official_gt_status']=='NOT_ACQUIRED' and report['r43_eleven_gates']=='CLOSED','REPORT_SCIENCE')
path='experiments/trust_robot_r57_r57a_replay_checkpoint_v1/checkpoint_manifest_v1.json'
commit=subprocess.check_output(['git','-C',str(R),'rev-list','-1','HEAD','--',path],text=True).strip()
if commit:
 parent=subprocess.check_output(['git','-C',str(R),'rev-parse',commit+'^'],text=True).strip()
 need(parent==m['parent_commit'],'GIT_PARENT')
need(set(m['documentation_sha256'])=={'AGENTS.md','docs/TRUST_ROBOT_PROJECT_STATE.md','docs/audits/trust_robot/TRUST_ROBOT_KIOS_R51_R55F_EVIDENCE_V1.md'},'DOC_SCOPE')
for rel,expected in m['documentation_sha256'].items():
 blob=subprocess.check_output(['git','-C',str(R),'show',commit+':'+rel]) if commit else (R/rel).read_bytes()
 need(hashlib.sha256(blob).hexdigest()==expected,'DOC_SHA:'+rel)
print('R58_REPLAY_CHECKPOINT_STANDALONE=PASS')
print('R58_REPLAY_ARCHIVE_PINNED_FILES=15')
print('R58_ORIGINAL_FAILED_LAUNCHER=AUTHENTIC_PRESERVED')
print('R58_TARGETED_LAUNCHER_REPAIR=EXACT_PATCH_VERIFIED')
print('R58_R57A_PHASE_TEST_LOGS=6_VERIFIED')
print('R58_COMMIT_SCOPED_DOCUMENTATION=VERIFIED')
print('R58_GT=NOT_ACQUIRED SCIENCE_GATES=11_CLOSED')
