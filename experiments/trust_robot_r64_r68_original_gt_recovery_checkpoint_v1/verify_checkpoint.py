"""Reproducible SHA-pinned R64-R68 recovery archive. No GT bytes included."""
import ast, hashlib, json, os, pathlib, shutil, stat, sys

BASE='f3373e2d2c12a290661e03e0f6e59f66cdead4f9'
BRANCH='kios-isaacsim-v15-integration'
GTSHA='79d2c6d9132ce3cf87bb87445729302cd73709a59344a3dfacc5d7788937589d'
QUALITYSHA='8b27f25c02d04e838a88eb62980b1f2e94d0e1ed13defd0c6fa0f0b07c6bed49'
# Archive-relative path | off-Git experiments-relative source | original SHA256.
SOURCES='''
r64/result/r64d_historical_gt_staging_receipt_v1.json|trust_robot_r64d_existing_gt_staging_result_v1/r64d_historical_gt_staging_receipt_v1.json|46f3a22a315c442ed79aabb4f378ae4de5e6bb2f81586bf1a665fd097b9400ad
r65/dev/r65_independent.py|trust_robot_r65_gt_structure_audit_dev_v1/r65_independent.py|9fb624efdea9021af6c1021a149fdd288a399711f2098e8d71ec2d099855eb45
r65/dev/r65_primary.py|trust_robot_r65_gt_structure_audit_dev_v1/r65_primary.py|5e3ebedf9f183fcf65f247020e36ce5b663f5a6ec86d3cf428f9eaa36079be52
r65/dev/test_r65.py|trust_robot_r65_gt_structure_audit_dev_v1/test_r65.py|60a6f9f12a5359a35321723a7a52962114351ec90f91bae25734a70293cfb8fe
r65/result/r65_independent_validation_v1.json|trust_robot_r65_gt_structure_audit_result_v1/r65_independent_validation_v1.json|b8295319f06176e2991de9e7401132995dcd325b47bf04e0ba3767fd5d4b52fe
r65/result/r65_primary_profile_v1.json|trust_robot_r65_gt_structure_audit_result_v1/r65_primary_profile_v1.json|76dafd7ed30cbf4b504cabbdc2a0db738c67161eeb3d949f26a4ec2d69d20f7e
r66/dev/r66_independent.py|trust_robot_r66_original_rotation_rule_dev_v1/r66_independent.py|5281d5e1eda4efde80f16696339f8d9289a2ecaa093078eed5ef002d5ee3576b
r66/dev/r66_original.py|trust_robot_r66_original_rotation_rule_dev_v1/r66_original.py|511a3ced3d9071a477876071a13179fc97c04661defca03672d7583257578549
r66/dev/test_r66.py|trust_robot_r66_original_rotation_rule_dev_v1/test_r66.py|5095e28a0de2834136fec51abc4d329c600b3db8e67857abd78b1e37c0be4218
r66/result/r66_independent_validation_v1.json|trust_robot_r66_original_rotation_rule_result_v1/r66_independent_validation_v1.json|7d9dbeb6ffc4ec6fe4030b76f0cbae526f31040ec90a3b560d22fe3f16e307c2
r66/result/r66_original_rotation_rule_v1.json|trust_robot_r66_original_rotation_rule_result_v1/r66_original_rotation_rule_v1.json|efd35eb5ab6efaa6c25e048903935ae39b84abf7661ee095177944bba7740946
r67/dev/r67_independent.py|trust_robot_r67_historical_quality_replay_dev_v1/r67_independent.py|85662f0aa23ab748e1fe1856ced024ea2fd0a56002dff7b77ba6f7536e4e5a22
r67/dev/r67_rebuild.py|trust_robot_r67_historical_quality_replay_dev_v1/r67_rebuild.py|6831add317ccc2e1abf9f9360afaeb41ca3292574e500071b41e49bc9aba69b3
r67/dev/test_r67.py|trust_robot_r67_historical_quality_replay_dev_v1/test_r67.py|4643173ef7d007ae14c8a6bebf8e08c1c7c03f76d5380bc9c1b6a4bfbc8165a6
r67/result/r67_independent_validation_v1.json|trust_robot_r67_historical_quality_replay_result_v1/r67_independent_validation_v1.json|3c2ac2ec5bd6141484ac47e490caec4e109fef90af1e81beb6c4b86ef2b77b9c
r67/result/r67_rebuilt_room_02_reference_quality_v1.json|trust_robot_r67_historical_quality_replay_result_v1/r67_rebuilt_room_02_reference_quality_v1.json|8b27f25c02d04e838a88eb62980b1f2e94d0e1ed13defd0c6fa0f0b07c6bed49
r67/result/r67_replay_receipt_v1.json|trust_robot_r67_historical_quality_replay_result_v1/r67_replay_receipt_v1.json|7e87e7b7e7b6f242fc63fdd85bf46fe91fb25ee13c49f8968753ff45dfaa6b28
r68/dev/r68_independent.py|trust_robot_r68_physical_gap_reconciliation_dev_v1/r68_independent.py|e00b4516be589280883342ec657396547fdb42bfd57ca60235e592ea5b79e30b
r68/dev/r68_reconcile.py|trust_robot_r68_physical_gap_reconciliation_dev_v1/r68_reconcile.py|514057c43b348f86f909c86a99a3e752a7a5e65c528f3410e4a6af3098435393
r68/result/r68_independent_validation_v1.json|trust_robot_r68_physical_gap_reconciliation_result_v1/r68_independent_validation_v1.json|95d23240328e91557de28c4b38abce4257fb0ffe7ea0a3d1f7d0b68b9dbfb9f6
r68/result/r68_physical_gate_reconciliation_v1.json|trust_robot_r68_physical_gap_reconciliation_result_v1/r68_physical_gate_reconciliation_v1.json|304840f59df0c9bc16c40822bc169ec078692de043e7494b5164fd391e631f05
r68/result/r68_updated_author_physical_evidence_request_v1.md|trust_robot_r68_physical_gap_reconciliation_result_v1/r68_updated_author_physical_evidence_request_v1.md|cb515efcf80e29b1961bf87917b171ead80cf91fb4cd6c83900003d8fa3e44f2
'''
ROWS=[tuple(line.split('|')) for line in SOURCES.strip().splitlines()]
PINS={rel:sha for rel,src,sha in ROWS}

