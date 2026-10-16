"""L36-L40 immutable-artifact and version-correct documentation verifier."""
import ast
import hashlib
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parent
repo = root.parents[1]
BASE = '0b542e8644f3c4b98ed92c0f83a7c82a4635ae52'
PINS = {
 'code/l36_acquisition_boundary.py': 'c79a250bdfe4b6854de002b60bef6df3fff600214a140ec77d1c9391969d4376',
 'evidence/l36_interface_contract.json': 'ee8dfaa3a0f95813d29efa68f65a3222a39cce5e12cf855c4c3508791dcc05f9',
 'evidence/l36_falsification_report.json': '18ba0c5ee8644581987321a955133518481e86f5c702600b11cf2d9dc904ba96',
 'code/l37_runtime_builder.py': '1cef92c43172800988093de5468363b5fac922e45a759272bcbecda0026065f2',
 'code/l37_runtime_guard.py': 'b6bcabaf081bb1d6bf31b0ff907369bef841cf012d33b4ec407efd9bd6d94965',
 'code/l37_nonexecuted_candidate.py': '4384b085f79dff51af5dbbf8a4c4bf4cae6deffc906bfbcaf8a8ef00a7e05dec',
 'evidence/l37_integration_plan.json': '51aa9fd4b612af45ac53d049fe21184ad15123b8154b7d72a8c71f5692d0f466',
 'evidence/l37_validation.json': 'ecc7e2cee1c066b1dc39f85136efd850422901b08936cd892b13d981ba6ff926',
 'code/l38_registry.py': '86672d8f9dbd12d41f61b93c1ae883f30c67fbf24eb6dadaa36833e1d12c55e8',
 'code/l38_independent_verify.py': 'd8496ef8e6ae76126ade1c2916e98e4dbe4fa7f7e79a41ba659bbb9018daff85',
 'evidence/l38_challenge.json': '2a20c6b86f79472003a0187dc3d6d9fc520092743d8343aeb2412556c8f770db',
 'evidence/l38_admission.json': '2f8a0f3be28eb0b2b139f9f36836160cf05775917c313982b0f666e930588a61',
 'evidence/l38_seal.json': '4d380b175c62401d404169d1611f8c332203c53506b79474673e68a118771bdd',
 'evidence/l38_validation.json': 'd3ec936ccc7ebeb1aeb7d629d90b0767a8fc15d9ff6e772637a4c2c9ca7adba8',
 'code/l39_crash_recovery.py': 'e2353db5a37863d296b888e71a8271458b505585d685e7635b8132cb44ea9c98',
 'code/l39_independent_verify.py': 'a1d97220d9977727843ee8b5aa13afaecc6be6d81ee780750d0bc2a8242a87e9',
 'evidence/l39_recovery_matrix.json': 'c9c7afe88785c3e59b8e2954834973ca6478d424b4402a008d756fabb3762b1c',
 'evidence/l39_validation.json': '68b3c40d46c686d8c619959f9cbce8fca639e6eee3e0c97493a8a2ee772bcf8d',
 'code/l40_outbox.py': '1df54c21a92bbf48387b48e1b78a0b71ea0298767005df7e3f7548f307a99736',
 'code/l40_exercise.py': '4b7424ad462a76871041563ee6c5f4fdc45a4f1b6929edb1fc12dd5e815ce0ad',
 'code/l40_independent_verify.py': 'ba468339dde1e26cc713870e838542ff8ed171de39be8a34cd2945fd43de1ef1',
 'evidence/l40_outbox_validation.json': '5bf243322cac38204defd66402b20b771d547ef6c6027567f91fc283fab6f2cf',
 'evidence/l40_independent_validation.json': '2eaaa416f94b52bb9707f1001f1a94703ff26ebc154c421df73660cfdc831886',
}
DYNAMIC = {
 'README.md', 'evidence/l38_registry_snapshot.json',
 'evidence/l40_registry_snapshot.json', 'evidence/l40_challenge.json',
 'evidence/l40_admission.json', 'evidence/l40_seal.json',
}
DOCS = {
 'AGENTS.md', 'docs/TRUST_ROBOT_PROJECT_STATE.md',
 'docs/audits/trust_robot/TRUST_ROBOT_KIOS_L36_L40_ACQUISITION_WITNESS_V1.md',
}

