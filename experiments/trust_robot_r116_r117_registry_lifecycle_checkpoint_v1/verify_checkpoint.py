"""R118: standalone SHA-pinned R116/R117 evidence verifier."""

import hashlib
import json
import pathlib
import stat
import sys

SCHEMA='TRUST_ROBOT_R116_R117_REGISTRY_LIFECYCLE_CHECKPOINT_V1'
BASE='b95302ba3f385a6b39b6b8511bec30e008445b1d'
BRANCH='kios-isaacsim-v15-integration'

S6_SHA='a1c9d0b4b9219d1e1b370e5ab5f42fcb25ac53f1b77f005cb42b3497b90bfc9a'

PINS={
    'evidence/r116/dev/r116_lifecycle.py':
        '062b00f992d3543611c0cc395ed7b1f102c57eab62315cf2cc713871122ea520',
    'evidence/r116/dev/test_r116.py':
        '8115800b821977460db10c8b3d6c4d5527ca7947c35718ca36a99a4228fdd293',
    'evidence/r116/dev/r116_lifecycle_contract_v1.md':
        '6138352528feefdf33091a95125d1ab30537766c97aeaa87f669113693877a03',
    'evidence/r116/result/r116_session_lifecycle_v1.json':
        '7ecf4dde3b8cf60584a8dfb19fb968c25e51ab27696a178ab9b6430f7e75e8f1',
    'evidence/r116/result/r116_independent_validation_v1.json':
        '7e65c32839ab8e9fa170880a9122517863d20f3a50e6e0eb0b87d2039a437ab0',

    'evidence/r117/dev/r117_registry.py':
        'f9809330f3bdeec3f2b8f7fd86890edbd0428f1dbf9d2c0c3a5348e899766e98',
    'evidence/r117/dev/test_r117.py':
        '463bc7462817e8299616de7800819bf7ad845178fc6acbc3f9143cfbbd2fe84a',
    'evidence/r117/dev/r117_registry_contract_v1.md':
        '683bad092ab199a8b8ac31ddad4250ea7a692c97018e9a34dda40f88953dbf1b',
    'evidence/r117/result/r117_registry_hardening_v1.json':
        '7a52188672767654bf290b35e17122301dc6f32492b06ca310ab3a8f4b64fd98',
    'evidence/r117/result/r117_independent_validation_v1.json':
        '7d555e8255a9d8ab6ceb7aabb05f80ec87e6386011293d2910b42ff5ab67fbfe',
}

DOCS={
    'AGENTS.md',
    'docs/TRUST_ROBOT_PROJECT_STATE.md',
    'docs/audits/trust_robot/TRUST_ROBOT_KIOS_R116_R117_REGISTRY_LIFECYCLE_CHECKPOINT_V1.md',
}

REPORT_DENIALS=(
    'r95_backend_imported',
    'real_sensor_factors_authorized',
    'physical_clock_or_extrinsics_verified',
    'health_training_authorized',
    'ate_rpe_authorized',
    'confirmation_test_accessed',
    'raw_gt_or_rosbags_opened',
)

MANIFEST_DENIALS=(
    'real_sensor_factor_execution_authorized',
    'r95_backend_merged_into_s6',
    'hardware_streaming_verified',
    'actual_concurrent_thread_safety_verified',
    'durable_audit_log_verified',
    'authenticated_audit_log_verified',
    'physical_memory_reclamation_verified',
    'physical_resource_deadlines_verified',
    'health_training_authorized',
    'ate_rpe_authorized',
    'confirmation_test_accessed',
    'raw_gt_or_rosbags_archived',
    'qualified_author_reply_ingested',
)

def need(ok,reason):
    if not ok:
        raise ValueError('R118_CHECKPOINT_DENIED:'+reason)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def load(root,name):
    return json.loads((root/name).read_bytes())