README=f'''# TRUST-ROBOT R64–R68 historical M2DGR GT recovery checkpoint

The original TRAIN `room_02.txt` was already stored in the original Verona M2DGR dataset. A checksum-identical 504403-byte copy was transferred Verona → Windows → KIOS, kept OUTSIDE Git at `/home/kios/TRUST_ROBOT_ALI/manual_official_gt_staging_v1/room_02_official_gt_candidate.txt`.
Historical GT SHA256: `{GTSHA}`. This is a match to our original dataset evidence, **not** an independent original-author checksum attestation.

R65: 3831 numeric eight-column records, 77.82016110420227 first-column span, no duplicate/decreasing values; 90 candidate quaternion deviations >0.01.
R66: original 0.001 quaternion norm rule and independent replay agree on 90 invalid rotations in 61 sample-index runs, 3741 structurally valid rotations, zero invalid translations.
R67: original Phase-2 reference-quality artifact rebuilt BYTE-FOR-BYTE, SHA256 `{QUALITYSHA}`.
R68: reconciled original frozen R43/R53 physical evidence requirements; corrected author request is a DRAFT, NOT SENT.

All 11 physical/scientific gates remain CLOSED. No independent physical GT timestamp/event/epoch mapping, mocap tracked body origin, mocap-to-LiDAR rigid transform, or required sensor calibration. No real pose factors, health training, ATE/RPE or test-data selection. `confirmation_test` remains sealed. No raw `.bag` or original `.txt` GT is in this archive. R61's historical `GT=ABSENT` describes its earlier staging state only; it is not current.

Verona original dataset path: `/mnt/hdd16T/ToqeerHomeBackup/toqeer/datasets/TRUST_ROBOT/M2DGR/`; Verona project: `~/toqeer/TRUST_ROBOT`; KIOS active Git checkout: `/home/kios/TRUST_ROBOT_ALI/github_checkout_v15`.

To verify all 22 frozen original off-Git source/report SHA pins and scientific semantics from a Git clone:
`python3 experiments/trust_robot_r64_r68_original_gt_recovery_checkpoint_v1/verify_checkpoint.py verify experiments/trust_robot_r64_r68_original_gt_recovery_checkpoint_v1`

The verifier does not require raw ground-truth or ROS bag bytes.
'''

def demand(b,msg):
    if not b: raise ValueError('R69_CHECKPOINT_DENIED:'+msg)