def need(value, message):
 if not value: raise ValueError(message)

def sha(path):
 p = Path(path)
 need(p.is_file() and not p.is_symlink(), 'Missing/symlink: '+str(p))
 need(p.stat().st_nlink == 1 and p.stat().st_size <= 3_000_000, 'Unsafe size/link: '+str(p))
 return hashlib.sha256(p.read_bytes()).hexdigest()

def load(name):
 return json.loads((root / name).read_text(encoding='utf-8'))

m = load('checkpoint_manifest_v1.json')
need(m['schema'] == 'TRUST_ROBOT_KIOS_L36_L40_CHECKPOINT_V1', 'Schema')
need(m['parent_commit'] == BASE, 'Parent')
need(m['branch'] == 'kios-isaacsim-v15-integration', 'Branch')
need(m['pinned_sha256'] == PINS, 'Immutable hardcoded source pins')
need(set(m['files_sha256']) == set(PINS) | DYNAMIC, 'File inventory')
need(m['archive_content_bytes'] <= 8_000_000, 'Archive size')
actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
need(actual == set(m['files_sha256']) | {'checkpoint_manifest_v1.json','verify_checkpoint.py'}, 'Unexpected files')
for rel, expected in m['files_sha256'].items():
 need(not Path(rel).is_absolute() and '..' not in Path(rel).parts, 'Unsafe path')
 need(sha(root/rel) == expected, 'Bad hash: '+rel)
 if rel in PINS: need(expected == PINS[rel], 'Pin mismatch: '+rel)
 if rel.endswith('.py'): ast.parse((root/rel).read_text(encoding='utf-8'))
 if rel.endswith('.json'): load(rel)
need([len(m['phase_files'][str(n)]) for n in range(36,41)] == [3,5,7,4,9], 'Phase counts')
parts=[p for n in range(36,41) for p in m['phase_files'][str(n)]]
need(len(parts)==len(set(parts))==28 and set(parts)==set(m['files_sha256'])-{'README.md'}, 'Phase coverage')

# A project's mutable AGENTS.md and state doc must be verified AT THIS
# CHECKPOINT COMMIT, not incorrectly at whatever HEAD exists years later.
manifest_path = (root/'checkpoint_manifest_v1.json').relative_to(repo).as_posix()
committed = subprocess.check_output(['git','-C',str(repo),'rev-list','-1','HEAD','--',manifest_path],text=True).strip()
need(set(m['documentation_sha256']) == DOCS, 'Documentation allowlist')
for rel, expected in m['documentation_sha256'].items():
 if committed:
  data=subprocess.check_output(['git','-C',str(repo),'show',committed+':'+rel])
  actual_sha=hashlib.sha256(data).hexdigest()
 else:
  actual_sha=sha(repo/rel)
 need(actual_sha == expected, 'Historical document pin: '+rel)

r36=load('evidence/l36_falsification_report.json')
r37=load('evidence/l37_validation.json')
p37=load('evidence/l37_integration_plan.json')
r38=load('evidence/l38_validation.json')
r39=load('evidence/l39_recovery_matrix.json')
v39=load('evidence/l39_validation.json')
r40=load('evidence/l40_outbox_validation.json')
v40=load('evidence/l40_independent_validation.json')
s38=load('evidence/l38_registry_snapshot.json')
s40=load('evidence/l40_registry_snapshot.json')
need(r36['implementation_sha256']==PINS['code/l36_acquisition_boundary.py'], 'L36 implementation')
need(r36['interface_contract_sha256']==PINS['evidence/l36_interface_contract.json'], 'L36 contract')
need(r36['negative_controls_count']==46 and r36['simulator_launch_authorized'] is False, 'L36 cases')
for f, rel in [
 ('builder_source_sha256','code/l37_runtime_builder.py'),
 ('guard_source_sha256','code/l37_runtime_guard.py'),
 ('candidate_source_sha256','code/l37_nonexecuted_candidate.py'),
 ('plan_sha256','evidence/l37_integration_plan.json')]:
 need(r37[f]==PINS[rel], 'L37 binding: '+f)
