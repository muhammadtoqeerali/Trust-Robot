"""Independent, exact-source R101/R102 archive verifier."""
import hashlib,json,pathlib,stat,sys

SCHEMA='TRUST_ROBOT_R101_R102_PRIOR_COMPATIBILITY_CHECKPOINT_V1'
PARENT='10ee70fb423930fce30eff919f7a5cb735771f60'
BRANCH='kios-isaacsim-v15-integration'
PINS={
 'evidence/r101/dev/r101_prior_adapter.py':'cfff7ea529051ec253883d886db21b2460cde7261e8f2649c4c4432ae873c880',
 'evidence/r101/dev/test_r101.py':'ef96f38fd83b26d79d52f81535d600ba304e4c414e612691d5807a2775078a44',
 'evidence/r101/dev/r101_interface_contract_v1.md':'46bacfb94163822bd4e0f2697f5c29c334c5c63ce860b290d248cbf9e0a63f7a',
 'evidence/r101/result/r101_prior_adapter_report_v1.json':'e3d852ee5607c807d62ec4f811d83487060fac9baca21c8327abc2f1c01be186',
 'evidence/r101/result/r101_independent_validation_v1.json':'6f20e1ec0fdf282c474b8ca608ccd7e5c9de17bbb2cc8e7f3b4186b76097096d',
 'evidence/r102/dev/r102_compatibility.py':'16d66f46c5197b2d5a1f35eb6bd471461bbbfddfd32edd0804c815214bc2ed1b',
 'evidence/r102/dev/test_r102.py':'703390420e7921808505105afbf104fb5c33f306c53fdc684904149b434ce07e',
 'evidence/r102/dev/r102_compatibility_decision_v1.md':'fd68ca0899792d3bfcac5886f1cbbe9f7a5da2fedc3ca34b2c5db4aa978ac078',
 'evidence/r102/result/r102_compatibility_report_v1.json':'329f29bd40cd177e5a50907da144e39ed1f7e8bf2616ba94c40d214f3e440120',
 'evidence/r102/result/r102_independent_validation_v1.json':'0b7bcdee25a25239c04153cdf40c8923ab27c9a0365b28c96dd0d9328219bba0',
}
DOCS={
 'AGENTS.md','docs/TRUST_ROBOT_PROJECT_STATE.md',
 'docs/audits/trust_robot/TRUST_ROBOT_KIOS_R101_R102_BACKEND_COMPATIBILITY_CHECKPOINT_V1.md',
}
BLOCKERS=(
 'FRAME_NAMESPACE_MISMATCH','CLOCK_EPOCH_NOT_ASSOCIATED',
 'WINDOW_DURATION_MISMATCH','GAUGE_ANCHOR_MISMATCH',
 'PRIOR_RETAINED_DIMENSION_MISMATCH','PRIOR_NODE_IDENTITY_MISMATCH',
 'REGULARIZATION_POLICY_MISMATCH','FACTOR_LINEAGE_MAPPING_NOT_ESTABLISHED',
)
def need(ok,why):
    if not ok: raise ValueError('R103_CHECKPOINT_DENIED:'+why)
