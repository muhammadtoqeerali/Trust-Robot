"""R79 standalone file-integrity, provenance and fail-closed verification."""
import hashlib
import json
import pathlib
import stat
import sys

SCHEMA='TRUST_ROBOT_R76_R78_PHYSICAL_INTAKE_RUNTIME_CHECKPOINT_V1'
PARENT='c1f59bb5e38bdfece14798031c0d911441b28de8'

def require(ok, reason):
    if not ok:
        raise ValueError('R79_CHECKPOINT_DENIED:'+reason)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verify(root):
    require(root.is_dir() and not root.is_symlink(),'ARCHIVE_ROOT')
    mp=root/'checkpoint_manifest_v1.json'
    m=json.loads(mp.read_text('utf-8'))
    require(m.get('schema')==SCHEMA,'SCHEMA')
    require(m.get('parent_commit')==PARENT,'PARENT')
    require(m.get('branch')=='kios-isaacsim-v15-integration','BRANCH')
    sources=m.get('source_sha256')
    meta=m.get('metadata_sha256')
    require(type(sources) is dict and len(sources)==15,'SOURCE_COUNT')
    require(type(meta) is dict and set(meta)=={'README.md','verify_checkpoint.py'},'META_FIELDS')
    expected=set(sources)|set(meta)|{'checkpoint_manifest_v1.json'}
    actual={str(p.relative_to(root)) for p in root.rglob('*')}
    dirs=set()
    for rel in expected:
        parts=pathlib.PurePosixPath(rel).parts
        for idx in range(1,len(parts)):
            dirs.add('/'.join(parts[:idx]))
    require(actual==expected|dirs,'FILE_AND_DIRECTORY_ALLOWLIST')
    require(len(expected)==18,'EXACT_18_FILES')
    for rel in expected:
        p=root/rel
        s=p.lstat()
        require(stat.S_ISREG(s.st_mode) and s.st_nlink==1 and 0<s.st_size<=1048576,'FILE_TYPE:'+rel)
    for rel,pin in {**sources,**meta}.items():
        require(type(pin) is str and len(pin)==64 and sha(root/rel)==pin,'SOURCE_SHA:'+rel)
    require(m.get('scientific_gates_closed')==11,'GATES')
    require(m.get('r43_historical_unfilled')==11 and m.get('r53_historical_unfilled')==5,'HISTORICAL_RECEIPTS')
    for field in ('original_gt_archived','rosbags_archived','private_verona_reports_archived',
                  'physical_frame_qualified','physical_clock_qualified','real_pose_factors_authorized',
                  'health_training_authorized','ate_rpe_authorized','confirmation_test_accessed',
                  'author_request_sent'):
        require(m.get(field) is False,'UNAUTHORIZED_FLAG:'+field)
    def obj(rel): return json.loads((root/rel).read_text('utf-8'))
    r76=obj('evidence/r76/result/r76_source_intake_contract_v1.json')
    r76v=obj('evidence/r76/result/r76_independent_validation_v1.json')
    r77=obj('evidence/r77/result/r77_intake_sensor_factor_boundary_v1.json')
    r77v=obj('evidence/r77/result/r77_independent_validation_v1.json')
    r78=obj('evidence/r78/result/r78_runtime_boundary_decision_v1.json')
    r78v=obj('evidence/r78/result/r78_independent_validation_v1.json')
    require(r76.get('schema')=='TRUST_ROBOT_R76_PHYSICAL_SOURCE_INTAKE_CONTRACT_V1','R76_SCHEMA')
    require(r77.get('schema')=='TRUST_ROBOT_R77_INTAKE_SENSOR_FACTOR_GATE_BRIDGE_V1','R77_SCHEMA')
    require(r78.get('schema')=='TRUST_ROBOT_R78_RECORDED_FACTOR_RUNTIME_BOUNDARY_V1','R78_SCHEMA')
    require(len(r76.get('historical_r43_gates',{}))==11 and len(r76.get('historical_r53_receipts',{}))==5,'R76_GATES')
    require(r76.get('scientific_gates_closed')==11 and r76.get('independent_new_sources_qualified')==0 and r76.get('new_execution_authorizations')==0,'R76_DENIAL')
    require(r76.get('original_room_02_gt_recovered_in_later_phase') is True,'GT_RECOVERY_HISTORY')
    require(r76v.get('status')=='PASS' and r76v.get('contract_sha256')==sha(root/'evidence/r76/result/r76_source_intake_contract_v1.json'),'R76_RECEIPT')
    require(r77.get('status')=='PASS_SOFTWARE_ONLY' and r77.get('scientific_gates_closed')==11,'R77_STATUS')
    require(r77.get('historical_gates_checked')==11 and r77.get('historical_timing_receipts_checked')==5,'R77_COUNTS')
    require(r77.get('m2dgr_sensor_admission_gate_rejected') is True and r77.get('multimodal_recorded_factor_gate_rejected') is True,'R77_SENSOR_GATES')
    require(r77.get('r76_contract_sha256')==sha(root/'evidence/r76/result/r76_source_intake_contract_v1.json'),'R76_R77_LINEAGE')
    require(r77.get('r76_independent_validation_sha256')==sha(root/'evidence/r76/result/r76_independent_validation_v1.json'),'R76_R77_VALIDATION_LINEAGE')
    require(r77v.get('status')=='PASS' and r77v.get('primary_result_sha256')==sha(root/'evidence/r77/result/r77_intake_sensor_factor_boundary_v1.json'),'R77_RECEIPT')
    require(r78.get('status')=='PASS_SOFTWARE_ONLY' and r78.get('scientific_gates_closed')==11,'R78_STATUS')
    require(r78.get('candidate_shapes_tested')==11 and r78.get('apparently_filled_author_like_cases_denied')==11,'R78_CANDIDATE_DENIAL')
    require(r78.get('existing_sensor_factor_gates_tested')==2 and r78.get('physically_qualified_sources')==0 and r78.get('runtime_authorizations')==0,'R78_EXECUTION_DENIAL')
    for name,path in {
        'r76_intake.py':'evidence/r76/dev/r76_intake.py',
        'r77_bridge.py':'evidence/r77/dev/r77_bridge.py'
    }.items():
        require(r78.get('source_code_sha256',{}).get(name)==sha(root/path),'R78_SOURCE_LINEAGE:'+name)
    for name,path in {
        'r76_source_intake_contract_v1.json':'evidence/r76/result/r76_source_intake_contract_v1.json',
        'r76_independent_validation_v1.json':'evidence/r76/result/r76_independent_validation_v1.json',
        'r77_intake_sensor_factor_boundary_v1.json':'evidence/r77/result/r77_intake_sensor_factor_boundary_v1.json',
        'r77_independent_validation_v1.json':'evidence/r77/result/r77_independent_validation_v1.json'
    }.items():
        require(r78.get('prior_private_report_sha256',{}).get(name)==sha(root/path),'R78_REPORT_LINEAGE:'+name)
    require(r78v.get('status')=='PASS' and r78v.get('primary_sha256')==sha(root/'evidence/r78/result/r78_runtime_boundary_decision_v1.json'),'R78_RECEIPT')
    for document in ('evidence/r76/result/r76_author_physical_evidence_request_DRAFT_NOT_SENT.md',
                     'evidence/r76/result/r76_source_intake_contract_v1.json',
                     'evidence/r77/result/r77_intake_sensor_factor_boundary_v1.json',
                     'evidence/r78/result/r78_runtime_boundary_decision_v1.json',
                     'README.md'):
        s=(root/document).read_text('utf-8')
        for term in ('/home/kios/','/mnt/hdd16T/','C:\\Users\\'):
            require(term not in s,'PRIVATE_PATH:'+document)
    require('NOT SENT' in (root/'evidence/r76/result/r76_author_physical_evidence_request_DRAFT_NOT_SENT.md').read_text('utf-8'),'AUTHOR_DRAFT_STATUS')
    for report in (r76,r77,r78):
        require(report.get('scientific_gates_closed')==11,'REPORT_GATES')
        for field in ('real_pose_factors_authorized','health_training_authorized','ate_rpe_authorized','confirmation_test_accessed'):
            require(report.get(field) is False,'REPORT_DENIAL:'+field)
    print('R79_STANDALONE_CHECKPOINT_VERIFIER=PASS')
    print('R79_SOURCE_FILES=15_SHA256_EXACT')
    print('R79_CROSS_PHASE_R76_R78_LINEAGE=PASS')
    print('R79_SCIENTIFIC_GATES=11_CLOSED')

if __name__=='__main__':
    require(len(sys.argv)==3 and sys.argv[1]=='verify','ARGUMENTS')
    verify(pathlib.Path(sys.argv[2]))