def digest(data): return hashlib.sha256(data).hexdigest()
def safe_bytes(path):
    s=path.lstat()
    demand(stat.S_ISREG(s.st_mode) and s.st_nlink==1 and 0<s.st_size<=1024*1024,'UNSAFE_FILE:'+str(path))
    return path.read_bytes()
def load(root,rel): return json.loads(safe_bytes(root/'evidence'/rel))

def science(root):
    r64=load(root,'r64/result/r64d_historical_gt_staging_receipt_v1.json')
    r65=load(root,'r65/result/r65_primary_profile_v1.json')
    v65=load(root,'r65/result/r65_independent_validation_v1.json')
    r66=load(root,'r66/result/r66_original_rotation_rule_v1.json')
    v66=load(root,'r66/result/r66_independent_validation_v1.json')
    r67=load(root,'r67/result/r67_replay_receipt_v1.json')
    v67=load(root,'r67/result/r67_independent_validation_v1.json')
    quality=load(root,'r67/result/r67_rebuilt_room_02_reference_quality_v1.json')
    r68=load(root,'r68/result/r68_physical_gate_reconciliation_v1.json')
    v68=load(root,'r68/result/r68_independent_validation_v1.json')
    draft=safe_bytes(root/'evidence/r68/result/r68_updated_author_physical_evidence_request_v1.md').decode('utf-8')
    demand(r64['schema']=='TRUST_ROBOT_R64D_HISTORICAL_GT_STAGING_V1' and r64['final_sha256']==GTSHA and r64['size_bytes']==504403,'R64')
    demand(r64['gt_bytes_available_locally'] is True and r64['scientific_gates_closed']==11,'R64_GATES')
    p=r65['current_profile']; q=p['eight_column_diagnostics_only']
    demand(p['numeric_row_count']==3831 and p['numeric_width_histogram']=={'8':3831} and q['candidate_last_four_deviation_gt_1e_2']==90,'R65')
    demand(v65['status']=='PASS' and r65['scientific_gates_closed']==11,'R65_SCIENCE')
    demand(r66['gt_sha256']==GTSHA and len(r66['original_audit']['invalid_rotation_sample_indices'])==90 and r66['invalid_run_count']==61,'R66')
    demand(v66['status']=='PASS' and r66['scientific_gates_closed']==11,'R66_SCIENCE')
    demand(r67['exact_historical_quality_reproduction'] is True and r67['reproduced_quality_artifact_sha256']==QUALITYSHA and r67['scientific_gates_closed']==11,'R67')
    demand(v67['status']=='PASS' and quality['rotation_validity']['invalid_count']==90 and quality['sample_count']==3831,'R67_SCIENCE')
    demand(r68['dataset_bytes_recovered_and_verified'] is True and r68['historical_quality_report_byte_reproduced'] is True and r68['historical_r43_closed_gate_count']==11 and r68['historical_r53_unfilled_sensor_receipts']==5,'R68')
    demand(v68['status']=='PASS' and r68['scientific_gates_closed']==11 and r68['physical_qualification_authorizations_opened']==0,'R68_SCIENCE')
    demand('DRAFT ONLY' in draft and 'NOT SENT' in draft,'AUTHOR_REQUEST_NOT_SENT')
    for record in (r64,r65,r66,r67,r68):
        for flag in ('real_pose_factors_authorized','health_training_authorized','ate_rpe_authorized'):
            if flag in record: demand(record[flag] is False,'SCIENCE:'+flag)
        demand(record['confirmation_test_accessed'] is False,'SEALED')
    for flag in ('mocap_to_lidar_transform_verified','reference_to_sensor_clock_mapping_verified','physical_sensor_calibration_verified'):
        demand(r68[flag] is False,'PHYSICAL:'+flag)
    demand(r68['original_gt_modified'] is False and r68['raw_bag_opened'] is False,'PRESERVATION')