def sha(data): return hashlib.sha256(data).hexdigest()
def read(root,name): return json.loads((root/name).read_bytes())
def check(root):
    need(root.is_dir() and not root.is_symlink(),'ROOT')
    m=read(root,'checkpoint_manifest_v1.json')
    need(m.get('schema')==SCHEMA and m.get('parent_commit')==PARENT and m.get('branch')==BRANCH,'IDENTITY')
    need(m.get('source_sha256')==PINS and m.get('source_count')==10,'SOURCE_ALLOWLIST')
    meta=m.get('metadata_sha256')
    need(type(meta) is dict and set(meta)=={'README.md','verify_checkpoint.py'},'METADATA_ALLOWLIST')
    docs=m.get('documentation_sha256')
    need(type(docs) is dict and set(docs)==DOCS,'DOCS_ALLOWLIST')
    wanted=set(PINS)|set(meta)|{'checkpoint_manifest_v1.json'}
    dirs=set()
    for name in wanted:
        p=pathlib.PurePosixPath(name)
        need(not p.is_absolute() and '..' not in p.parts,'PATH')
        dirs.update('/'.join(p.parts[:i]) for i in range(1,len(p.parts)))
    observed={str(p.relative_to(root)) for p in root.rglob('*')}
    need(observed==wanted|dirs,'EXACT_TREE')
    for name in dirs:
        d=root/name
        need(d.is_dir() and not d.is_symlink(),'DIR:'+name)
    for name in wanted:
        p=root/name
        s=p.lstat()
        need(stat.S_ISREG(s.st_mode) and s.st_nlink==1 and 0<s.st_size<2_000_000,'REGULAR:'+name)
    forbidden=(b'/home/'+b'kios/',b'/mnt/'+b'hdd16T/',b'C:'+b'\\Users\\')
    for name,pin in {**PINS,**meta}.items():
        raw=(root/name).read_bytes()
        need(type(pin) is str and len(pin)==64 and sha(raw)==pin,'SHA:'+name)
        need(not any(fragment in raw for fragment in forbidden),'PRIVATE_PATH:'+name)
    a=read(root,'evidence/r101/result/r101_prior_adapter_report_v1.json')
    b=read(root,'evidence/r102/result/r102_compatibility_report_v1.json')
    va=read(root,'evidence/r101/result/r101_independent_validation_v1.json')
    vb=read(root,'evidence/r102/result/r102_independent_validation_v1.json')
    need(a.get('schema')=='TRUST_ROBOT_R101_SYNTHETIC_PRIOR_ADAPTER_V1','R101_SCHEMA')
    need(a.get('status')=='PASS_SYNTHETIC_SOFTWARE_ONLY','R101_STATUS')
    need(a.get('scenarios')==4 and a.get('converted_gaussian_prior_prefixes')==16 and a.get('independent_synthetic_segments')==5 and a.get('timestamp_gaps')==1,'R101_COUNTS')
    need(len(a.get('cases',{}))==4,'R101_CASES')
    prefixes=0
    for case in a['cases'].values():
        need(case.get('cross_gap_prior_reuse') is False,'R101_GAP')
        for seg in case['rows']:
            need(seg.get('fresh_synthetic_segment_gauge') is True and seg.get('prior_copied_across_gap') is False,'R101_SEGMENT')
            for p in seg['prefixes']:
                prefixes+=1
                need(p['information_relative_error']<1e-9 and p['gradient_relative_error']<1e-9 and p['max_energy_relative_error']<1e-7,'R101_NUMERICS')
                need(p['quarantine_node_id']>=100,'R101_QUARANTINE')
    need(prefixes==16,'R101_PREFIXES')
    need(b.get('schema')=='TRUST_ROBOT_R102_SYNTHETIC_BACKEND_COMPATIBILITY_V1','R102_SCHEMA')
    need(b.get('status')=='PASS_FAIL_CLOSED_COMPATIBILITY_AUDIT','R102_STATUS')
    need(b.get('shared_inertial_residual_function') is True and b.get('shared_15d_state_size') is True,'SHARED_MATH')
    need(b.get('compatibility_blocker_count')==8 and b.get('compatibility_blockers')==list(BLOCKERS),'BLOCKERS')
    source=b.get('source',{});target=b.get('target',{})
    need(source.get('window_duration_ns')==100_000_000 and target.get('window_duration_ns')==200_000_000,'DURATION')
    need(source.get('prior_dimension')==15 and target.get('prior_dimension')==30,'PRIOR_DIMENSIONS')
    need(source.get('retained_node_ids')==[100] and target.get('retained_node_ids')==[1,2],'PRIOR_NODE_IDS')
    need(target.get('actual_marginalizations')==3,'NONLINEAR_LINEAGE')
    for report in (a,b):
        need(report.get('scientific_gates_closed')==11,'GATES')
        for field in ('health_training_authorized','ate_rpe_authorized','confirmation_test_accessed','raw_gt_or_rosbags_opened'):
            need(report.get(field) is False,'DENIAL:'+field)
    for field in ('s6_nonlinear_node_binding_authorized','r95_gaussian_backend_merged_into_s6','recorded_sensor_factors_authorized','physical_clock_verified','physical_extrinsics_verified'):
        need(a.get(field) is False,'R101_DENIAL:'+field)
    for field in ('real_cross_backend_prior_binding_performed','r95_backend_merged_into_s6','real_sensor_factors_authorized','physical_clock_or_extrinsics_verified','source_trajectory_alignment_verified'):
        need(b.get(field) is False,'R102_DENIAL:'+field)
    need(va.get('schema')=='TRUST_ROBOT_R101_INDEPENDENT_VALIDATION_V1' and va.get('status')=='PASS' and va.get('regression_tests')==28,'R101_RECEIPT')
    need(vb.get('schema')=='TRUST_ROBOT_R102_INDEPENDENT_VALIDATION_V1' and vb.get('status')=='PASS' and vb.get('regression_tests')==27,'R102_RECEIPT')
    for receipt,phase,engine,tests,report,md in (
      (va,'r101','r101_prior_adapter.py','test_r101.py','r101_prior_adapter_report_v1.json','r101_interface_contract_v1.md'),
      (vb,'r102','r102_compatibility.py','test_r102.py','r102_compatibility_report_v1.json','r102_compatibility_decision_v1.md'),
    ):
        for key,name,place in (('engine_sha256',engine,'dev'),('tests_sha256',tests,'dev'),('report_sha256',report,'result')):
            need(receipt.get(key)==PINS[f'evidence/{phase}/{place}/{name}'],'RECEIPT_SHA:'+phase+key)
        key='interface_contract_sha256' if phase=='r101' else 'decision_sha256'
        need(receipt.get(key)==PINS[f'evidence/{phase}/dev/{md}'],'RECEIPT_DOC:'+phase)
        need(receipt.get('scientific_gates_closed')==11,'RECEIPT_GATES')
    need(vb.get('r101_report_sha256')==PINS['evidence/r101/result/r101_prior_adapter_report_v1.json'],'R101_R102_LINEAGE')
    need(va.get('s6_source_sha256')==m.get('s6_source_sha256'),'S6_LINEAGE')
    need(m.get('source_count')==10 and m.get('archived_regression_tests')==55 and m.get('r101_test_count')==28 and m.get('r102_test_count')==27 and m.get('scientific_gates_closed')==11,'MANIFEST_COUNTS')
    for field in ('real_sensor_factor_execution_authorized','health_training_authorized','ate_rpe_authorized','physical_clock_or_extrinsics_verified','confirmation_test_accessed','raw_gt_or_rosbags_archived','r95_backend_merged_into_s6','qualified_author_response_ingested'):
        need(m.get(field) is False,'MANIFEST_DENIAL:'+field)
    print('R103_STANDALONE_CHECKPOINT_VERIFIER=PASS')
    print('R103_SHA256_SOURCE_AND_METADATA=12_PASS')
    print('R103_R101_R102_LINEAGE=PASS')
    print('R103_COMPATIBILITY_BLOCKERS=8_FAIL_CLOSED')
    print('R103_SCIENTIFIC_GATES=11_CLOSED')
if __name__=='__main__':
    need(len(sys.argv)==3 and sys.argv[1]=='verify','ARGUMENTS')
    check(pathlib.Path(sys.argv[2]))
