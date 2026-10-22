"""Standalone SHA-pinned R110-R111 checkpoint verifier."""

import hashlib
import json
import pathlib
import stat
import sys

SCHEMA='TRUST_ROBOT_R110_R111_FAILURE_TRANSACTION_CHECKPOINT_V1'
BASE='0ea093b47b04682d1144dc6c2e7f25b9dac3baf2'
BRANCH='kios-isaacsim-v15-integration'
S6_SHA='a1c9d0b4b9219d1e1b370e5ab5f42fcb25ac53f1b77f005cb42b3497b90bfc9a'

PINS={
    'evidence/r110/dev/r110_failstop.py':
        '646a87d7e87122e3054000f755111d00b55ddfb5fe88820613298f564541eed5',

    'evidence/r110/dev/test_r110.py':
        'd807b73a8a9d5f9a52a7af4b937858b61d8fc967d2cdf1861f16e6e78745eabd',

    'evidence/r110/dev/r110_failstop_contract_v1.md':
        '6dd0a9a91f77d5cc57509ef395b5eff8e48fd3bde642a097cf6176b85f094da4',

    'evidence/r110/result/r110_failure_atomicity_v1.json':
        '044286f5764ed82bf66f2bf8fa662a4127706ca5b9a1b283821d52205b21112c',

    'evidence/r110/result/r110_independent_validation_v1.json':
        'f33b78735f7d20933238210d21a37c6b56230ce7bc30164bfa43a7aa1a1b492c',

    'evidence/r111/dev/r111_transaction.py':
        'e2c7a35aaf37c3b9da17fde7b23a76e55c9468db569ea120fe7f686aa0fd498f',

    'evidence/r111/dev/test_r111.py':
        '02eaba8a7a89b028ed663d85a5a3fe06d60407d30aa0b9f402ee0fa7b805c70c',

    'evidence/r111/dev/r111_transaction_contract_v1.md':
        'd7470694b523bcba6d476b7dfe0945b2cb2ea6cbe3734293ac1b5bbc003e51d3',

    'evidence/r111/result/r111_shadow_transaction_v1.json':
        '66a77ed7aaa9d68a0a04e53ff32a668673b97a0aed8d3b968f0ac17eaf01f8bd',

    'evidence/r111/result/r111_independent_validation_v1.json':
        '53b2860b585bbf372bfccede1182a9f6e0690ef811975ec1df0a14ac696afee3',
}

DOCS={
    'AGENTS.md',
    'docs/TRUST_ROBOT_PROJECT_STATE.md',
    'docs/audits/trust_robot/TRUST_ROBOT_KIOS_R110_R111_FAILURE_TRANSACTION_CHECKPOINT_V1.md',
}

def need(ok,reason):
    if not ok:
        raise ValueError(
            'R112_CHECKPOINT_DENIED:'+reason
        )

def sha(data):
    return hashlib.sha256(data).hexdigest()

def obj(root,name):
    return json.loads((root/name).read_bytes())

