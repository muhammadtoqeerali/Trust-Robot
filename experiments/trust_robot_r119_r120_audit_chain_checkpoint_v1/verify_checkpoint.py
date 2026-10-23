"""R121 standalone source-pinned scientific checkpoint verifier."""

import hashlib
import json
import pathlib
import stat
import sys

SCHEMA='TRUST_ROBOT_R119_R120_AUDIT_CHAIN_CHECKPOINT_V1'
BASE='39a4a27fad7ed9a84b872b1b1b4146f6f9dd8da9'
BRANCH='kios-isaacsim-v15-integration'
S6_SHA='a1c9d0b4b9219d1e1b370e5ab5f42fcb25ac53f1b77f005cb42b3497b90bfc9a'

PINS={
    'evidence/r119/dev/r119_observation.py':
        '61b0e267a92fc99b1deebb786debe3a8ae76719b9675afba89e3ef0bac16d669',
    'evidence/r119/dev/test_r119.py':
        '91456f65d9b0d005aaa0ef3d7ea6607eb92003c28a7961aec636368a279bd4a5',
    'evidence/r119/dev/r119_observation_contract_v1.md':
        '65605811297b702aec7528614bb1edcfd65138ba1b6c3f7e5a4ad679c24e8c42',
    'evidence/r119/result/r119_audit_observation_v1.json':
        '56d526116859247549443f473f9c9473194dbc8a9d6e92f6347f8820dabf7a6a',
    'evidence/r119/result/r119_independent_validation_v1.json':
        '57e0f5c11e4070304aa5f87c47f2e4006aca2e0756defa71e43f2f1e7699cc14',

    'evidence/r120/dev/r120_audit_guard.py':
        '96dbbfb1c3f492d4797963191b917713324c35755d71b6125d06cd7b29932739',
    'evidence/r120/dev/test_r120.py':
        '72d68d914eeed456a2ea50c697ab1a8e8688d10fa0add276bac4b381dedb5145',
    'evidence/r120/dev/r120_audit_guard_contract_v1.md':
        '373bf3b40e71711728746652b43b1d0156fe8f8e3fe5f45967cce9b7a175dbc8',
    'evidence/r120/result/r120_audit_chain_guard_v1.json':
        '01d13b234ec5942ada81bbc3feda85bf40963dbaf9fc43fbf1b44c7a7b02df9f',
    'evidence/r120/result/r120_independent_validation_v1.json':
        '7630d488c70801779b423df59c8a1a6b48c90a258c68c8f9925168e8f13617ef',
}

DOCS={
    'AGENTS.md',
    'docs/TRUST_ROBOT_PROJECT_STATE.md',
    'docs/audits/trust_robot/TRUST_ROBOT_KIOS_R119_R120_AUDIT_CHAIN_CHECKPOINT_V1.md',
}

DENIALS=(
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
    'authenticated_audit_log_verified',
    'durable_audit_log_verified',
    'concurrent_thread_safety_verified',
    'physical_memory_reclamation_verified',
    'physical_resource_deadlines_verified',
    'health_training_authorized',
    'ate_rpe_authorized',
    'confirmation_test_accessed',
    'raw_gt_or_rosbags_archived',
    'qualified_author_reply_ingested',
    'receipt_saturation_liveness_proven',
    'saturation_emergency_shutdown_proven',
)

def need(ok,reason):
    if not ok:
        raise ValueError('R121_CHECKPOINT_DENIED:'+reason)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def load(root,name):
    return json.loads((root/name).read_bytes())