def verify(root):
    demand(root.is_dir() and not root.is_symlink(),'ARCHIVE_ROOT')
    demand(len(ROWS)==22 and len(PINS)==22 and all(len(t)==3 and len(t[2])==64 for t in ROWS),'PIN_LIST')
    allfiles=set()
    for path in root.rglob('*'):
        demand(not path.is_symlink(),'SYMLINK')
        if path.is_file(): allfiles.add(path.relative_to(root).as_posix())
    expected={'README.md','checkpoint_manifest_v1.json','verify_checkpoint.py'}|{'evidence/'+r for r in PINS}
    demand(allfiles==expected,'INVENTORY')
    manifest=json.loads(safe_bytes(root/'checkpoint_manifest_v1.json'))
    demand(manifest['schema']=='TRUST_ROBOT_R64_R68_GT_RECOVERY_ARCHIVE_V1' and manifest['parent_commit']==BASE and manifest['branch']==BRANCH,'MANIFEST_IDENTITY')
    demand(manifest['source_pins']==PINS and manifest['source_count']==22,'MANIFEST_PINS')
    demand(manifest['raw_gt_bytes_archived'] is False and manifest['raw_rosbag_archived'] is False and manifest['confirmation_test_accessed'] is False,'DATA_LEAKAGE')
    demand(manifest['scientific_gates_closed']==11 and manifest['real_pose_factors_authorized'] is False and manifest['health_training_authorized'] is False and manifest['ate_rpe_authorized'] is False,'SCIENCE_MANIFEST')
    demand(manifest['original_gt_sha256']==GTSHA and manifest['historical_quality_artifact_sha256']==QUALITYSHA,'DATA_PINS')
    demand(safe_bytes(root/'README.md').decode('utf-8')==README,'README_IDENTITY')
    total=0
    for rel,sha in sorted(PINS.items()):
        b=safe_bytes(root/'evidence'/rel)
        demand(digest(b)==sha,'SOURCE_SHA:'+rel)
        total+=len(b)
        if rel.endswith('.py'):ast.parse(b,filename=rel)
        if rel.endswith('.json'):json.loads(b)
    demand(total==manifest['evidence_total_bytes'],'EVIDENCE_SIZE')
    science(root)
    print('R69_STANDALONE_ARCHIVE_VERIFIER=PASS')
    print('R69_SOURCE_FILES=22_EXACT_SHA256')
    print('R69_HISTORICAL_QUALITY_SHA256=EXACT')
    print('R69_SCIENTIFIC_GATES=11_CLOSED')

def build(experiments,root):
    demand(not root.exists() and not root.is_symlink(),'ARCHIVE_ALREADY_EXISTS')
    demand(experiments.is_dir() and not experiments.is_symlink(),'EXPERIMENT_ROOT')
    root.mkdir(mode=0o755)
    shutil.copyfile(pathlib.Path(__file__),root/'verify_checkpoint.py')
    (root/'verify_checkpoint.py').chmod(0o644)
    (root/'README.md').write_text(README,encoding='utf-8')
    (root/'README.md').chmod(0o644)
    total=0
    for rel,src,sha in ROWS:
        source=experiments/src
        b=safe_bytes(source)
        demand(digest(b)==sha,'ORIGINAL_SOURCE_SHA:'+src)
        target=root/'evidence'/rel
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write(b)
        target.chmod(0o644)
        total+=len(b)
    manifest={
        'schema':'TRUST_ROBOT_R64_R68_GT_RECOVERY_ARCHIVE_V1',
        'parent_commit':BASE,'branch':BRANCH,'source_pins':PINS,
        'source_count':len(PINS),'evidence_total_bytes':total,
        'original_gt_sha256':GTSHA,'original_gt_size_bytes':504403,
        'historical_quality_artifact_sha256':QUALITYSHA,
        'historical_gt_recovered_locally':True,
        'original_verona_dataset_path':'/mnt/hdd16T/ToqeerHomeBackup/toqeer/datasets/TRUST_ROBOT/M2DGR/',
        'original_gt_is_independently_author_checksum_verified':False,
        'physical_reference_clock_and_frame_verified':False,
        'scientific_gates_closed':11,
        'real_pose_factors_authorized':False,
        'health_training_authorized':False,'ate_rpe_authorized':False,
        'raw_gt_bytes_archived':False,'raw_rosbag_archived':False,
        'confirmation_test_accessed':False,
        'author_request_sent':False,
    }
    with (root/'checkpoint_manifest_v1.json').open('x') as f: json.dump(manifest,f,sort_keys=True,indent=2);f.write('\n')
    (root/'checkpoint_manifest_v1.json').chmod(0o644)
    verify(root)

if __name__=='__main__':
    if len(sys.argv)==4 and sys.argv[1]=='build':build(pathlib.Path(sys.argv[2]),pathlib.Path(sys.argv[3]))
    elif len(sys.argv)==3 and sys.argv[1]=='verify':verify(pathlib.Path(sys.argv[2]))
    else:raise SystemExit('Usage: verify_checkpoint.py verify ARCHIVE | build EXPERIMENTS ARCHIVE')