def verify(root):
    need(
        root.is_dir() and not root.is_symlink(),
        'ARCHIVE_ROOT'
    )

    m=obj(root,'checkpoint_manifest_v1.json')

    need(m.get('schema')==SCHEMA,'SCHEMA')
    need(m.get('parent_commit')==BASE,'PARENT')
    need(m.get('branch')==BRANCH,'BRANCH')

    need(
        m.get('source_sha256')==PINS
        and m.get('source_count')==10,
        'SOURCE_PINS'
    )

    metadata=m.get('metadata_sha256')

    need(
        type(metadata) is dict
        and set(metadata)=={
            'README.md',
            'verify_checkpoint.py',
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

    directories=set()

    for name in expected:
        path=pathlib.PurePosixPath(name)

        need(
            not path.is_absolute()
            and '..' not in path.parts,
            'UNSAFE_PATH'
        )

        for index in range(1,len(path.parts)):
            directories.add(
                '/'.join(path.parts[:index])
            )

    observed={
        p.relative_to(root).as_posix()
        for p in root.rglob('*')
    }

    need(
        observed==expected|directories,
        'EXACT_ARCHIVE_TREE'
    )

    for name in directories:
        p=root/name
        need(
            p.is_dir() and not p.is_symlink(),
            'ARCHIVE_DIRECTORY'
        )

    for name in expected:
        p=root/name
        s=p.lstat()

        need(
            stat.S_ISREG(s.st_mode)
            and s.st_nlink==1
            and 0<s.st_size<2_000_000,
            'REGULAR_FILE:'+name
        )

    # Deliberately split private path signatures
    # to avoid matching this verifier's own code.
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
            not any(x in raw for x in forbidden),
            'PRIVATE_PATH:'+name
        )

    a=obj(
        root,
        'evidence/r110/result/r110_failure_atomicity_v1.json'
    )

    b=obj(
        root,
        'evidence/r111/result/r111_shadow_transaction_v1.json'
    )

    va=obj(
        root,
        'evidence/r110/result/r110_independent_validation_v1.json'
    )

    vb=obj(
        root,
        'evidence/r111/result/r111_independent_validation_v1.json'
    )

    need(
        a.get('schema')==
        'TRUST_ROBOT_R110_SYNTHETIC_FAIL_STOP_AUDIT_V1',
        'R110_SCHEMA'
    )

    need(
        b.get('schema')==
        'TRUST_ROBOT_R111_SYNTHETIC_SHADOW_TRANSACTION_V1',
        'R111_SCHEMA'
    )

    need(
        a.get('status')==
            'PASS_SYNTHETIC_FAIL_STOP_SOFTWARE_ONLY'
        and b.get('status')==
            'PASS_SYNTHETIC_SHADOW_TRANSACTION_ONLY',
        'REPORT_STATUS'
    )

    need(
        a.get('healthy_solver_executions')==6
        and a.get('healthy_nonlinear_windows')==24
        and a.get('healthy_schur_marginalizations')==18
        and a.get('healthy_prior_recenterings')==9
        and a.get('fault_injection_count')==6
        and a.get('faulted_sessions_quarantined')==6
        and a.get('faults_with_internal_state_change')==5,
        'R110_COUNTS'
    )

    need(
        type(a.get('healthy_cases')) is dict
        and len(a['healthy_cases'])==6
        and type(a.get('fault_cases')) is dict
        and len(a['fault_cases'])==6,
        'R110_CASES'
    )

    for case in a['fault_cases'].values():
        receipt=case.get('fault_receipt')

        need(
            type(receipt) is dict
            and case.get('session_quarantined') is True
            and case.get('post_fault_operations_rejected')==2
            and case.get('post_fault_state_unchanged_on_rejection')
                is True
            and case.get('rollback_proven') is False,
            'R110_FAULT_QUARANTINE'
        )

        need(
            receipt.get('exception_type')=='InjectedFault'
            and receipt.get('successful_acknowledgement_issued')
                is False
            and receipt.get('continued_execution_authorized')
                is False
            and receipt.get('transactional_rollback_performed')
                is False,
            'R110_FAULT_RECEIPT'
        )

    need(
        a.get('admission',{}).get('pre_admission_rejections')==8
        and a.get('admission',{}).get('state_unchanged_on_rejection')
            is True
        and a.get('fresh_session_recovery_verified') is True,
        'R110_ADMISSION'
    )

    need(
        b.get('healthy_solver_sessions')==12
        and b.get('committed_operations')==60
        and b.get('nonlinear_windows_in_committed_sessions')==48
        and b.get('schur_events_in_committed_sessions')==36
        and b.get('same_graph_prior_transfers')==18
        and b.get('fault_injections')==6
        and b.get('unchanged_committed_snapshots_after_fault')==6
        and b.get('successful_retries')==6,
        'R111_COUNTS'
    )

    need(
        type(b.get('healthy_cases')) is dict
        and len(b['healthy_cases'])==12
        and type(b.get('fault_cases')) is dict
        and len(b['fault_cases'])==6,
        'R111_CASES'
    )

    for case in b['healthy_cases'].values():
        threshold=(
            2e-5
            if case.get('recentered') is True
            else 1e-8
        )

        need(
            case.get('acknowledged_operations')==5
            and case.get('nonlinear_windows')==4
            and case.get('schur_marginalizations')==3
            and case.get('prior_transfers')==
                (3 if case.get('recentered') is True else 0)
            and case.get('factor_ownership_verified') is True
            and case.get('candidate_state_published_after_success')
                is True
            and 0<=case.get('max_abs_error_vs_s6',1)<threshold,
            'R111_ESTIMATOR_EQUIVALENCE'
        )

    for case in b['fault_cases'].values():
        for key in (
            'no_ack_on_failed_operation',
            'committed_snapshot_unchanged',
            'committed_object_identity_unchanged',
            'failed_shadow_discarded',
            'retry_after_injection_removed',
            'session_recovered_without_reusing_failed_shadow',
        ):
            need(
                case.get(key) is True,
                'R111_FAULT_ATOMICITY:'+key
            )

        need(
            case.get('new_physical_fault_recovery_proven')
            is False,
            'R111_PHYSICAL_CLAIM'
        )

    need(
        b.get('invalid_admission',{}).get('rejections')==8
        and b.get('invalid_admission',{}).get('state_unchanged')
            is True
        and b.get('invalid_admission',{}).get(
            'session_completed_after_rejections'
        ) is True
        and b.get('in_memory_shadow_isolation_verified') is True,
        'R111_ADMISSION'
    )

    need(
        a.get('scientific_gates_closed')==11
        and b.get('scientific_gates_closed')==11,
        'SCIENTIFIC_GATES'
    )

    for key in (
        'existing_r108_transactional_rollback_proven',
        'new_transactional_rollback_implemented',
        'faulted_session_resume_authorized',
        'hardware_fault_recovery_verified',
        'real_time_deadlines_verified',
        'transport_authentication_verified',
        'r95_gaussian_prior_imported',
        'real_sensor_factors_authorized',
        'physical_clock_or_extrinsics_verified',
        'health_training_authorized',
        'ate_rpe_authorized',
        'confirmation_test_accessed',
        'raw_gt_or_rosbags_opened',
    ):
        need(
            a.get(key) is False,
            'R110_SCIENCE_DENIAL:'+key
        )

    for key in (
        'original_r107_r108_modified',
        'existing_r108_rollback_implemented',
        'durable_crash_recovery_verified',
        'distributed_exactly_once_verified',
        'concurrent_atomic_publication_verified',
        'direct_private_object_mutation_isolated',
        'physical_hardware_recovery_verified',
        'hardware_streaming_verified',
        'transport_authentication_verified',
        'r95_backend_imported',
        'real_sensor_factors_authorized',
        'physical_clock_or_extrinsics_verified',
        'health_training_authorized',
        'ate_rpe_authorized',
        'confirmation_test_accessed',
        'raw_gt_or_rosbags_opened',
    ):
        need(
            b.get(key) is False,
            'R111_SCIENCE_DENIAL:'+key
        )

    need(
        va.get('schema')==
        'TRUST_ROBOT_R110_INDEPENDENT_FAIL_STOP_VALIDATION_V1'
        and va.get('status')=='PASS'
        and va.get('regression_tests')==39
        and va.get('fault_injections_checked')==6,
        'R110_RECEIPT'
    )

    need(
        vb.get('schema')==
        'TRUST_ROBOT_R111_INDEPENDENT_SHADOW_VALIDATION_V1'
        and vb.get('status')=='PASS'
        and vb.get('regression_tests')==43
        and vb.get('fault_injections')==6,
        'R111_RECEIPT'
    )

    checks=(
        (
            va,'r110','r110_failstop.py',
            'test_r110.py',
            'r110_failstop_contract_v1.md',
            'r110_failure_atomicity_v1.json',
        ),
        (
            vb,'r111','r111_transaction.py',
            'test_r111.py',
            'r111_transaction_contract_v1.md',
            'r111_shadow_transaction_v1.json',
        ),
    )

    for receipt,phase,engine,tests,contract,report in checks:
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
            and receipt.get('scientific_gates_closed')==11
            and receipt.get('real_sensor_factors_authorized')
                is False
            and receipt.get('confirmation_test_accessed')
                is False,
            'RECEIPT_SCIENCE:'+phase
        )

    need(
        vb.get('r110_report_sha256')==
        PINS[
            'evidence/r110/result/r110_failure_atomicity_v1.json'
        ],
        'R110_R111_LINEAGE'
    )

    need(
        m.get('r110_test_count')==39
        and m.get('r111_test_count')==43
        and m.get('archived_regression_tests')==82
        and m.get('source_count')==10
        and m.get('s6_source_sha256')==S6_SHA
        and m.get('scientific_gates_closed')==11,
        'MANIFEST_COUNTS'
    )

    for key in (
        'real_sensor_factor_execution_authorized',
        'r95_backend_merged_into_s6',
        'hardware_streaming_verified',
        'durable_crash_recovery_verified',
        'distributed_exactly_once_verified',
        'concurrent_atomic_publication_verified',
        'physical_clock_or_extrinsics_verified',
        'health_training_authorized',
        'ate_rpe_authorized',
        'confirmation_test_accessed',
        'raw_gt_or_rosbags_archived',
        'qualified_author_reply_ingested',
    ):
        need(
            m.get(key) is False,
            'MANIFEST_GATES:'+key
        )

    print('R112_STANDALONE_CHECKPOINT_VERIFIER=PASS')
    print('R112_SOURCE_AND_METADATA_SHA256=12_PASS')
    print('R112_R110_R111_RESULT_LINEAGE=PASS')
    print('R112_FAIL_STOP_AND_SHADOW_TRANSACTION_AUDIT=PASS')
    print('R112_SCIENTIFIC_GATES=11_CLOSED')

if __name__=='__main__':
    need(
        len(sys.argv)==3
        and sys.argv[1]=='verify',
        'ARGUMENTS'
    )

    verify(pathlib.Path(sys.argv[2]))