def verify(root):
    need(
        root.is_dir() and not root.is_symlink(),
        'ARCHIVE_ROOT'
    )

    manifest=load(root,'checkpoint_manifest_v1.json')

    need(manifest.get('schema')==SCHEMA,'SCHEMA')
    need(manifest.get('parent_commit')==BASE,'PARENT')
    need(manifest.get('branch')==BRANCH,'BRANCH')

    need(
        manifest.get('source_count')==10
        and manifest.get('source_sha256')==PINS,
        'SOURCE_PINS'
    )

    metadata=manifest.get('metadata_sha256')

    need(
        type(metadata) is dict
        and set(metadata)=={
            'README.md',
            'verify_checkpoint.py',
        },
        'METADATA_PINS'
    )

    docs=manifest.get('documentation_sha256')

    need(
        type(docs) is dict
        and set(docs)==DOCS,
        'DOCUMENTATION_PINS'
    )

    expected=set(PINS)|set(metadata)|{
        'checkpoint_manifest_v1.json'
    }

    directories=set()

    for name in expected:
        path=pathlib.PurePosixPath(name)

        need(
            not path.is_absolute()
            and '..' not in path.parts,
            'UNSAFE_PATH'
        )

        for i in range(1,len(path.parts)):
            directories.add(
                '/'.join(path.parts[:i])
            )

    found={
        p.relative_to(root).as_posix()
        for p in root.rglob('*')
    }

    need(
        found==expected|directories,
        'EXACT_ARCHIVE_TREE'
    )

    for name in directories:
        path=root/name

        need(
            path.is_dir() and not path.is_symlink(),
            'ARCHIVE_DIRECTORY:'+name
        )

    for name in expected:
        path=root/name
        st=path.lstat()

        need(
            stat.S_ISREG(st.st_mode)
            and st.st_nlink==1
            and 0<st.st_size<2_000_000,
            'REGULAR_FILE:'+name
        )

    # Literal private prefixes are intentionally
    # composed rather than embedded in this source.
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
            not any(prefix in raw for prefix in forbidden),
            'PRIVATE_PATH:'+name
        )

    a=load(
        root,
        'evidence/r119/result/r119_audit_observation_v1.json'
    )
    b=load(
        root,
        'evidence/r120/result/r120_audit_chain_guard_v1.json'
    )

    va=load(
        root,
        'evidence/r119/result/r119_independent_validation_v1.json'
    )
    vb=load(
        root,
        'evidence/r120/result/r120_independent_validation_v1.json'
    )

    need(
        a.get('schema')==
        'TRUST_ROBOT_R119_SYNTHETIC_AUDIT_OBSERVATION_V1',
        'R119_SCHEMA'
    )

    need(
        b.get('schema')==
        'TRUST_ROBOT_R120_SYNTHETIC_AUDIT_CHAIN_GUARD_V1',
        'R120_SCHEMA'
    )

    need(
        a.get('status')==
        'PASS_SYNTHETIC_AUDIT_OBSERVATION_SOFTWARE_ONLY'
        and b.get('status')==
        'PASS_SYNTHETIC_AUDIT_CHAIN_GUARDS_ONLY',
        'RESULT_STATUS'
    )

    need(
        a.get('healthy_sessions')==12
        and a.get('acknowledged_operations')==60
        and a.get('attempted_work_units')==168
        and a.get('retirement_receipts')==12
        and a.get('rejected_admission_receipts')==10
        and a.get('charged_failure_receipts')==4
        and a.get('cancelled_candidate_receipts')==1
        and a.get('internal_tamper_controls')==1,
        'R119_COUNTS'
    )

    healthy=a.get('healthy_observation',{})

    need(
        type(healthy.get('runs')) is dict
        and len(healthy['runs'])==12
        and healthy.get('sessions')==12
        and healthy.get('acknowledged_operations')==60
        and healthy.get('attempted_work_units')==168
        and healthy.get('retirement_receipts')==12
        and healthy.get('denial_receipts')==0
        and healthy.get('active_after')==0
        and healthy.get(
            'detached_retirement_copy_verified'
        ) is True,
        'R119_HEALTHY_CASES'
    )

    for row in healthy['runs'].values():
        rebase=row.get('recentered') is True
        threshold=2e-5 if rebase else 1e-8

        need(
            row.get('acknowledged_operations')==5
            and row.get('attempted_work_units')==14
            and row.get('nonlinear_windows')==4
            and row.get('schur_events')==3
            and row.get('prior_transfers')==
                (3 if rebase else 0)
            and row.get('retired') is True
            and 0<=row.get(
                'max_abs_error_vs_s6',1
            )<threshold,
            'R119_HEALTHY_ROW'
        )

    admissions=a.get('denied_admissions',{})

    need(
        admissions.get('denials')==10
        and type(admissions.get('patterns')) is list
        and len(admissions['patterns'])==10
        and admissions.get(
            'invalid_admission_work_units'
        )==0
        and admissions.get('successful_recovery') is True
        and admissions.get(
            'detached_failure_receipts_verified'
        ) is True
        and admissions.get(
            'linked_denial_chain_verified'
        ) is True,
        'R119_ADMISSIONS'
    )

    failures=a.get('charged_failure_observation',{})

    need(
        failures.get('failure_receipts')==4
        and failures.get('aborted_candidates')==3
        and failures.get('charged_attempt_ledger')==
            [1,1,1,0]
        and failures.get(
            'fourth_attempt_denied_without_charge'
        ) is True
        and failures.get(
            'committed_state_preserved'
        ) is True
        and failures.get('healthy_peer_completed') is True
        and failures.get('retirement_receipts')==2,
        'R119_FAILED_CANDIDATES'
    )

    cancellation=a.get('prepublication_failure_receipt',{})

    need(
        cancellation.get('denial_receipts')==1
        and cancellation.get('candidate_acknowledged') is False
        and cancellation.get('attempted_work_units_charged')==1
        and cancellation.get('committed_state_unchanged') is True
        and cancellation.get('terminal_cancellation') is True
        and cancellation.get('retired_after_abort') is True,
        'R119_PREPUBLICATION'
    )

    tamper=a.get('internal_receipt_tamper',{})

    need(
        tamper.get(
            'internal_receipt_tamper_rejected'
        ) is True
        and tamper.get(
            'subsequent_operations_after_restoration'
        ) is True,
        'R119_TAMPER'
    )

    need(
        b.get('healthy_sessions')==6
        and b.get('healthy_acknowledgements')==30
        and b.get('healthy_replay_work_units')==84
        and b.get('admission_denials')==10
        and b.get('charged_failed_candidates')==3
        and b.get('retirement_order_denials')==1
        and b.get('bounded_denial_capacity') is True
        and b.get('receipt_semantics_verified') is True
        and b.get(
            'out_of_order_retirement_denied_pre_mutation'
        ) is True,
        'R120_COUNTS'
    )

    healthy=b.get('healthy_cases',{})

    need(
        type(healthy.get('runs')) is dict
        and len(healthy['runs'])==6
        and healthy.get('sessions')==6
        and healthy.get('acknowledged_operations')==30
        and healthy.get('attempted_work_units')==84
        and healthy.get('nonlinear_windows')==24
        and healthy.get('schur_events')==18
        and healthy.get('prior_transfers')==9
        and healthy.get(
            'detached_observations_verified'
        ) is True,
        'R120_HEALTHY_CASES'
    )

    for row in healthy['runs'].values():
        rebase=row.get('recentered') is True
        threshold=2e-5 if rebase else 1e-8

        need(
            row.get('acknowledged_operations')==5
            and row.get('attempted_work_units')==14
            and row.get('nonlinear_windows')==4
            and row.get('schur_events')==3
            and row.get('prior_transfers')==
                (3 if rebase else 0)
            and row.get('retired') is True
            and 0<=row.get(
                'max_abs_error_vs_s6',1
            )<threshold,
            'R120_HEALTHY_ROW'
        )

    admissions=b.get('admission_receipts',{})

    need(
        admissions.get('denials')==10
        and type(admissions.get('rejected_patterns')) is list
        and len(admissions['rejected_patterns'])==10
        and admissions.get('charged_attempt_units')==0
        and admissions.get(
            'eventual_healthy_completion'
        ) is True
        and admissions.get(
            'all_denials_unacknowledged'
        ) is True
        and admissions.get(
            'semantic_denial_validation'
        ) is True,
        'R120_ADMISSIONS'
    )

    failures=b.get('failed_candidate_receipts',{})

    need(
        failures.get('aborted_candidates')==3
        and failures.get('denial_receipts')==4
        and failures.get('attempt_charge_ledger')==
            [1,1,1,0]
        and failures.get(
            'fourth_attempt_rejected_without_charge'
        ) is True
        and failures.get('committed_state_preserved') is True
        and failures.get('healthy_peer_completed') is True
        and failures.get('retired_sessions')==2
        and failures.get(
            'semantic_receipts_verified'
        ) is True,
        'R120_FAILED_CANDIDATES'
    )

    order=b.get('retirement_order_guard',{})

    need(
        order.get('pre_mutation_order_rejections')==1
        and order.get('policy_receipts')==1
        and order.get('policy_tamper_controls')==1
        and order.get('committed_state_unchanged') is True
        and order.get('subsequent_ordered_retirement') is True
        and order.get('retired_sessions')==2
        and order.get('registry_integrity_preserved') is True,
        'R120_RETIREMENT_ORDER'
    )

    capacity=b.get('capacity_saturation',{})

    need(
        capacity.get('maximum_denial_receipts')==3
        and capacity.get('recorded_denials')==3
        and capacity.get('additional_operations_blocked')==2
        and capacity.get('additional_individual_receipts')==0
        and capacity.get('committed_state_unchanged') is True
        and capacity.get(
            'read_only_observations_available'
        ) is True
        and capacity.get('active_session_left_unretired') is True
        and capacity.get(
            'liveness_guarantee_after_saturation'
        ) is False,
        'R120_CAPACITY_AND_LIVENESS'
    )

    cancellation=b.get('prepublication_abort',{})

    need(
        cancellation.get('aborted_candidates')==1
        and cancellation.get('charged_attempt_units')==1
        and cancellation.get('committed_units')==0
        and cancellation.get('committed_state_preserved') is True
        and cancellation.get('cancellation_terminal') is True
        and cancellation.get('retired_after_abort') is True,
        'R120_PREPUBLICATION'
    )

    tamper=b.get('denial_tamper_control',{})

    need(
        tamper.get('linked_denial_tamper_rejected') is True
        and tamper.get(
            'subsequent_operations_after_restore'
        ) is True
        and tamper.get('authenticated_log_verified') is False,
        'R120_TAMPER'
    )

    for report in (a,b):
        need(
            report.get('scientific_gates_closed')==11,
            'REPORT_GATES'
        )

        for key in DENIALS:
            need(
                report.get(key) is False,
                'SCIENCE_DENIAL:'+key
            )

    for key in (
        'authenticated_logging_verified',
        'durable_logging_verified',
        'external_ledger_anchor_verified',
        'malicious_inprocess_tamper_protection_verified',
        'actual_concurrent_thread_safety_verified',
        'physical_memory_reclamation_verified',
        'wall_clock_resource_bound_verified',
        'cryptographic_owner_authentication_verified',
        'hardware_streaming_verified',
    ):
        need(
            a.get(key) is False,
            'R119_SCIENCE_BOUNDARY:'+key
        )

    for key in (
        'authenticated_logging_verified',
        'durable_logging_verified',
        'external_ledger_anchor_verified',
        'malicious_inprocess_tamper_protection_verified',
        'concurrent_thread_safety_verified',
        'physical_memory_reclamation_verified',
        'wall_clock_resource_bound_verified',
        'cryptographic_owner_authentication_verified',
        'hardware_streaming_verified',
    ):
        need(
            b.get(key) is False,
            'R120_SCIENCE_BOUNDARY:'+key
        )

    need(
        va.get('schema')==
        'TRUST_ROBOT_R119_INDEPENDENT_OBSERVATION_VALIDATION_V1'
        and va.get('status')=='PASS'
        and va.get('regression_tests')==58
        and va.get('healthy_sessions')==12
        and va.get('rejected_admission_receipts')==10
        and va.get('charged_failure_receipts')==4,
        'R119_RECEIPT'
    )

    need(
        vb.get('schema')==
        'TRUST_ROBOT_R120_INDEPENDENT_AUDIT_GUARD_VALIDATION_V1'
        and vb.get('status')=='PASS'
        and vb.get('regression_tests')==70
        and vb.get('healthy_sessions')==6
        and vb.get('admission_denials')==10
        and vb.get('charged_failed_candidates')==3
        and vb.get(
            'retirement_order_preflight_verified'
        ) is True
        and vb.get(
            'bounded_denial_history_verified'
        ) is True
        and vb.get(
            'liveness_after_saturation_verified'
        ) is False,
        'R120_RECEIPT'
    )

    for receipt,phase,engine,tests,contract,report in (
        (
            va,'r119','r119_observation.py',
            'test_r119.py',
            'r119_observation_contract_v1.md',
            'r119_audit_observation_v1.json'
        ),
        (
            vb,'r120','r120_audit_guard.py',
            'test_r120.py',
            'r120_audit_guard_contract_v1.md',
            'r120_audit_chain_guard_v1.json'
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
            'RECEIPT_SHA:'+phase
        )

        need(
            receipt.get('parent_git_commit')==BASE
            and receipt.get('s6_source_sha256')==S6_SHA
            and receipt.get('r118_manifest_sha256')==
                manifest.get('r118_manifest_sha256')
            and receipt.get('scientific_gates_closed')==11
            and receipt.get('real_sensor_factors_authorized')
                is False
            and receipt.get('confirmation_test_accessed')
                is False,
            'RECEIPT_LINEAGE:'+phase
        )

    need(
        vb.get('r119_report_sha256')==
        PINS[
            'evidence/r119/result/r119_audit_observation_v1.json'
        ],
        'R119_TO_R120_LINEAGE'
    )

    need(
        manifest.get('r119_test_count')==58
        and manifest.get('r120_test_count')==70
        and manifest.get('archived_regression_tests')==128
        and manifest.get('s6_source_sha256')==S6_SHA
        and manifest.get('scientific_gates_closed')==11,
        'MANIFEST_COUNTS'
    )

    for key in MANIFEST_DENIALS:
        need(
            manifest.get(key) is False,
            'MANIFEST_GATE:'+key
        )

    print('R121_STANDALONE_CHECKPOINT_VERIFIER=PASS')
    print('R121_SOURCE_AND_METADATA_SHA256=12_PASS')
    print('R121_R119_R120_RESULT_LINEAGE=PASS')
    print('R121_RECEIPT_AND_SATURATION_BOUNDARY=PASS')
    print('R121_SCIENTIFIC_GATES=11_CLOSED')

if __name__=='__main__':
    need(
        len(sys.argv)==3
        and sys.argv[1]=='verify',
        'ARGUMENTS'
    )

    verify(pathlib.Path(sys.argv[2]))