def verify(root):
    need(
        root.is_dir() and not root.is_symlink(),
        'ROOT'
    )

    m=load(root,'checkpoint_manifest_v1.json')

    need(m.get('schema')==SCHEMA,'SCHEMA')
    need(m.get('parent_commit')==BASE,'PARENT')
    need(m.get('branch')==BRANCH,'BRANCH')

    need(
        m.get('source_count')==10
        and m.get('source_sha256')==PINS,
        'SOURCE_PINS'
    )

    metadata=m.get('metadata_sha256')

    need(
        type(metadata) is dict
        and set(metadata)=={
            'README.md','verify_checkpoint.py'
        },
        'METADATA_PINS'
    )

    docs=m.get('documentation_sha256')

    need(
        type(docs) is dict
        and set(docs)==DOCS,
        'DOCUMENTATION_PINS'
    )

    expected=set(PINS)|set(metadata)|{
        'checkpoint_manifest_v1.json'
    }

    dirs=set()

    for name in expected:
        path=pathlib.PurePosixPath(name)

        need(
            not path.is_absolute()
            and '..' not in path.parts,
            'UNSAFE_PATH'
        )

        for i in range(1,len(path.parts)):
            dirs.add('/'.join(path.parts[:i]))

    found={
        p.relative_to(root).as_posix()
        for p in root.rglob('*')
    }

    need(
        found==expected|dirs,
        'EXACT_ARCHIVE_TREE'
    )

    for name in dirs:
        p=root/name
        need(
            p.is_dir() and not p.is_symlink(),
            'DIRECTORY:'+name
        )

    for name in expected:
        p=root/name
        st=p.lstat()

        need(
            stat.S_ISREG(st.st_mode)
            and st.st_nlink==1
            and 0<st.st_size<2_000_000,
            'REGULAR_FILE:'+name
        )

    # Keep these signatures split to avoid a false
    # match against this verifier's own source code.
    forbidden=(
        b'/home/'+b'kios/',
        b'/mnt/'+b'hdd16T/',
        b'C:'+b'\\Users\\',
    )

    for name,pin in {**PINS,**metadata}.items():
        raw=(root/name).read_bytes()

        need(
            type(pin) is str
            and len(pin)==64
            and sha(raw)==pin,
            'SOURCE_SHA:'+name
        )

        need(
            not any(part in raw for part in forbidden),
            'PRIVATE_PATH:'+name
        )

    a=load(
        root,
        'evidence/r116/result/r116_session_lifecycle_v1.json'
    )
    b=load(
        root,
        'evidence/r117/result/r117_registry_hardening_v1.json'
    )
    va=load(
        root,
        'evidence/r116/result/r116_independent_validation_v1.json'
    )
    vb=load(
        root,
        'evidence/r117/result/r117_independent_validation_v1.json'
    )

    need(
        a.get('schema')==
        'TRUST_ROBOT_R116_SYNTHETIC_SESSION_LIFECYCLE_V1',
        'R116_SCHEMA'
    )
    need(
        b.get('schema')==
        'TRUST_ROBOT_R117_SYNTHETIC_REGISTRY_HARDENING_V1',
        'R117_SCHEMA'
    )

    need(
        a.get('status')==
            'PASS_SYNTHETIC_SESSION_LIFECYCLE_SOFTWARE_ONLY'
        and b.get('status')==
            'PASS_SYNTHETIC_REGISTRY_HARDENING_SOFTWARE_ONLY',
        'REPORT_STATUS'
    )

    need(
        a.get('healthy_sessions')==12
        and a.get('healthy_committed_operations')==60
        and a.get('healthy_replay_work_units')==168
        and a.get('capacity_rejections')==2
        and a.get('failed_attempts_charged')==3
        and a.get('invalid_admission_patterns_rejected')==10,
        'R116_COUNTS'
    )

    runs=a.get('interleaved_sessions',{})

    need(
        type(runs.get('runs')) is dict
        and len(runs['runs'])==12
        and runs.get('session_count')==12
        and runs.get('acknowledged_operations')==60
        and runs.get('attempted_work_units')==168
        and runs.get('nonlinear_windows')==48
        and runs.get('schur_marginalizations')==36
        and runs.get('same_graph_prior_transfers')==18,
        'R116_INTERLEAVING'
    )

    pool=runs.get('pool_audit',{})

    need(
        pool.get('created')==12
        and pool.get('active_count')==0
        and pool.get('retired_count')==12
        and pool.get('peak_active')==2,
        'R116_SESSION_RETIREMENT'
    )

    for row in runs['runs'].values():
        rebase=row.get('recentered') is True
        bound=2e-5 if rebase else 1e-8

        need(
            row.get('acknowledged_operations')==5
            and row.get('attempted_work_units')==14
            and row.get('committed_work_units')==14
            and row.get('nonlinear_windows')==4
            and row.get('schur_marginalizations')==3
            and row.get('prior_transfers')==(3 if rebase else 0)
            and row.get('factor_ownership_verified') is True
            and row.get('retired') is True
            and 0<=row.get('max_abs_error_vs_s6',1)<bound,
            'R116_HEALTHY_CASE'
        )

    cap=a.get('capacity_and_retirement',{})

    need(
        cap.get('active_capacity_denials')==1
        and cap.get('creation_limit_denials')==1
        and cap.get('retired_handles')==3
        and cap.get('retired_handle_reuses_denied')==3
        and cap.get('active_after_retirement')==0,
        'R116_CAPACITY'
    )

    isolation=a.get('fault_isolation',{})

    need(
        isolation.get('injected_failed_attempts')==3
        and isolation.get('charged_failed_work_units')==3
        and isolation.get('cross_graph_packet_rejections')==1
        and isolation.get('exhausted_fourth_attempt_rejected')
            is True
        and isolation.get('unrelated_session_completed') is True
        and isolation.get('registry_active_after')==0,
        'R116_FAULT_ISOLATION'
    )

    cancellation=a.get('prepublication_retirement',{})

    need(
        cancellation.get('attempted_work_units_charged')==1
        and cancellation.get('committed_work_units')==0
        and cancellation.get('candidate_acknowledged') is False
        and cancellation.get('committed_state_unchanged') is True
        and cancellation.get('cancelled_session_retired') is True,
        'R116_CANCELLATION'
    )

    admissions=a.get('admission_fault_patterns',{})

    need(
        admissions.get('rejected_count')==10
        and type(admissions.get('rejected_fault_patterns')) is list
        and len(admissions['rejected_fault_patterns'])==10
        and admissions.get(
            'attempted_work_charged_for_invalid_operations'
        )==0
        and admissions.get('eventual_successful_completion')
            is True,
        'R116_ADMISSION'
    )

    need(
        b.get('healthy_sessions')==12
        and b.get('acknowledged_operations')==60
        and b.get('healthy_attempted_work_units')==168
        and b.get('healthy_retirement_receipts')==12
        and b.get('corruption_controls_rejected')==2
        and b.get('cross_registry_admissions_rejected')==6
        and b.get('charged_failed_attempts')==3,
        'R117_COUNTS'
    )

    healthy=b.get('healthy_interleaving',{})

    need(
        type(healthy.get('runs')) is dict
        and len(healthy['runs'])==12
        and healthy.get('healthy_sessions')==12
        and healthy.get('nonlinear_windows')==48
        and healthy.get('schur_events')==36
        and healthy.get('prior_transfers')==18
        and healthy.get('retirement_receipts')==12,
        'R117_INTERLEAVING'
    )

    ledger=healthy.get('registry_audit',{})

    need(
        ledger.get('created')==12
        and ledger.get('active_count')==0
        and ledger.get('retired_count')==12
        and ledger.get('peak_active')==2
        and ledger.get('receipt_count')==12
        and type(ledger.get('retirement_chain_sha256')) is str
        and len(ledger['retirement_chain_sha256'])==64
        and ledger['retirement_chain_sha256']!='0'*64,
        'R117_RETIREMENT_LEDGER'
    )

    for row in healthy['runs'].values():
        rebase=row.get('recentered') is True
        bound=2e-5 if rebase else 1e-8

        need(
            row.get('acknowledged_operations')==5
            and row.get('attempted_work_units')==14
            and row.get('committed_work_units')==14
            and row.get('nonlinear_windows')==4
            and row.get('schur_events')==3
            and row.get('prior_transfers')==(3 if rebase else 0)
            and row.get('retired') is True
            and 0<=row.get('max_abs_error_vs_s6',1)<bound,
            'R117_HEALTHY_CASE'
        )

    cap=b.get('capacity_and_stale_handles',{})

    need(
        cap.get('active_capacity_rejections')==1
        and cap.get('creation_limit_rejections')==1
        and cap.get('retired_handles')==3
        and cap.get('stale_handle_rejections')==1
        and cap.get('opaque_handle_reuse') is False
        and cap.get('registry_drained') is True,
        'R117_CAPACITY'
    )

    cross=b.get('cross_registry_admissions',{})

    need(
        cross.get('rejection_count')==6
        and type(cross.get('rejected_patterns')) is list
        and len(cross['rejected_patterns'])==6
        and cross.get('zero_work_charged_for_invalid_admissions')
            is True
        and cross.get('both_registries_completed') is True
        and cross.get('cross_registry_handle_reuse_denied')
            is True,
        'R117_CROSS_REGISTRY'
    )

    integrity=b.get('ledger_corruption_controls',{})

    need(
        integrity.get('detected_corruptions')==2
        and integrity.get('linked_ledger_tamper_rejected') is True
        and integrity.get('underlying_receipt_tamper_rejected')
            is True
        and integrity.get('subsequent_healthy_registry_operation')
            is True
        and integrity.get('durable_audit_storage_proven') is False,
        'R117_CORRUPTION'
    )

    isolation=b.get('failure_exhaustion_isolation',{})

    need(
        isolation.get('charged_failed_attempts')==3
        and isolation.get('fourth_attempt_rejected') is True
        and isolation.get('healthy_peer_completed') is True
        and isolation.get('retirement_chain_entries')==2
        and isolation.get('registry_drained') is True,
        'R117_FAULT_ISOLATION'
    )

    cancellation=b.get('prepublication_cancellation',{})

    need(
        cancellation.get('failed_candidate_attempt_units')==1
        and cancellation.get('committed_work_units')==0
        and cancellation.get('committed_estimator_unchanged')
            is True
        and cancellation.get('candidate_acknowledged') is False
        and cancellation.get('cancelled_and_retired') is True
        and cancellation.get('stale_handle_reuse_rejected') is True,
        'R117_CANCELLATION'
    )

    for report in (a,b):
        need(
            report.get('scientific_gates_closed')==11,
            'REPORT_GATES'
        )

        for key in REPORT_DENIALS:
            need(
                report.get(key) is False,
                'SCIENCE_DENIAL:'+key
            )

    for key in (
        'actual_concurrent_thread_safety_verified',
        'physical_memory_reclamation_verified',
        'wall_clock_resource_bound_verified',
        'durable_registry_recovery_verified',
        'cryptographic_owner_authentication_verified',
        'private_python_object_isolation_verified',
        'hardware_streaming_verified',
    ):
        need(a.get(key) is False,'R116_BOUNDARY:'+key)

    for key in (
        'authenticated_audit_log_verified',
        'durable_audit_log_verified',
        'physical_memory_reclamation_verified',
        'actual_concurrent_thread_safety_verified',
        'direct_private_object_mutation_isolated',
        'cryptographic_owner_authentication_verified',
        'hardware_streaming_verified',
        'physical_resource_deadlines_verified',
    ):
        need(b.get(key) is False,'R117_BOUNDARY:'+key)

    need(
        va.get('schema')==
        'TRUST_ROBOT_R116_INDEPENDENT_SESSION_VALIDATION_V1'
        and va.get('status')=='PASS'
        and va.get('regression_tests')==58
        and va.get('healthy_sessions')==12,
        'R116_RECEIPT'
    )

    need(
        vb.get('schema')==
        'TRUST_ROBOT_R117_INDEPENDENT_REGISTRY_VALIDATION_V1'
        and vb.get('status')=='PASS'
        and vb.get('regression_tests')==62
        and vb.get('healthy_sessions')==12
        and vb.get('retirement_receipts')==12
        and vb.get('ledger_tamper_controls')==2
        and vb.get('cross_registry_rejections')==6,
        'R117_RECEIPT'
    )

    for receipt,phase,engine,tests,contract,report in (
        (
            va,'r116','r116_lifecycle.py',
            'test_r116.py',
            'r116_lifecycle_contract_v1.md',
            'r116_session_lifecycle_v1.json',
        ),
        (
            vb,'r117','r117_registry.py',
            'test_r117.py',
            'r117_registry_contract_v1.md',
            'r117_registry_hardening_v1.json',
        ),
    ):
        prefix='evidence/'+phase+'/'

        need(
            receipt.get('engine_sha256')==
                PINS[prefix+'dev/'+engine]
            and receipt.get('tests_sha256')==
                PINS[prefix+'dev/'+tests]
            and receipt.get('contract_sha256')==
                PINS[prefix+'dev/'+contract]
            and receipt.get('report_sha256')==
                PINS[prefix+'result/'+report],
            'RECEIPT_HASH:'+phase
        )

        need(
            receipt.get('parent_git_commit')==BASE
            and receipt.get('s6_source_sha256')==S6_SHA
            and receipt.get('scientific_gates_closed')==11
            and receipt.get('real_sensor_factors_authorized')
                is False
            and receipt.get('confirmation_test_accessed')
                is False,
            'RECEIPT_BOUNDARY:'+phase
        )

        need(
            receipt.get('r115_manifest_sha256')==
                m.get('r115_manifest_sha256'),
            'R115_MANIFEST_LINEAGE:'+phase
        )

    need(
        vb.get('r116_report_sha256')==
        PINS['evidence/r116/result/r116_session_lifecycle_v1.json'],
        'R116_R117_LINEAGE'
    )

    need(
        m.get('r116_test_count')==58
        and m.get('r117_test_count')==62
        and m.get('archived_regression_tests')==120
        and m.get('s6_source_sha256')==S6_SHA
        and m.get('scientific_gates_closed')==11,
        'MANIFEST_COUNTS'
    )

    for key in MANIFEST_DENIALS:
        need(
            m.get(key) is False,
            'MANIFEST_GATE:'+key
        )

    print('R118_STANDALONE_CHECKPOINT_VERIFIER=PASS')
    print('R118_SOURCE_AND_METADATA_SHA256=12_PASS')
    print('R118_R116_R117_RESULT_LINEAGE=PASS')
    print('R118_REGISTRY_AND_RETIREMENT_AUDIT=PASS')
    print('R118_SCIENTIFIC_GATES=11_CLOSED')

if __name__=='__main__':
    need(
        len(sys.argv)==3
        and sys.argv[1]=='verify',
        'ARGUMENTS'
    )

    verify(pathlib.Path(sys.argv[2]))