need(r37['static_mutations_rejected_count']==12 and r37['runtime_preflight_denied'] is True and r37['runtime_seal_denied'] is True, 'L37 gates')
need(p37['live_simulator_launch_enabled'] is False and p37['scene_and_runtime_assets_staged'] is False, 'L37 launch')
candidate=(root/'code/l37_nonexecuted_candidate.py').read_text()
need(candidate.index('from l37_runtime_guard import preflight_gate') < candidate.index('from isaacsim import SimulationApp'), 'Pre-simulator hook')
need(candidate.index('from l37_runtime_guard import seal_after_capture') > candidate.index('    _l29_export('), 'Post-export hook')
need(r38['registry_source_sha256']==PINS['code/l38_registry.py'] and r38['verifier_source_sha256']==PINS['code/l38_independent_verify.py'], 'L38 source')
for field, rel in [('challenge_sha256','l38_challenge'),('admission_sha256','l38_admission'),('seal_sha256','l38_seal')]:
 need(r38[field]==sha(root/'evidence'/ (rel+'.json')), 'L38 receipts')
need(r38['adversarial_mutations_count']==20 and r38['final_registry_state']=='SEALED', 'L38 replay')
need(s38['database_sha256']==r38['registry_db_sha256'] and s38['state']=='SEALED', 'L38 snapshot')
need(all(s38[k]==r38[k] for k in ['challenge_sha256','admission_sha256','seal_sha256']), 'L38 snapshot linkage')
need(r39['implementation_sha256']==PINS['code/l39_crash_recovery.py'] and v39['verifier_source_sha256']==PINS['code/l39_independent_verify.py'], 'L39 source')
need(v39['assessment_report_sha256']==PINS['evidence/l39_recovery_matrix.json'], 'L39 report')
need(r39['case_count']==20 and r39['decision_counts']=={'VERIFIED_SEALED':1,'ISSUED_REVIEW_REQUIRED':1,'ADMITTED_REVIEW_REQUIRED':1,'QUARANTINED':17}, 'L39 cases')
need(r40['protocol_source_sha256']==PINS['code/l40_outbox.py'] and r40['orchestrator_source_sha256']==PINS['code/l40_exercise.py'] and v40['verifier_source_sha256']==PINS['code/l40_independent_verify.py'], 'L40 source')
need(v40['assessment_sha256']==PINS['evidence/l40_outbox_validation.json'], 'L40 report')
need(r40['recovery_count']==2 and r40['faults_rejected_count']==7 and r40['nonce_replay_rejected'] is True, 'L40 cases')
need(s40['database_sha256']==r40['primary_registry_sha256'] and s40['state']=='SEALED' and len(s40['outbox'])==3, 'L40 snapshot')
for n, name in enumerate(['challenge','admission','seal']):
 digest=sha(root/'evidence'/('l40_'+name+'.json'))
 need(digest==r40['primary_receipts_sha256'][name+'_v1.json'], 'L40 published receipt')
 row=s40['outbox'][n]
 need(row=={'stage':n,'digest':digest,'published':1}, 'L40 outbox row')
need(m['l38_database_sha256']==s38['database_sha256'] and m['l40_database_sha256']==s40['database_sha256'], 'DB archive binding')
for k in ('new_sensor_acquisitions','pose_factors_authorized','health_labels_generated'):
 need(m[k]==0, 'No science promotion: '+k)
for k in ('live_simulator_launch_authorized','physical_sync_verified','independent_source_authenticity_verified','hardware_attestation_verified','real_power_loss_durability_verified','raw_sqlite_databases_committed','raw_sensor_recordings_committed','frozen_frontend_modified'):
 need(m[k] is False, 'False science flag: '+k)
for p in root.rglob('*'):
 need(not p.is_symlink(), 'Archived symlink')
 if p.is_file():
  need(p.suffix.lower() not in {'.sqlite','.db','.npy','.npz','.usd','.usda','.usdc','.bin','.so','.log','.pt','.pth'}, 'Unwanted binary')
print('L36_L40_CHECKPOINT_INTEGRITY=PASS')
print('L36_L40_ALL_PINNED_HASHES=VERIFIED')
print('L36_L40_VERSIONED_DOCUMENTATION=VERIFIED')
print('L38_L40_REGISTRY_SNAPSHOTS=VERIFIED')
print('SCIENTIFIC_POSE_FACTORS=0')
